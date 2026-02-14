# TEST.md — Bedrock PR Test Agent

## Overview
This document captures the **exact steps** to use the Bedrock-powered PR Test Agent
for both **DIFF (PR-aware)** and **FULL (entire repo)** test generation.

Repo:
https://github.com/saravanaaws2025-hash/pr-ai-agent

---

## 1. Prerequisites

### Java
- Java **17** (required)
```bash
brew install temurin@17
java -version
```

### Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install boto3
```

### Git
```bash
git clone https://github.com/saravanaaws2025-hash/pr-ai-agent.git
cd pr-ai-agent
```

---

## 2. AWS Bedrock (Claude Opus) Setup

### Required IAM Permissions
Your IAM user/role must allow:
- bedrock:InvokeModel
- bedrock:InvokeModelWithResponseStream
- bedrock:ListInferenceProfiles

### Environment Variables
```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID="arn:aws:bedrock:us-east-1:302263057519:inference-profile/us.anthropic.claude-opus-4-20250514-v1:0"
```

Verify:
```bash
aws sts get-caller-identity
```

---

## 3. Make a Code Change

Example:
```bash
git checkout -b ai/diff-smoke-test
vi src/main/java/com/example/demo/service/ProductService.java
```

Commit:
```bash
git add src/main/java
git commit -m "feat: update product service logic"
git push -u origin ai/diff-smoke-test
```

---

## 4. DIFF Mode (PR-aware Test Generation)

```bash
export MODE=diff
export BASE_BRANCH=main
export MAX_FILES=25

python .github/scripts/impact_generated_bedrock.py
```

What happens:
- Computes git diff vs base branch
- Generates tests only for changed Java files
- Writes tests under `src/test/java`
- Produces `generated-tests-manifest.json`

---

## 5. FULL Mode (Entire Repo)

```bash
export MODE=full
export MAX_FILES=50

python .github/scripts/impact_generated_bedrock.py
```

Use FULL mode sparingly (bootstrap only).

---

## 6. Run Tests

```bash
mvn test
```

---

## 7. Commit Generated Tests

```bash
git add src/test/java generated-tests-manifest.json
git commit -m "test: add Bedrock-generated tests"
git push
```

---

## 8. GitHub PR Flow

1. Open PR from your branch → `main`
2. CI runs in DIFF mode
3. Artifacts include:
   - generated-tests-manifest.json
   - surefire-reports

---

## 9. Common Pitfalls (Already Solved)

| Problem | Fix |
|------|----|
Mockito fails on Java 25 | Use Java 17 |
Repository test fails to find config | Auto-detect `@SpringBootApplication` |
Bedrock ValidationException | Use inference profile ARN |
Git diff empty | Robust merge-base fallback |

---

## 10. Files Added

- `.github/scripts/impact_generated_bedrock.py`
- `.github/workflows/*`
- `generated-tests-manifest.json`
- `TEST.md`

---

## 11. Recommended Next Enhancements

- Auto-commit generated tests from CI
- PR comments with coverage summary
- Rate-limit + cost guardrails
- Test healing loop

---

**This setup is production-grade and PR-safe.**
