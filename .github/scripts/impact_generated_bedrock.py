import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import boto3


# -----------------------------
# Config (env overridable)
# -----------------------------
SRC_DIR = os.getenv("SRC_DIR", "src/main/java")
TEST_DIR = os.getenv("TEST_DIR", "src/test/java")

# MODE:
#   - "diff" (PR-aware)   -> generate tests only for changed Java files
#   - "full"              -> generate tests for all Java files under SRC_DIR
MODE = os.getenv("MODE", "diff").lower()

# CI context (GitHub Actions)
GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS", "").lower() == "true"
GITHUB_BASE_REF = os.getenv("GITHUB_BASE_REF")   # PR base branch name (e.g., "main")
GITHUB_HEAD_REF = os.getenv("GITHUB_HEAD_REF")   # PR head branch name (e.g., "feature/x")

# Prefer BASE_BRANCH from CI if present
BASE_BRANCH = os.getenv("BASE_BRANCH") or (GITHUB_BASE_REF if GITHUB_BASE_REF else "main")

MAX_FILES = int(os.getenv("MAX_FILES", "50"))
START_AT = int(os.getenv("START_AT", "0"))
RUN_MAVEN = os.getenv("RUN_MAVEN", "false").lower() == "true"
MAVEN_CMD = os.getenv("MAVEN_CMD", "mvn test -DfailIfNoTests=false")

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

# For Claude Opus via Bedrock, use an Inference Profile ARN
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


def run_out(cmd: str, check: bool = True) -> str:
    cp = run(cmd, check=check)
    return (cp.stdout or "").strip()


def git_root() -> Path:
    try:
        return Path(run_out("git rev-parse --show-toplevel", check=True))
    except subprocess.CalledProcessError:
        raise RuntimeError("Not inside a git repository. Run this inside your pr-ai-agent repo.")


def ensure_repo_root_cwd() -> Path:
    root = git_root()
    os.chdir(root)
    return root


def safe_read_text(p: Path, limit_chars: int = 200_000) -> str:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if len(txt) > limit_chars:
        return txt[:limit_chars] + "\n/* TRUNCATED */\n"
    return txt


def java_to_test_path(source_path: str) -> str:
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


def bedrock_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


def bedrock_generate_text(client, prompt: str) -> str:
    if not BEDROCK_MODEL_ID:
        raise RuntimeError(
            "BEDROCK_MODEL_ID is not set. For Claude Opus in many accounts you must set it to an "
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
        if isinstance(b, dict) and "text" in b:
            parts.append(b["text"])
    return "\n".join(parts).strip()


def strip_code_fences(text: str) -> str:
    return text.replace("```java", "").replace("```", "").strip()


def ensure_mvnw_fallback(cmd: str) -> str:
    if cmd.strip().startswith("./mvnw") and not Path("mvnw").exists():
        return cmd.replace("./mvnw", "mvn", 1)
    return cmd


def discover_spring_boot_application_class(repo_root: Path) -> Optional[str]:
    """
    Finds a class annotated with @SpringBootApplication and returns FQCN, e.g. com.example.demo.DemoApplication
    """
    src = repo_root / SRC_DIR
    if not src.exists():
        return None

    for f in src.rglob("*.java"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        if "@SpringBootApplication" not in text:
            continue

        pkg = None
        m = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", text, re.MULTILINE)
        if m:
            pkg = m.group(1).strip()

        cls = None
        m2 = re.search(r"^\s*public\s+class\s+([A-Za-z0-9_]+)\s*", text, re.MULTILINE)
        if m2:
            cls = m2.group(1).strip()

        if pkg and cls:
            return f"{pkg}.{cls}"

    return None


def ensure_origin_base_fetched(base_branch: str) -> None:
    # Best-effort fetch so origin/<base> exists in CI/local
    run("git fetch --all --prune --no-tags", check=False)
    run(f"git fetch origin {base_branch} --prune --no-tags", check=False)


def safe_merge_base(base_ref: str) -> Optional[str]:
    try:
        sha = run_out(f"git merge-base {base_ref} HEAD", check=True)
        return sha if sha else None
    except Exception:
        return None


def get_changed_java_files(base_branch: str) -> List[str]:
    """
    Robust diff selection:
      1) origin/<base>...HEAD (preferred; PR-style)
      2) merge-base(origin/<base>, HEAD)..HEAD
      3) HEAD~1..HEAD
    """
    ensure_origin_base_fetched(base_branch)
    base_ref = f"origin/{base_branch}"

    # 1) Try triple-dot first
    try:
        out = run_out(f"git diff --name-only {base_ref}...HEAD", check=True)
        files = [f.strip() for f in out.splitlines() if f.strip()]
        return [f for f in files if f.endswith(".java") and f.startswith(SRC_DIR)]
    except Exception:
        pass

    # 2) merge-base fallback
    mb = safe_merge_base(base_ref)
    if mb:
        try:
            out = run_out(f"git diff --name-only {mb}..HEAD", check=True)
            files = [f.strip() for f in out.splitlines() if f.strip()]
            return [f for f in files if f.endswith(".java") and f.startswith(SRC_DIR)]
        except Exception:
            pass

    # 3) last commit fallback
    try:
        out = run_out("git diff --name-only HEAD~1..HEAD", check=True)
        files = [f.strip() for f in out.splitlines() if f.strip()]
        return [f for f in files if f.endswith(".java") and f.startswith(SRC_DIR)]
    except Exception:
        return []


def build_prompt(component_type: str, source_code: str, target_test_file: str, boot_app_fqcn: Optional[str]) -> str:
    rules = [
        "Return ONLY Java code (no markdown, no explanations).",
        "Include correct package declaration matching the target path.",
        "Include all necessary imports.",
        "Use JUnit 5.",
        "Avoid flaky timing.",
        "Do NOT require Mockito inline mocking features.",
    ]

    repo_hint = ""
    if component_type == "REPOSITORY":
        if boot_app_fqcn:
            repo_hint = (
                "\nRepository testing requirements:\n"
                f"- Prefer @DataJpaTest.\n"
                f"- Add @ContextConfiguration(classes = {boot_app_fqcn}.class) to avoid 'Unable to find a @SpringBootConfiguration'.\n"
                "- Use TestEntityManager when useful.\n"
            )
        else:
            repo_hint = (
                "\nRepository testing requirements:\n"
                "- Prefer @DataJpaTest.\n"
                "- If you cannot locate the application configuration, use @SpringBootTest(classes=...) or @ContextConfiguration with a minimal config.\n"
            )

    controller_hint = ""
    if component_type == "CONTROLLER":
        controller_hint = (
            "\nController testing requirements:\n"
            "- Prefer @WebMvcTest(ControllerClass.class).\n"
            "- Mock dependencies via @MockBean.\n"
            "- Use MockMvc and validate status + JSON.\n"
        )

    service_hint = ""
    if component_type == "SERVICE":
        service_hint = (
            "\nService testing requirements:\n"
            "- Pure unit tests with Mockito (MockitoExtension).\n"
            "- Mock collaborators and cover edge cases.\n"
        )

    prompt = (
        "You are a Senior Java Test Automation Engineer.\n\n"
        "Goal: Generate a high-quality JUnit 5 test for this Java component.\n"
        f"Component Type: {component_type}\n"
        f"Target Test File Path: {target_test_file}\n\n"
        "RULES:\n" + "\n".join([f"- {r}" for r in rules]) + "\n"
        f"{repo_hint}{controller_hint}{service_hint}\n"
        "SOURCE CODE START\n"
        + source_code
        + "\nSOURCE CODE END\n"
    )
    return prompt


# -----------------------------
# Main
# -----------------------------
def main():
    repo_root = ensure_repo_root_cwd()
    print(f"Repo root: {repo_root}")
    print(f"CI={GITHUB_ACTIONS}  MODE={MODE}  BASE_BRANCH={BASE_BRANCH}  HEAD_REF={GITHUB_HEAD_REF}")

    src_path = repo_root / SRC_DIR
    if not src_path.exists():
        raise RuntimeError(f"SRC_DIR not found: {src_path}")

    boot_app_fqcn = discover_spring_boot_application_class(repo_root)
    if boot_app_fqcn:
        print(f"SpringBootApplication detected: {boot_app_fqcn}")
    else:
        print("SpringBootApplication not detected (repository tests may require manual config).")

    if MODE == "diff":
        java_files = get_changed_java_files(BASE_BRANCH)
        if not java_files:
            print("No changed Java files detected via diff. Exiting.")
            return
    else:
        java_files = [str(p.as_posix()) for p in src_path.rglob("*.java")]

    java_files = java_files[START_AT:START_AT + MAX_FILES]
    print(f"Files selected={len(java_files)}  START_AT={START_AT}  MAX_FILES={MAX_FILES}")

    client = bedrock_client()

    generated = []
    for i, f in enumerate(java_files, start=1):
        src_file = Path(f)
        if not src_file.exists():
            continue

        comp_type = classify_component(src_file)
        tgt = java_to_test_path(str(src_file))

        source_code = safe_read_text(src_file)
        prompt = build_prompt(comp_type, source_code, tgt, boot_app_fqcn)

        print(f"[{i}/{len(java_files)}] Generating test: {src_file} -> {tgt}")
        out = bedrock_generate_text(client, prompt)
        code = strip_code_fences(out)

        target_path = Path(tgt)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(code, encoding="utf-8")

        generated.append({"source": str(src_file), "test": str(target_path), "type": comp_type})

    Path(OUTPUT_MANIFEST).write_text(
        json.dumps(
            {
                "mode": MODE,
                "base_branch": BASE_BRANCH,
                "start_at": START_AT,
                "max_files": MAX_FILES,
                "spring_boot_application": boot_app_fqcn,
                "generated": generated,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
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