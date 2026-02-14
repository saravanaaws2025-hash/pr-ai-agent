
#!/usr/bin/env python3
# Full PR-aware Test Automation Agent with AWS Bedrock (Claude Opus 4.1)

import os
import subprocess
import json
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

SRC_DIR = "src/main/java"
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")
GITHUB_REF_NAME = os.getenv("GITHUB_REF_NAME", "")
GITHUB_HEAD_REF = os.getenv("GITHUB_HEAD_REF", "")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "local")

# ----------------------------
# Prompt model
# ----------------------------
@dataclass(frozen=True)
class Prompt:
    system: str
    user: str

SYSTEM_JAVA_TEST_ENGINEER = (
    "You are a Senior Java Test Automation Engineer. "
    "Generate correct, compiling, deterministic JUnit 5 tests. "
    "Return ONLY Java source code."
)

def build_synthesize_prompt(entry, source_code, existing_test_code):
    return Prompt(
        system=SYSTEM_JAVA_TEST_ENGINEER,
        user=f"""Generate JUnit 5 tests.

TARGET:
- target_test_file: {entry['target_test_file']}
- action: {entry['action']}
- component_type: {entry['test_type']}
- frameworks: {', '.join(entry['frameworks'])}

RULES:
1) If CREATE: output full class with package/imports.
2) If EXTEND: output ONLY new @Test methods.
3) Do not invent constructors.
4) Use Mockito where applicable.
5) Ensure code compiles.

SOURCE CODE:
{source_code}

EXISTING TEST CODE:
{existing_test_code}
"""
    )

def build_self_heal_prompt(entry, source_code, current_test, error_log):
    return Prompt(
        system=SYSTEM_JAVA_TEST_ENGINEER,
        user=f"""Fix the failing JUnit 5 test code so it compiles and passes.

RULES:
1) Output FULL Java source for the test file.
2) Do not change production code.
3) Ensure code compiles.

TARGET_TEST_FILE:
{entry['target_test_file']}

SOURCE CODE:
{source_code}

CURRENT TEST CODE:
{current_test}

ERROR LOG:
{error_log}
"""
    )

# ----------------------------
# Bedrock Claude LLM
# ----------------------------
@dataclass(frozen=True)
class Message:
    role: str
    content: str

class BedrockClaudeLLM:
    def __init__(self, model: str, max_tokens: int):
        import boto3
        self.client = boto3.client("bedrock-runtime")
        self.model = model
        self.max_tokens = max_tokens

    def generate_text(self, messages: List[Message]) -> str:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        user = "\n\n".join(m.content for m in messages if m.role == "user")

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        response = self.client.invoke_model(
            modelId=self.model,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        return payload["content"][0]["text"].strip()

def strip_fences(t: str) -> str:
    return t.replace("```java", "").replace("```", "").strip()

# ----------------------------
# Main Agent
# ----------------------------
class TestAutomationAgent:
    def __init__(self, llm):
        self.llm = llm
        self.all_source_files = list(Path(SRC_DIR).rglob("*.java"))

    def run_cmd(self, cmd: str):
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return (result.stdout + result.stderr).strip(), result.returncode

    def find_dependents(self, class_name: str, original_path: str) -> List[str]:
        dependents = []
        pattern = re.compile(r"\b" + re.escape(class_name) + r"\b")
        for f in self.all_source_files:
            if str(f) == original_path:
                continue
            try:
                if pattern.search(f.read_text(errors="ignore")):
                    dependents.append(str(f))
            except Exception:
                pass
        return dependents

    def execute(self):
        diff_cmd = f"git diff --name-only origin/{BASE_BRANCH}...HEAD"
        changed = subprocess.check_output(diff_cmd, shell=True, text=True).splitlines()
        java_files = [f for f in changed if f.endswith(".java")]

        if not java_files:
            print("No Java changes detected.")
            return

        test_entries = []
        for src in java_files:
            test_file = src.replace("src/main/java", "src/test/java").replace(".java", "Test.java")
            action = "EXTEND" if Path(test_file).exists() else "CREATE"
            test_entries.append({
                "source_path": src,
                "target_test_file": test_file,
                "action": action,
                "frameworks": ["JUnit 5", "Mockito"],
                "test_type": "general"
            })

        for entry in test_entries:
            source_code = Path(entry["source_path"]).read_text(errors="ignore")
            existing = Path(entry["target_test_file"]).read_text(errors="ignore") if entry["action"] == "EXTEND" else ""

            prompt = build_synthesize_prompt(entry, source_code, existing)
            raw = self.llm.generate_text([
                Message("system", prompt.system),
                Message("user", prompt.user)
            ])
            code = strip_fences(raw)

            Path(entry["target_test_file"]).parent.mkdir(parents=True, exist_ok=True)
            if entry["action"] == "CREATE":
                Path(entry["target_test_file"]).write_text(code)
            else:
                cur = Path(entry["target_test_file"]).read_text()
                Path(entry["target_test_file"]).write_text(cur.rstrip("}") + "\n" + code + "\n}")

        out, rc = self.run_cmd("./mvnw test -DfailIfNoTests=false")
        print(out)
        if rc != 0:
            print("Tests failed")
            sys.exit(1)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic.claude-opus-4-1")
    ap.add_argument("--max-tokens", type=int, default=4000)
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    llm = BedrockClaudeLLM(args.model, args.max_tokens)
    TestAutomationAgent(llm).execute()
