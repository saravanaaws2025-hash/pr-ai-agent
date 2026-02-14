import os
import subprocess
import json
import re
import sys
from pathlib import Path
from google import genai


SRC_DIR = "src/main/java"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")
GITHUB_REF_NAME = os.getenv("GITHUB_REF_NAME")
GITHUB_HEAD_REF = os.getenv("GITHUB_HEAD_REF")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "local")

# --- Configuration ---
CLIENT = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.0-flash" # Optimized for speed/cost in CI

class TestAutomationAgent:
    
    def __init__(self):
        self.all_source_files = list(Path(SRC_DIR).rglob("*.java"))

    def run_cmd(self, cmd):
        # If the command starts with ./mvnw, check if it exists
        if cmd.startswith("./mvnw") and not os.path.exists("mvnw"):
            print("⚠️ Maven Wrapper not found. Falling back to global 'mvn'...")
            cmd = cmd.replace("./mvnw", "mvn")
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip() + "\n" + result.stderr.strip(), result.returncode

    def run_git_command(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ""

    def get_class_name(self, file_path):
        basename = os.path.basename(file_path)
        return os.path.splitext(basename)[0]

    def identify_component_type(self, file_path):
        if not os.path.exists(file_path): return "DELETED"
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if "@RestController" in content or "@Controller" in content: return "CONTROLLER"
        if "@Service" in content: return "SERVICE"
        if "@Repository" in content: return "REPOSITORY"
        if "@Entity" in content: return "ENTITY"
        if "DTO" in file_path or "Dto" in file_path: return "DTO"
        return "JAVA_COMPONENT" # Default

    # def find_dependents(self, target_class_name, all_java_files):
    #     """
    #     Returns a list of file paths that use the target_class_name.
    #     """
    #     dependents = []
    #     # Regex for whole word match to avoid partials (e.g. matching 'User' in 'UserDto')
    #     pattern = re.compile(r'\b' + re.escape(target_class_name) + r'\b')

    #     for file_path in all_java_files:
    #         # Don't check the file against itself here (handled in main logic)
    #         if target_class_name in os.path.basename(file_path):
    #             continue
                
    #         with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    #             if pattern.search(f.read()):
    #                 dependents.append(file_path)
                
    #     return dependents

    def find_dependents(self, class_name, original_path):
        dependents = []
        pattern = re.compile(r'\b' + re.escape(class_name) + r'\b')
        for f in self.all_source_files:
            if class_name in os.path.basename(str(f)):
                continue
            if str(f) != str(original_path) and pattern.search(f.read_text(errors='ignore')):
                dependents.append(str(f))
        return dependents



#### Generate test-plan related logic begins here ######

    def get_test_strategy(self, comp_type):
        """Deterministic rules for test generation."""
        strategies = {
            "CONTROLLER": {
                "type": "controller",
                "frameworks": ["JUnit 5", "Spring MockMvc"],
                "description": "Integration test for REST endpoints and status codes."
            },
            "SERVICE": {
                "type": "service",
                "frameworks": ["JUnit 5", "Mockito"],
                "description": "Unit test for business logic with mocked dependencies."
            },
            "REPOSITORY": {
                "type": "repository",
                "frameworks": ["JUnit 5", "DataJpaTest", "Testcontainers"],
                "description": "Persistence layer testing with H2 or Dockerized DB."
            },
            "DTO": {
                "type": "dto",
                "frameworks": ["JUnit 5", "AssertJ"],
                "description": "Verification of data mapping and Bean Validation."
            },
            "CONFIGURATION": {
                "type": "security",
                "frameworks": ["Spring Security Test"],
                "description": "Validating authentication and authorization filters."
            }
        }
        return strategies.get(comp_type, {
            "type": "general",
            "frameworks": ["JUnit 5"],
            "description": "Standard regression test."
        })

    def get_test_path(self, source_path):
        """Converts src/main/java/.../Name.java to src/test/java/.../NameTest.java"""
        test_path = source_path.replace("src/main/java", "src/test/java")
        return test_path.replace(".java", "Test.java")


    def generate_test_plan(self, impact_manifest):
        test_plan = {
            "plan_id": "PR_TEST_PLAN_" + GITHUB_RUN_ID,
            "test_entries": []
        }
        
        seen_files = set()

        # Process both direct modifications and ripple effects
        for cluster in impact_manifest["impact_analysis"]:
            source = cluster["source_file"]
            dependents = cluster["ripple_effect"]
            
            # Add source file to test plan
            all_targets = [(source["path"], source["type"], "DIRECT")]
            # Add ripple files to test plan
            for dep in dependents:
                all_targets.append((dep["path"], dep["type"], "RIPPLE"))

            for path, comp_type, impact_kind in all_targets:
                if path in seen_files:
                    continue
                
                strategy = self.get_test_strategy(comp_type)
                test_file = self.get_test_path(path)
                
                # Determine action: Check if test file already exists
                action = "EXTEND" if os.path.exists(test_file) else "CREATE"

                test_plan["test_entries"].append({
                    "component_name": os.path.basename(path).replace(".java", ""), ##Path(path).stem
                    "source_path": path,
                    "impact_origin": impact_kind,
                    "test_type": strategy["type"],
                    "frameworks": strategy["frameworks"],
                    "target_test_file": test_file,
                    "action": action,
                    "coverage_goal": "High" if impact_kind == "DIRECT" else "Regression"
                })
                seen_files.add(path)

        return test_plan

#### Generate test-plan related logic ends here ######


#### Test Generation (LLM assisted) starts here ######
    def synthesize_and_save(self, entry):
            source_code = Path(entry['source_path']).read_text()
            existing_test_code = open(entry['target_test_file'], 'r', encoding='utf-8').read() if entry['action'] == 'EXTEND' and os.path.exists(entry['target_test_file']) else ''
            newline = '\n'
            
            prompt = f"""
            You are a Senior Java Test Automation Engineer.

            Generate JUnit 5 code for {entry['target_test_file']}.      

            CONTEXT:
            - Component Type: {entry['test_type']}
            - Frameworks: {', '.join(entry['frameworks'])}
            - Action: {entry['action']} existing test file.

            SOURCE CODE:
            ```java
            {source_code}
            ```
            { "EXISTING TEST CODE:" + newline + "```java" + newline + existing_test_code + newline + "```" if entry['action'] ==  "EXTEND"  else ""}

            TASK:
            Generate a complete, high-quality JUnit 5 test class. 
            - Use Mockito for dependencies.
            - If action is EXTEND, only provide the NEW test methods to be added.
            - If action is CREATE, provide the full class including imports and package declaration.
            - Ensure all code is written for the file path: {entry['target_test_file']} 
            
            RULES:
            1. Only return the Java code. No markdown explanations.
            2. Ensure all imports for {' and '.join(entry['frameworks'])} are included.
            3. Focus on edge cases and the logic changed in the PR.
            4. Ensure declared constructor in a class cannot be applied to given types
            """

            response = CLIENT.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            code = response.text.replace("```java", "").replace("```", "").strip()
            
            target_path = Path(entry['target_test_file'])
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if entry['action'] == "CREATE":
                target_path.write_text(code)
            else:
                current = target_path.read_text()
                # Basic append logic before final class brace
                updated = current.rstrip().rstrip('}') + "\n\n    // Generated Tests\n" + code + "\n}"
                target_path.write_text(updated)

#### Test Generation (LLM assisted) ends here ######


#### Test Execution starts here ######
    def run_selective_tests(self, test_plan):
        """Runs only the newly generated/modified tests."""
        # Convert file paths to class names for Maven (e.g., src/test/java/com/pkg/AppTest.java -> com.pkg.AppTest)
        test_classes = []
        for entry in test_plan["test_entries"]:
            path = entry["target_test_file"]
            class_name = path.replace("src/test/java/", "").replace(".java", "").replace("/", ".")
            test_classes.append(class_name)
        
        test_filter = ",".join(test_classes)
        # Use -DfailIfNoTests=false to avoid crashing if mapping fails
        print(f"👟 Running generated tests: {test_filter}")
        output, code = self.run_cmd(f"./mvnw test -Dtest={test_filter} -DfailIfNoTests=false")
        return code, output
    
    def self_heal(self, entry, error_log):
        """Attempts to fix the code using LLM by providing the error log."""
        print(f"🩹 Attempting self-heal for {entry['component_name']}...")
        source_code = Path(entry['source_path']).read_text()
        current_test = Path(entry['target_test_file']).read_text()
        
        prompt = f"""
        The JUnit test I generated failed. Fix the test code.
        SOURCE: {source_code}
        FAILED TEST: {current_test}
        ERROR LOG: {error_log}
        RULES: Return ONLY the corrected Java code.
        """
        
        response = CLIENT.models.generate_content(
                model=MODEL_ID,
                contents=prompt
        )
        new_code = response.text.replace("```java", "").replace("```", "").strip()
        Path(entry['target_test_file']).write_text(new_code)

    def promote_to_pr(self, test_plan, summary):

        current_branch = GITHUB_HEAD_REF

        # SAFETY CHECK: If we are already on an AI-generated branch, DO NOT create another PR
        if current_branch and current_branch.startswith("ai-test-suite-"):
            print(f"Skipping PR creation: Already on AI branch {current_branch}")
            return

        """Creates a new branch and opens a PR using GitHub CLI."""
        orig_pr_id = GITHUB_REF_NAME.split("/")[0]
        new_branch = f"ai-test-suite-{orig_pr_id}"
        
        # Git Operations
        subprocess.run(f"git checkout -b {new_branch}", shell=True)
        subprocess.run("git add src/test/java/ impact.json test-plan.json", shell=True)
        subprocess.run('git commit -m "docs: AI-generated test suite and impact analysis"', shell=True)
        subprocess.run(f"git push origin {new_branch} --force", shell=True)

        # PR Creation via 'gh' CLI
        pr_body = f"### AI Generated Test Suite\n{summary}\n\nRelated to PR #{orig_pr_id}"
        subprocess.run(f'gh pr create --title "[PR-Aware] Test Validation for PR #{orig_pr_id}" --body "{pr_body}" --base main --head {new_branch}', shell=True)

    def create_error_branch(self):

        current_branch = GITHUB_HEAD_REF

        # SAFETY CHECK: If we are already on an AI-generated branch, DO NOT create another PR
        if current_branch and current_branch.startswith("ai-test-suite-"):
            print(f"Skipping PR creation: Already on AI branch {current_branch}")
            return

        """Creates a new branch and opens a PR using GitHub CLI."""
        orig_pr_id = GITHUB_REF_NAME.split("/")[0]
        new_branch = f"ai-test-suite-error{orig_pr_id}"
        
        # Git Operations
        subprocess.run(f"git checkout -b {new_branch}", shell=True)
        subprocess.run("git add src/test/java/ impact.json test-plan.json", shell=True)
        subprocess.run('git commit -m "docs: AI-generated test suite and impact analysis"', shell=True)
        subprocess.run(f"git push origin {new_branch} --force", shell=True)

    # def parse_test_results(self, stdout):
    #     """
    #     Extracts the Maven test summary from the raw console output.
    #     """
    #     # 1. Locate the block after the 'T E S T S' header
    #     # 2. Look for the 'Results :' summary line
    #     summary_regex = r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"
        
    #     match = re.search(summary_regex, stdout)
        
    #     if match:
    #         runs, fails, errs, skips = match.groups()
    #         # Build a nice Markdown summary
    #         status = "✅ PASS" if int(fails) == 0 and int(errs) == 0 else "❌ FAIL"
    #         return (
    #             f"### Test Execution Summary {status}\n"
    #             f"- **Total Tests**: {runs}\n"
    #             f"- **Failures**: {fails}\n"
    #             f"- **Errors**: {errs}\n"
    #             f"- **Skipped**: {skips}\n"
    #         )
        
    #     return "✅ All generated tests passed after validation."
    
 

    def parse_test_results(self, stdout):
        """
        Extracts the final aggregate Maven test summary by locating 
        the line immediately following the 'Results:' header.
        """
        # Regex logic: 
        # 1. Find 'Results:' (case-insensitive)
        # 2. Skip whitespace/newlines
        # 3. Capture the 'Tests run' line that follows
        pattern = r"Results\s*:\s*\n+(Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+))"
        
        match = re.search(pattern, stdout, re.IGNORECASE)
        
        if match:
            # group(1) is the full text line, groups 2-5 are the digits
            _, runs, fails, errs, skips = match.groups()
            
            status = "✅ PASS" if int(fails) == 0 and int(errs) == 0 else "❌ FAIL"
            
            return (
                f"### Test Execution Summary {status}\n"
                f"- **Total Tests**: {runs} (Aggregate)\n"
                f"- **Failures**: {fails}\n"
                f"- **Errors**: {errs}\n"
                f"- **Skipped**: {skips}\n"
            )
        
        # Fallback: If 'Results:' header is missing, grab the very last 'Tests run' line found
        all_summaries = re.findall(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)", stdout)
        if all_summaries:
            runs, fails, errs, skips = all_summaries[-1]
            status = "✅ PASS" if int(fails) == 0 and int(errs) == 0 else "❌ FAIL"
            return (
                f"### Test Execution Summary {status}\n"
                f"- **Total Tests**: {runs}\n"
                f"- **Failures**: {fails}\n"
                f"- **Errors**: {errs}\n"
                f"- **Skipped**: {skips}\n"
            )

        return "✅ All generated tests passed after validation."

#### Test Execution ends here ######

    def execute(self):

        # 1. Get Changed Files
        diff_cmd = f"git diff --name-only origin/{BASE_BRANCH}...HEAD"
        raw_changes = self.run_git_command(diff_cmd).split('\n')
        changed_files = [f for f in raw_changes if f.endswith(".java")]

        # 2. Map all existing Java files for scanning
        all_java_files = []
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                if file.endswith(".java"):
                    all_java_files.append(os.path.join(root, file))

        manifest = {
            "summary": {"total_files_changed": len(changed_files), "risk_level": "LOW"},
            "impact_analysis": []
        }

        # 3. Analyze each change individually
        for file_path in changed_files:
            # A. Metadata for the changed file
            class_name = self.get_class_name(file_path)
            comp_type = self.identify_component_type(file_path)
            
            # Get line ranges
            diff_hunk_cmd = f"git diff -U0 origin/{BASE_BRANCH}...HEAD -- {file_path}"
            diff_output = self.run_git_command(diff_hunk_cmd)
            ranges = [m.group(1) for m in re.finditer(r"^@@ -\d+.*? \+(\d+)", diff_output, re.MULTILINE)]
            
            # B. Find Ripple Effects
            dependents = self.find_dependents(class_name, all_java_files)
            
            ripple_effects = []
            for dep in dependents:
                dep_status = "IMPACTED"
                # Check if this dependent is ALSO in the changed_files list
                if dep in changed_files:
                    dep_status = "ALSO_MODIFIED"

                ripple_effects.append({
                    "path": dep,
                    "type": self.identify_component_type(dep),
                    "reason": f"Imports/Uses {class_name}",
                    "status": dep_status
                })

            # C. Construct the Change Cluster
            change_entry = {
                "source_file": {
                    "path": file_path,
                    "type": comp_type,
                    "class_name": class_name,
                    "line_ranges": ranges
                },
                "ripple_effect": ripple_effects
            }
            
            manifest["impact_analysis"].append(change_entry)

        # 4. Calculate Risk
        # High risk if any Core Entity is changed or if ripple effects are widespread
        total_ripples = sum(len(item["ripple_effect"]) for item in manifest["impact_analysis"])
        types_changed = [item["source_file"]["type"] for item in manifest["impact_analysis"]]
        
        if "ENTITY" in types_changed or total_ripples > 10:
            manifest["summary"]["risk_level"] = "HIGH"
        elif total_ripples > 0:
            manifest["summary"]["risk_level"] = "MEDIUM"

        with open("impact.json", "w") as f:
            json.dump(manifest, f, indent=2)

        print("Completed creating impact.json")
        
        # 5. Plan Test
        impact_data = manifest
        test_plan = self.generate_test_plan(impact_data)
        with open("test-plan.json", "w") as f:
            json.dump(test_plan, f, indent=2)
        print("Completed creating test-plan.json")

        # for entry in test_plan["test_entries"]:
        #     print(f"🤖 Synthesizing {entry['test_type']} test for {entry['component_name']}...")
        #     self.synthesize_and_save(entry)
        #     print(f"🤖 Completed Synthesizing {entry['test_type']} test for {entry['component_name']}...")

        entry = test_plan["test_entries"][0]
        self.synthesize_and_save(entry)
        print(f"🤖 Completed Synthesizing {entry['test_type']} test for {entry['component_name']}...")

        # 6. Execution & Healing Loop

        max_retries = 2
        attempt = 0
        success = False
        
        while attempt < max_retries:
            exit_code, output = self.run_selective_tests(test_plan)
            
            if exit_code == 0:
                success = True
                break
            
                            # break
            print(f"❌ Test Failure (Attempt {attempt + 1}/{max_retries})")
            for entry in test_plan["test_entries"]:
                self.self_heal(entry, output)
            attempt += 1

        # 3. Finalization
        if success:
            try:
                summary = self.parse_test_results(output)
                self.promote_to_pr(test_plan, summary)
            except Exception as e:
                print(f"Error in passing test results: {str(e)}")

        else:
            print("🛑 Healing failed. Publishing diagnostics.")
            print(f"❌ failure_diagnostics.log {output}")
            self.create_error_branch()
            with open("failure_diagnostics.log", "w") as f:
                f.write(output)
            sys.exit(1) # Halt CI pipeline
      

if __name__ == "__main__":
    TestAutomationAgent().execute()

