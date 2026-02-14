import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional

import boto3


# -----------------------------
# Config (env overridable)
# -----------------------------
SRC_DIR = os.getenv("SRC_DIR", "src/main/java")
TEST_DIR = os.getenv("TEST_DIR", "src/test/java")

MODE = os.getenv("MODE", "full").lower()  # "full" (default) or "diff"
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")

MAX_FILES = int(os.getenv("MAX_FILES", "50"))  # safety cap
START_AT = int(os.getenv("START_AT", "0"))     # resume support
RUN_MAVEN = os.getenv("RUN_MAVEN", "false").lower() == "true"
MAVEN_CMD = os.getenv("MAVEN_CMD", "./mvnw test -DfailIfNoTests=false")

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

# IMPORTANT:
# For Claude Opus 4.6 in many accounts, you must use an Inference Profile ARN here.
# Example:
# export BEDROCK_MODEL_ID="arn:aws:bedrock:us-east-1:123456789012:inference-profile/my-claude-opus-46"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "").strip()

# LLM generation knobs
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("TOP_P", "0.9"))

OUTPUT_MANIFEST = os.getenv("OUTPUT_MANIFEST", "generated-tests-manifest.json")


# -----------------------------
# Helpers
# -----------------------------
def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, check=check)


def git_root() -> Path:
    try:
        cp = run("git rev-parse --show-toplevel", check=True)
        return Path(cp.stdout.strip())
    except subprocess.CalledProcessError:
        raise RuntimeError("Not inside a git repository. Run this inside your pr-ai-agent repo.")


def ensure_repo_root_cwd() -> Path:
    root = git_root()
    os.chdir(root)
    return root


def file_class_name(java_path: str) -> str:
    return Path(java_path).stem


def safe_read_text(p: Path, limit_chars: int = 200_000) -> str:
    # limit to avoid huge prompts
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if len(txt) > limit_chars:
        return txt[:limit_chars] + "\n/* TRUNCATED */\n"
    return txt


def java_to_test_path(source_path: str) -> str:
    # src/main/java/a/b/C.java -> src/test/java/a/b/CTest.java
    test_path = source_path.replace(SRC_DIR, TEST_DIR)
    return test_path.replace(".java", "Test.java")


def classify_component(java_file: Path) -> str:
    txt = safe_read_text(java_file, limit_chars=80_000)
    if "@RestController" in txt or "@Controller" in txt:
        return "CONTROLLER"
    if "@Service" in txt:
        return "SERVICE"
    if "@Repository" in txt:
        return "REPOSITORY"
    if "@Entity" in txt:
        return "ENTITY"
    if "DTO" in str(java_file) or "Dto" in str(java_file):
        return "DTO"
    return "JAVA_COMPONENT"


def get_changed_java_files(base_branch: str) -> List[str]:
    """
    Robust diff selection:
      - Try three-dot (merge-base) first
      - Fall back to two-dot
      - Fall back to last commit
    """
    candidates = [
        f"git diff --name-only origin/{base_branch}...HEAD",
        f"git diff --name-only {base_branch}...HEAD",
        f"git diff --name-only origin/{base_branch}..HEAD",
        f"git diff --name-only {base_branch}..HEAD",
        "git diff --name-only HEAD~1..HEAD",
    ]

    out = ""
    for cmd in candidates:
        try:
            cp = run(cmd, check=True)
            out = cp.stdout.strip()
            if out:
                break
        except subprocess.CalledProcessError as e:
            msg = (e.stderr or e.stdout or "").strip()
            last = msg.splitlines()[-1] if msg else "unknown git diff error"
            print(f"Warning: diff failed: {cmd}")
            print(f"  {last}")

    if not out:
        return []

    return [f for f in out.splitlines() if f.endswith(".java")]


def bedrock_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


def bedrock_generate_text(client, prompt: str) -> str:
    if not BEDROCK_MODEL_ID:
        raise RuntimeError(
            "BEDROCK_MODEL_ID is not set. For Claude Opus 4.6 you typically must set it to an "
            "Inference Profile ARN (not the raw model id)."
        )

    resp = client.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={
            "maxTokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "topP": TOP_P,
        },
    )

    blocks = resp.get("output", {}).get("message", {}).get("content", [])
    parts = []
    for b in blocks:
        if "text" in b:
            parts.append(b["text"])
    return "\n".join(parts).strip()


def build_prompt(component_type: str, source_code: str, target_test_file: str) -> str:
    # Avoid triple-backticks inside triple-quotes; keep prompt construction simple.
    rules = [
        "Return ONLY Java code (no markdown, no explanations).",
        "Include correct package declaration matching the target path.",
        "Include all necessary imports.",
        "Use JUnit 5. Use Mockito where needed.",
        "Prefer deterministic tests; avoid flaky timing.",
        "If Spring controller: use MockMvc and cover status + payload validations.",
        "If service: mock dependencies and cover edge cases.",
        "If repository/entity: prefer @DataJpaTest patterns (if feasible) or focus on mapping/validation.",
    ]

    prompt = (
        "You are a Senior Java Test Automation Engineer.\n\n"
        f"Goal: Generate a high-quality JUnit 5 test for this Java component.\n"
        f"Component Type: {component_type}\n"
        f"Target Test File Path: {target_test_file}\n\n"
        "RULES:\n"
        + "\n".join([f"- {r}" for r in rules])
        + "\n\n"
        "SOURCE CODE START\n"
        + source_code
        + "\nSOURCE CODE END\n"
    )
    return prompt


def strip_code_fences(text: str) -> str:
    # In case the model returns ```java ... ```
    text = text.replace("```java", "").replace("```", "")
    return text.strip()


def ensure_mvnw_fallback(cmd: str) -> str:
    if cmd.strip().startswith("./mvnw") and not Path("mvnw").exists():
        return cmd.replace("./mvnw", "mvn", 1)
    return cmd


# -----------------------------
# Main
# -----------------------------
def main():
    repo_root = ensure_repo_root_cwd()
    print(f"Repo root: {repo_root}")

    # Refresh remote refs (best effort)
    try:
        run("git fetch --all --prune", check=True)
        run(f"git fetch origin {BASE_BRANCH} --prune", check=False)
    except subprocess.CalledProcessError as e:
        print("Warning: git fetch failed; continuing. This may affect diff mode.")
        print((e.stderr or e.stdout or "").strip())

    src_path = repo_root / SRC_DIR
    if not src_path.exists():
        raise RuntimeError(f"SRC_DIR not found: {src_path}")

    if MODE == "diff":
        java_files = get_changed_java_files(BASE_BRANCH)
        if not java_files:
            print("No changed Java files detected via diff. Exiting.")
            return
    else:
        java_files = [str(p) for p in src_path.rglob("*.java")]

    # Apply safety window
    java_files = java_files[START_AT:START_AT + MAX_FILES]
    print(f"Mode={MODE}  Files={len(java_files)}  START_AT={START_AT}  MAX_FILES={MAX_FILES}")

    client = bedrock_client()

    generated = []
    for i, f in enumerate(java_files, start=1):
        src_file = Path(f)
        if not src_file.exists():
            continue

        comp_type = classify_component(src_file)
        tgt = java_to_test_path(str(src_file))

        source_code = safe_read_text(src_file)
        prompt = build_prompt(comp_type, source_code, tgt)

        print(f"[{i}/{len(java_files)}] Generating test for: {src_file} -> {tgt}")
        try:
            out = bedrock_generate_text(client, prompt)
        except Exception as e:
            print(f"Bedrock call failed for {src_file}: {e}")
            raise

        code = strip_code_fences(out)

        target_path = Path(tgt)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(code, encoding="utf-8")

        generated.append({"source": str(src_file), "test": str(target_path), "type": comp_type})

    Path(OUTPUT_MANIFEST).write_text(json.dumps({"generated": generated}, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {OUTPUT_MANIFEST}")

    if RUN_MAVEN:
        cmd = ensure_mvnw_fallback(MAVEN_CMD)
        print(f"Running Maven: {cmd}")
        cp = run(cmd, check=False)
        print(cp.stdout)
        print(cp.stderr, file=sys.stderr)
        if cp.returncode != 0:
            raise SystemExit(cp.returncode)


if __name__ == "__main__":
    main()