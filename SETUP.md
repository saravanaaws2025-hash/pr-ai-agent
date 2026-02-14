# PR AI Agent – Bedrock Claude Setup Guide

This document captures the **complete, reproducible setup** for running the PR-aware AI Test Generation Agent using **Amazon Bedrock (Claude Opus)** with **Spring Boot + Maven** projects.

---

## 1. Prerequisites

### 1.1 Java (Required)
Mockito / ByteBuddy are **not compatible with Java 25+**. Use Java 17.

```bash
brew install --cask temurin@17
```

Verify:
```bash
java -version
```
Expected:
```
openjdk version "17.x"
```

---

### 1.2 Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install boto3
```

---

## 2. GitHub Repository Setup

### 2.1 Clone the repository

```bash
git clone https://github.com/saravanaaws2025-hash/pr-ai-agent.git
cd pr-ai-agent
```

Verify:
```bash
git remote -v
```

---

### 2.2 macOS: show hidden folders

```bash
ls -la .github
```

Finder shortcut:
```
Cmd + Shift + .
```

---

### 2.3 .gitignore

Ensure this exists:
```
target/
.DS_Store
```

---

## 3. AWS Bedrock + Claude Opus Setup

### 3.1 Configure AWS credentials

```bash
aws configure
```

Provide:
- AWS Access Key ID
- AWS Secret Access Key
- Region: `us-east-1`

Verify:
```bash
aws sts get-caller-identity
```

---

### 3.2 Set Bedrock environment variables

**IMPORTANT:** Use the **Inference Profile ARN**, not the raw model ID.

```bash
export AWS_REGION="us-east-1"
export BEDROCK_MODEL_ID="arn:aws:bedrock:us-east-1:302263057519:inference-profile/us.anthropic.claude-opus-4-20250514-v1:0"
```

Optional verification:
```bash
aws bedrock list-inference-profiles --region us-east-1
```

---

## 4. Spring Boot Configuration (Critical)

Repository tests require a Spring Boot anchor.

Create:
```
src/main/java/com/example/demo/DemoApplication.java
```

```java
package com.example.demo;

import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
}
```

Commit:
```bash
git add src/main/java/com/example/demo/DemoApplication.java
git commit -m "chore: add SpringBootApplication config for JPA tests"
git push origin main
```

---

## 5. AI Test Generation Script

### 5.1 Script location

```
.github/scripts/impact_generated_bedrock.py
```

This script:
- Detects changed Java files (PR mode) or full repo
- Sends source code to **Claude Opus via Bedrock**
- Generates JUnit 5 tests
- Writes to `src/test/java`
- Emits `generated-tests-manifest.json`

---

## 6. Running the Agent

### 6.1 Full repository test generation

```bash
source .venv/bin/activate
export MODE=full
export MAX_FILES=25
python .github/scripts/impact_generated_bedrock.py
```

---

### 6.2 PR-diff based generation (CI style)

```bash
export MODE=pr
python .github/scripts/impact_generated_bedrock.py
```

Uses:
```bash
git diff origin/main...HEAD
```

---

## 7. Running Tests

```bash
mvn test
```

Expected:
```
BUILD SUCCESS
```

---

## 8. Committing Generated Tests

```bash
git status -sb
git add src/test/java generated-tests-manifest.json
git commit -m "test: generate unit tests via Bedrock Claude Opus"
git push origin main
```

---

## 9. What This Enables

- PR-aware AI test generation
- Claude Opus 4.x via Amazon Bedrock
- Spring Boot–safe repository and controller tests
- CI-ready automation
- Java 17–stable Mockito + ByteBuddy setup

---

## 10. Recommended Next Enhancements

- Auto-commit tests from CI
- PR comments with test summary
- Retry / self-healing test generation
- Token & cost guards
- Coverage delta enforcement

---

**Owner:** Sarava