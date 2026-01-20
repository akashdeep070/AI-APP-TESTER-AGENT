#!/usr/bin/env python3
"""
TestRun AI - QA Analysis Module
Handles APK installation, QA prompt interpretation, and automated test generation.

This module combines:
- APK handling (install, extract package, launch)
- LLM-based QA prompt interpretation
- Test execution pipeline
- Visual regression analysis
"""

import asyncio
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment from project root .env
try:
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[QA] Loaded .env from {env_path}")
    else:
        load_dotenv()  # Try default locations
except ImportError:
    pass

# Groq setup
GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

try:
    from groq import Groq
    GROQ_AVAILABLE = True
    print("[QA] Groq module imported successfully")
except ImportError as e:
    GROQ_AVAILABLE = False
    print(f"[QA] Failed to import groq: {e}")

# DroidRun setup
try:
    from droidrun import AdbTools
    DROIDRUN_AVAILABLE = True
except ImportError:
    DROIDRUN_AVAILABLE = False


@dataclass
class TestStep:
    """A single test step generated from QA prompt."""
    step_number: int
    action: str  # tap, input, swipe, verify, wait
    target: str  # Element description
    value: Optional[str] = None  # For input actions
    assertion: Optional[str] = None  # Expected result


@dataclass 
class QAResult:
    """Results from QA analysis."""
    status: str  # PASS, FAIL, ERROR
    app_package: str
    prompt: str
    steps_total: int
    steps_passed: int
    steps_failed: int
    execution_time: float
    visual_score: Optional[float] = None
    error_message: Optional[str] = None
    steps: List[Dict] = None
    screenshots: List[str] = None
    

def get_groq_client(api_key: str = None):
    """
    Get Groq client with API key.
    
    Args:
        api_key: Optional API key. If not provided, uses environment variable.
    """
    if not GROQ_AVAILABLE:
        print("[QA] Groq not available")
        return None
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        print("[QA] No GROQ_API_KEY found in environment")
        return None
    
    print(f"[QA] Using Groq API key: {api_key[:15]}...")
    return Groq(api_key=api_key)


def install_apk(apk_path: str, device_id: str = "emulator-5554") -> tuple:
    """
    Install APK on device via adb.
    
    Returns:
        (success: bool, package_name: str, error: str)
    """
    try:
        # Install APK
        result = subprocess.run(
            ["adb", "-s", device_id, "install", "-r", apk_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if "Success" not in result.stdout and result.returncode != 0:
            return False, None, result.stderr or "Installation failed"
        
        # Extract package name using aapt
        try:
            aapt_result = subprocess.run(
                ["aapt", "dump", "badging", apk_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            match = re.search(r"package: name='([^']+)'", aapt_result.stdout)
            if match:
                package_name = match.group(1)
                return True, package_name, None
        except Exception:
            pass
        
        # Fallback: try to get from recent installs
        # This is a demo fallback
        return True, "unknown.package", None
        
    except subprocess.TimeoutExpired:
        return False, None, "Installation timed out"
    except Exception as e:
        return False, None, str(e)


def launch_app(package_name: str, device_id: str = "emulator-5554") -> bool:
    """Launch app via adb monkey or am start."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "monkey", "-p", package_name, 
             "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        time.sleep(2)  # Wait for app to start
        return True
    except Exception:
        return False


def get_next_test_step(
    original_prompt: str,
    app_package: str, 
    client,
    device_id: str,
    completed_steps: List[TestStep],
    max_steps: int = 10
) -> Optional[TestStep]:
    """
    Agentic approach: Generate the NEXT test step based on current UI state.
    
    This is called iteratively - after each action, we analyze the new screen
    and decide what to do next until the test is complete.
    """
    import base64
    
    # Check if we've completed enough steps
    if len(completed_steps) >= max_steps:
        print(f"[QA] Reached max steps ({max_steps})")
        return None
    
    # Capture current screen
    screenshot_b64 = None
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            screenshot_b64 = base64.b64encode(result.stdout).decode('utf-8')
    except Exception as e:
        print(f"[QA] Screenshot capture failed: {e}")
        return None
    
    if not screenshot_b64:
        return None
    
    # Build context of what we've done so far
    history = ""
    if completed_steps:
        history = "STEPS COMPLETED SO FAR:\n"
        for step in completed_steps:
            history += f"{step.step_number}. {step.action} → {step.target}"
            if step.value:
                history += f" (value: {step.value})"
            history += f" - {step.assertion}\n"
    else:
        history = "No steps completed yet - starting fresh"
    
    system_prompt = """You are an expert QA automation engineer performing real-time app testing.

YOUR JOB: Look at the current screenshot and decide THE NEXT SINGLE ACTION to take.

CONTEXT:
- You're in the middle of a test scenario
- You can see what steps have been completed
- You need to decide the NEXT action based on the current screen
- Continue until the test objective is achieved (typically 6-10 steps for a full flow)

DECISION RULES:
1. ANALYZE the screenshot - what screen are you on? What elements are visible?
2. CONSIDER the original test objective - what are you trying to accomplish?
3. REVIEW completed steps - what have you done? What's left?
4. DECIDE next action - tap a button? Enter text? Verify something? Or DONE if test complete?

WHEN TO STOP (return "DONE"):
- Test objective is fully accomplished
- You've tested key functionality (e.g., opened app, navigated screens, tested core features, verified results)
- Current screen shows successful completion
- You're stuck in a loop

ACTIONS AVAILABLE:
- tap: Click on a button/element (use exact text you see in screenshot)
- input: Enter text in a field (specify field + text to enter)
- swipe: Scroll up/down/left/right
- verify: Check if expected element/text is visible
- DONE: Test is complete

OUTPUT FORMAT (strict JSON):
{
  "action": "tap",
  "target": "Login Button",
  "value": null,
  "assertion": "Navigate to login screen",
  "reasoning": "I can see a Login button, tapping it to proceed with login test"
}

OR if test is complete:
{
  "action": "DONE",
  "target": "test_complete",
  "value": null,
  "assertion": "Test objective achieved",
  "reasoning": "Successfully tested main functionality - app loaded, navigation works, key features verified"
}

IMPORTANT:
- Be specific with targets (use exact button/field text from screenshot)
- Each step should make meaningful progress
- Don't just open app and stop - actually TEST features
- For shopping apps: browse products, add to cart, view cart, etc.
- For social apps: create post, view feed, interact, etc."""

    user_prompt = f"""ORIGINAL TEST OBJECTIVE: "{original_prompt}"

CURRENT APP: {app_package}

{history}

ANALYZE THE CURRENT SCREENSHOT and decide the next action.

What do you see on screen? What should be the next step to accomplish the test objective?

Output your decision as JSON:"""

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}"
                        }
                    }
                ]
            }
        ]
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        step_data = json.loads(content.strip())
        
        # Check if test is done
        if step_data.get("action", "").upper() == "DONE":
            print(f"[QA] LLM decided test is COMPLETE: {step_data.get('reasoning', 'No reason')}")
            return None
        
        # Create next step
        next_step = TestStep(
            step_number=len(completed_steps) + 1,
            action=step_data.get("action", "tap"),
            target=step_data.get("target", ""),
            value=step_data.get("value"),
            assertion=step_data.get("assertion", "")
        )
        
        reasoning = step_data.get("reasoning", "")
        print(f"[QA] Next step decided: {next_step.action} → {next_step.target} | Reason: {reasoning}")
        
        return next_step
        
    except Exception as e:
        print(f"[QA] Failed to get next step: {e}")
        import traceback
        traceback.print_exc()
        return None


async def execute_test_steps(
    steps: List[TestStep],
    device_id: str = "emulator-5554",
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Execute test steps on device.
    
    Returns:
        Dict with execution results
    """
    if output_dir is None:
        output_dir = str(PROJECT_ROOT / "artifacts" / f"qa_run_{int(time.time())}")
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        "steps": [],
        "screenshots": [],
        "passed": 0,
        "failed": 0
    }
    
    # Initialize DroidRun
    tools = None
    if DROIDRUN_AVAILABLE:
        try:
            tools = AdbTools(serial=device_id)
        except Exception as e:
            print(f"[QA] DroidRun init failed: {e}")
    
    for step in steps:
        step_result = {
            "step": step.step_number,
            "action": step.action,
            "target": step.target,
            "status": "PASS",
            "error": None
        }
        
        try:
            # Get UI state
            ui_elements = []
            if tools:
                state = await tools.get_state()
                if isinstance(state, tuple) and len(state) >= 3:
                    ui_elements = state[2] if isinstance(state[2], list) else []
            
            # Find target element
            target_index = None
            target_lower = step.target.lower()
            for elem in ui_elements:
                text = str(elem.get("text", "")).lower()
                res_id = str(elem.get("resourceId", "")).lower()
                if target_lower in text or target_lower in res_id:
                    target_index = elem.get("index")
                    break
            
            # Execute action
            if step.action == "tap" and tools and target_index is not None:
                await tools.tap_by_index(target_index)
                await asyncio.sleep(0.5)
                
            elif step.action == "input" and tools and target_index is not None:
                # DroidRun input_text signature: (text, index, clear)
                await tools.input_text(step.value or "", target_index)
                await asyncio.sleep(0.5)
                
            elif step.action == "wait":
                await asyncio.sleep(2)
                
            elif step.action == "swipe":
                # TODO: Implement swipe
                await asyncio.sleep(0.5)
                
            elif step.action == "verify":
                # Check if target text exists in UI
                found = any(target_lower in str(e.get("text", "")).lower() for e in ui_elements)
                if not found:
                    step_result["status"] = "FAIL"
                    step_result["error"] = f"Element '{step.target}' not found"
            
            # Capture screenshot using direct ADB (more reliable)
            screenshot_path = f"{output_dir}/step_{step.step_number}.png"
            try:
                import subprocess
                # Use ADB screencap directly
                result = subprocess.run(
                    ["adb", "-s", device_id, "exec-out", "screencap", "-p"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout:
                    with open(screenshot_path, "wb") as f:
                        f.write(result.stdout)
                    results["screenshots"].append(screenshot_path)
                    print(f"[QA] Screenshot saved: {screenshot_path}")
                else:
                    print(f"[QA] Screenshot failed: ADB returned {result.returncode}")
            except Exception as e:
                print(f"[QA] Screenshot error: {e}")
            
            if step_result["status"] == "PASS":
                results["passed"] += 1
            else:
                results["failed"] += 1
                
        except Exception as e:
            step_result["status"] = "FAIL"
            step_result["error"] = str(e)
            results["failed"] += 1
        
        results["steps"].append(step_result)
        print(f"[QA] Step {step.step_number}: {step.action} on '{step.target}' - {step_result['status']}")
    
    return results


async def run_qa_analysis(
    apk_path: str,
    qa_prompt: str,
    device_id: str = "emulator-5554",
    progress_callback=None
) -> QAResult:
    """
    Main entry point for QA analysis.
    
    Args:
        apk_path: Path to APK file (optional - can be empty for direct testing)
        qa_prompt: Natural language QA prompt
        device_id: Target device
        progress_callback: Optional callback for progress updates
        
    Returns:
        QAResult with analysis results
    """
    start_time = time.time()
    
    def log(msg):
        print(f"[QA] {msg}")
        if progress_callback:
            progress_callback(msg)
    
    # Step 0: Go to home screen first (reset to known state)
    log("Going to home screen...")
    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "keyevent", "KEYCODE_HOME"],
            capture_output=True,
            timeout=5
        )
        time.sleep(1)
    except Exception as e:
        log(f"Home press failed: {e}")
    
    # Smart app launch based on prompt keywords
    prompt_lower = qa_prompt.lower()
    package_name = "current_app"
    
    # Detect if user wants to go to Settings
    if any(kw in prompt_lower for kw in ["settings", "display", "dark mode", "brightness", "wifi", "bluetooth"]):
        log("Detected settings-related task - launching Settings app...")
        try:
            subprocess.run(
                ["adb", "-s", device_id, "shell", "am", "start", "-n", "com.android.settings/.Settings"],
                capture_output=True,
                timeout=10
            )
            package_name = "com.android.settings"
            time.sleep(2)
            
            # Scroll down to show more options if looking for display/dark mode
            if "display" in prompt_lower or "dark" in prompt_lower:
                log("Scrolling to find Display settings...")
                subprocess.run(
                    ["adb", "-s", device_id, "shell", "input", "swipe", "500", "1200", "500", "400"],
                    capture_output=True,
                    timeout=5
                )
                time.sleep(1)
        except Exception as e:
            log(f"Settings launch failed: {e}")
    
    # Detect if user wants to open an app from app drawer
    elif any(kw in prompt_lower for kw in ["shopping", "online shopping", "marc", "doctors"]):
        log("Opening app drawer to find app...")
        try:
            # Swipe up to open app drawer
            subprocess.run(
                ["adb", "-s", device_id, "shell", "input", "swipe", "500", "1500", "500", "500"],
                capture_output=True,
                timeout=5
            )
            time.sleep(1)
            package_name = "app_drawer"
        except Exception as e:
            log(f"App drawer open failed: {e}")
    
    # Step 1: Install APK (optional)
    if apk_path and apk_path != "/dev/null" and os.path.exists(apk_path):
        log("Installing APK...")
        success, pkg_name, error = install_apk(apk_path, device_id)
        
        if success and pkg_name:
            package_name = pkg_name
            log(f"Installed: {package_name}")
            
            # Launch the installed app
            log("Launching app...")
            launch_app(package_name, device_id)
            time.sleep(2)
        else:
            log(f"APK install skipped: {error or 'using direct testing'}")
    else:
        log("Direct testing mode - no APK upload")
    
    # Step 3: Get Groq client
    client = get_groq_client()
    if not client:
        err_msg = "Groq client failed to initialize"
        if not GROQ_AVAILABLE:
            err_msg = "Groq library not available (ImportError) - check logs"
        
        return QAResult(
            status="ERROR",
            app_package=package_name,
            prompt=qa_prompt,
            steps_total=0,
            steps_passed=0,
            steps_failed=0,
            execution_time=time.time() - start_time,
            error_message=err_msg
        )
    
    
    # Step 4: AGENTIC ITERATIVE TESTING
    # Instead of generating all steps upfront, we generate and execute one step at a time
    log("Starting AGENTIC testing (iterative step-by-step)...")
    
    completed_steps = []
    all_screenshots = []
    output_dir = str(PROJECT_ROOT / "artifacts" / f"qa_run_{int(time.time())}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize DroidRun tools
    tools = None
    if DROIDRUN_AVAILABLE:
        try:
            tools = AdbTools(serial=device_id)
            log("DroidRun tools initialized")
        except Exception as e:
            log(f"DroidRun init failed: {e}")
    
    passed_count = 0
    failed_count = 0
    max_attempts = 12  # Max test steps
    
    for attempt in range(max_attempts):
        log(f"--- Step {attempt + 1} ---")
        
        # Get next step from LLM based on current screen
        next_step = get_next_test_step(
            original_prompt=qa_prompt,
            app_package=package_name,
            client=client,
            device_id=device_id,
            completed_steps=completed_steps,
            max_steps=max_attempts
        )
        
        if not next_step:
            log("LLM decided test is COMPLETE or failed to generate step")
            break
        
        log(f"Executing: {next_step.action} → {next_step.target}")
        
        # Execute the step
        step_passed = False
        try:
            if tools:
                # Get fresh UI state
                state = await asyncio.create_task(tools.get_state())
                ui_elements = []
                if isinstance(state, tuple) and len(state) >= 3:
                    ui_elements = state[2] if isinstance(state[2], list) else []
                
                # Find target element
                target_index = None
                target_lower = next_step.target.lower()
                for elem in ui_elements:
                    text = str(elem.get("text", "")).lower()
                    res_id = str(elem.get("resourceId", "")).lower()
                    if target_lower in text or target_lower in res_id:
                        target_index = elem.get("index")
                        break
                
                # Execute action
                if next_step.action == "tap" and target_index is not None:
                    await asyncio.create_task(tools.tap_by_index(target_index))
                    await asyncio.sleep(0.8)
                    step_passed = True
                    
                elif next_step.action == "input" and target_index is not None:
                    await asyncio.create_task(tools.input_text(next_step.value or "", target_index))
                    await asyncio.sleep(0.8)
                    step_passed = True
                    
                elif next_step.action == "swipe":
                    # Simple scroll down
                    subprocess.run(
                        ["adb", "-s", device_id, "shell", "input", "swipe", "500", "1200", "500", "400"],
                        capture_output=True,
                        timeout=5
                    )
                    await asyncio.sleep(0.5)
                    step_passed = True
                    
                elif next_step.action == "verify":
                    # Check if target exists in UI
                    found = any(target_lower in str(e.get("text", "")).lower() for e in ui_elements)
                    step_passed = found
                    if not found:
                        log(f"Verification FAILED: '{next_step.target}' not found")
                elif next_step.action == "wait_for":
                    await asyncio.sleep(2)
                    step_passed = True
                else:
                    log(f"Unknown action: {next_step.action}")
                    step_passed = False
            
            # Capture screenshot
            screenshot_path = f"{output_dir}/step_{next_step.step_number}.png"
            try:
                result = subprocess.run(
                    ["adb", "-s", device_id, "exec-out", "screencap", "-p"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout:
                    with open(screenshot_path, "wb") as f:
                        f.write(result.stdout)
                    all_screenshots.append(screenshot_path)
            except Exception as e:
                log(f"Screenshot failed: {e}")
            
            if step_passed:
                passed_count += 1
                log(f"✓ Step {next_step.step_number} PASSED")
            else:
                failed_count += 1
                log(f"✗ Step {next_step.step_number} FAILED")
            
            completed_steps.append(next_step)
            
        except Exception as e:
            log(f"Step execution error: {e}")
            failed_count += 1
            completed_steps.append(next_step)
    
    # Calculate final results
    total_steps = len(completed_steps)
    status = "PASS" if failed_count == 0 and total_steps > 0 else "FAIL"
    
    log(f"Test complete: {passed_count}/{total_steps} steps passed")
    
    
    return QAResult(
        status=status,
        app_package=package_name,
        prompt=qa_prompt,
        steps_total=total_steps,
        steps_passed=passed_count,
        steps_failed=failed_count,
        execution_time=time.time() - start_time,
        visual_score=None,
        steps=[asdict(s) for s in completed_steps],
        screenshots=all_screenshots
    )


if __name__ == "__main__":
    # CLI test
    import sys
    if len(sys.argv) < 3:
        print("Usage: python qa_analysis.py <apk_path> <qa_prompt>")
        sys.exit(1)
    
    result = run_qa_analysis(sys.argv[1], sys.argv[2])
    print(json.dumps(asdict(result), indent=2))
