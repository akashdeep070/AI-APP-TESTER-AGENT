#!/usr/bin/env python3
"""
TestRun AI - Test Generator Module (Groq API Integration)
Converts recording JSON into runnable DroidRun Python scripts using LLM.

Uses Groq API with moonshotai/kimi-k2-instruct model for intelligent test generation.

Usage:
    python generator/generate.py --help
    python generator/generate.py --input recordings/demo1.json --output artifacts/demo1_test.py
    python generator/generate.py --input recordings/demo1.json --use-llm  # Enable LLM enhancement

Environment:
    GROQ_API_KEY - Required for LLM-powered generation
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from jinja2 import Environment, FileSystemLoader

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads from .env in project root
except ImportError:
    pass  # dotenv not installed, use system environment

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_DIR = Path(__file__).parent / "templates"

# =============================================================================
# GROQ API CONFIGURATION
# To use a different model, change the MODEL constant below.
# Supported models on Groq: https://console.groq.com/docs/models
# =============================================================================
GROQ_MODEL = "groq/compound"  # Primary model for test generation
# Alternative models (uncomment to switch):
# GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
# GROQ_MODEL = "moonshotai/kimi-k2-instruct"

# Try to import Groq client
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("[Generator] WARNING: Groq client not installed. LLM features disabled.")
    print("[Generator] Install with: pip install groq")


def get_groq_client() -> Optional[Any]:
    """
    Get Groq client instance with API key from environment.
    
    Returns:
        Groq client or None if not available/configured
    """
    if not GROQ_AVAILABLE:
        return None
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[Generator] WARNING: GROQ_API_KEY not set. LLM features disabled.")
        return None
    
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        print(f"[Generator] ERROR: Failed to initialize Groq client: {e}")
        return None


def enhance_recording_with_llm(
    recording: Dict[str, Any],
    client: Any
) -> Dict[str, Any]:
    """
    Use LLM to enhance recording with better element selectors and descriptions.
    
    Args:
        recording: Original recording dictionary
        client: Groq client instance
        
    Returns:
        Enhanced recording with improved selectors and descriptions
    """
    events = recording.get("events", [])
    if not events:
        return recording
    
    # Build prompt for LLM
    prompt = f"""You are a mobile test automation expert. Analyze this recorded test session and enhance it.

## Recording Data
App: {recording.get('meta', {}).get('app', 'unknown')}
Device: {recording.get('meta', {}).get('device', 'unknown')}

## Recorded Events
{json.dumps(events, indent=2)}

## Task
For each event, provide:
1. A better human-readable description of what the action does
2. Suggested assertion to verify the action succeeded
3. Any recommended wait conditions before the action

Respond ONLY with a valid JSON array where each item has:
{{
  "event_index": <original index>,
  "description": "<human readable description>",
  "assertion": "<what to verify after action>",
  "wait_condition": "<optional wait before action>"
}}
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a mobile test automation expert. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more deterministic output
            max_tokens=2000
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            enhancements = json.loads(content.strip())
            
            # Apply enhancements to events
            for enhancement in enhancements:
                idx = enhancement.get("event_index", -1)
                if 0 <= idx < len(events):
                    events[idx]["llm_description"] = enhancement.get("description", "")
                    events[idx]["llm_assertion"] = enhancement.get("assertion", "")
                    events[idx]["llm_wait"] = enhancement.get("wait_condition", "")
            
            print(f"[Generator] LLM enhanced {len(enhancements)} events")
            
        except json.JSONDecodeError as e:
            print(f"[Generator] WARNING: Failed to parse LLM response: {e}")
            
    except Exception as e:
        print(f"[Generator] ERROR: LLM enhancement failed: {e}")
    
    recording["events"] = events
    return recording


def generate_test_description_with_llm(
    recording: Dict[str, Any],
    client: Any
) -> str:
    """
    Use LLM to generate a natural language test description.
    
    Args:
        recording: Recording dictionary
        client: Groq client instance
        
    Returns:
        Markdown test description
    """
    prompt = f"""Generate a professional test case description for this mobile app test recording.

## Recording Data
Session ID: {recording.get('session_id', 'unknown')}
App: {recording.get('meta', {}).get('app', 'unknown')}
Device: {recording.get('meta', {}).get('device', 'unknown')}

## Recorded Events
{json.dumps(recording.get('events', []), indent=2)}

## Output Format
Generate a markdown document with:
1. Test Case Title
2. Objective (what the test validates)
3. Preconditions
4. Step-by-step test procedure
5. Expected results
6. Notes/recommendations

Keep it concise and professional.
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a QA engineer writing test documentation. Be concise and professional."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"[Generator] ERROR: LLM description generation failed: {e}")
        return generate_test_description_basic(recording)


def generate_test_assertions_with_llm(
    recording: Dict[str, Any],
    client: Any
) -> List[Dict[str, str]]:
    """
    Use LLM to generate assertions for each test step.
    
    Args:
        recording: Recording dictionary
        client: Groq client instance
        
    Returns:
        List of assertion dictionaries
    """
    prompt = f"""For this mobile app test recording, generate Python assertions that can verify each step succeeded.

## App Context
App: {recording.get('meta', {}).get('app', 'unknown')}

## Events to Generate Assertions For
{json.dumps(recording.get('events', []), indent=2)}

## Output Format
Respond with a JSON array where each item has:
{{
  "step": <step number>,
  "assertion_code": "<Python assertion code>",
  "description": "<what this assertion checks>"
}}

Generate realistic assertions that check for:
- Element visibility after navigation
- Text content after input
- Screen state after tap actions
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a test automation engineer. Generate Python assertions. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        return json.loads(content.strip())
        
    except Exception as e:
        print(f"[Generator] ERROR: LLM assertion generation failed: {e}")
        return []


def load_recording(json_path: str) -> Dict[str, Any]:
    """Load a recording JSON file."""
    with open(json_path, "r") as f:
        recording = json.load(f)
    
    print(f"[Generator] Loaded recording: {json_path}")
    print(f"[Generator] Session ID: {recording.get('session_id', 'unknown')}")
    print(f"[Generator] Events: {len(recording.get('events', []))}")
    
    return recording


def validate_recording(recording: Dict[str, Any]) -> bool:
    """Validate recording schema for DroidRun generation."""
    required_fields = ["session_id", "meta", "events"]
    for field in required_fields:
        if field not in recording:
            print(f"[Generator] ERROR: Missing required field: {field}")
            return False
    
    if not recording["events"]:
        print("[Generator] WARNING: No events in recording")
    
    return True


def generate_droidrun_script(
    recording: Dict[str, Any],
    use_llm: bool = False
) -> str:
    """
    Generate a DroidRun Python script from a recording.
    
    Args:
        recording: Parsed recording dictionary
        use_llm: Whether to use LLM for enhancement
        
    Returns:
        Generated Python script as a string
    """
    # Optionally enhance with LLM
    if use_llm:
        client = get_groq_client()
        if client:
            print(f"[Generator] Using LLM: {GROQ_MODEL}")
            recording = enhance_recording_with_llm(recording, client)
        else:
            print("[Generator] LLM not available, using template-only generation")
    
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Add custom filters
    env.filters['escape_string'] = lambda s: s.replace('"', '\\"').replace('\n', '\\n') if s else ""
    
    try:
        template = env.get_template("droidrun_template.py.j2")
    except Exception as e:
        print(f"[Generator] Template not found, using inline template: {e}")
        return _generate_inline(recording)
    
    # Prepare events with proper action method selection
    events = []
    for event in recording.get("events", []):
        action = {
            "type": event.get("type", "unknown"),
            "element_index": event.get("element_index"),
            "element_id": event.get("element_id", ""),
            "element_text": event.get("element_text", ""),
            "value": event.get("value", ""),
            "coordinates": event.get("coordinates"),
            "screenshot": event.get("screenshot", ""),
            # LLM enhancements (if available)
            "llm_description": event.get("llm_description", ""),
            "llm_assertion": event.get("llm_assertion", ""),
            "llm_wait": event.get("llm_wait", "")
        }
        
        # Determine best selector method
        if action["element_id"]:
            action["selector_type"] = "resource_id"
            action["selector_value"] = action["element_id"]
        elif action["element_index"] is not None:
            action["selector_type"] = "index"
            action["selector_value"] = action["element_index"]
        elif action["coordinates"]:
            action["selector_type"] = "coordinates"
            action["selector_value"] = action["coordinates"]
        else:
            action["selector_type"] = "text"
            action["selector_value"] = action["element_text"]
        
        events.append(action)
    
    # Render template
    script = template.render(
        session_id=recording.get("session_id", "unknown"),
        meta=recording.get("meta", {}),
        events=events,
        use_llm=use_llm
    )
    
    return script


def _generate_inline(recording: Dict[str, Any]) -> str:
    """Fallback inline script generation."""
    session_id = recording.get("session_id", "unknown")
    meta = recording.get("meta", {})
    events = recording.get("events", [])
    
    lines = [
        '#!/usr/bin/env python3',
        '"""',
        f'TestRun AI - Generated Test Script',
        f'Session: {session_id}',
        f'App: {meta.get("app", "unknown")}',
        f'Device: {meta.get("device", "unknown")}',
        '"""',
        '',
        'import asyncio',
        'import sys',
        'from pathlib import Path',
        '',
        '# DroidRun imports',
        'try:',
        '    from droidrun import AdbTools',
        '    DROIDRUN_AVAILABLE = True',
        'except ImportError:',
        '    DROIDRUN_AVAILABLE = False',
        '    print("[Test] WARNING: DroidRun not installed, using mock mode")',
        '',
        f'DEVICE_ID = "{meta.get("device", "emulator-5554")}"',
        f'APP_PACKAGE = "{meta.get("app", "com.example.app")}"',
        f'SESSION_ID = "{session_id}"',
        '',
        '',
        'async def run_test() -> bool:',
        '    """Execute the recorded test steps."""',
        '    print("=" * 60)',
        f'    print("[Test] Starting: {session_id}")',
        f'    print("[Test] App: {meta.get("app", "unknown")}")',
        '    print("=" * 60)',
        '',
        '    if DROIDRUN_AVAILABLE:',
        '        tools = AdbTools(serial=DEVICE_ID)',
        '    else:',
        '        tools = None',
        '',
        '    try:',
    ]
    
    for i, event in enumerate(events):
        event_type = event.get("type", "unknown")
        element_id = event.get("element_id", "")
        element_idx = event.get("element_index")
        value = event.get("value", "")
        text = event.get("element_text", "")
        llm_desc = event.get("llm_description", "")
        
        desc = llm_desc or text or element_id or f"index:{element_idx}"
        lines.append(f'        # Step {i + 1}: {desc}')
        lines.append(f'        print(f"[Test] Step {i + 1}/{len(events)}: {event_type}")')
        
        if event_type == "tap":
            if element_idx is not None:
                lines.append(f'        if tools: await tools.tap_by_index({element_idx})')
            lines.append('        await asyncio.sleep(0.5)')
        elif event_type == "input":
            if element_idx is not None:
                lines.append(f'        if tools: await tools.input_text({element_idx}, "{value}")')
            lines.append('        await asyncio.sleep(0.5)')
        
        lines.append('')
    
    lines.extend([
        '        print("=" * 60)',
        '        print("[Test] All steps completed!")',
        '        return True',
        '',
        '    except Exception as e:',
        '        print(f"[Test] ERROR: {e}")',
        '        return False',
        '',
        '',
        'def main():',
        '    result = asyncio.run(run_test())',
        '    print("✅ PASS" if result else "❌ FAIL")',
        '    sys.exit(0 if result else 1)',
        '',
        '',
        'if __name__ == "__main__":',
        '    main()',
    ])
    
    return '\n'.join(lines)


def save_script(script: str, output_path: str) -> str:
    """Save the generated script to a file."""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(script)
    
    os.chmod(output_path, 0o755)
    
    print(f"[Generator] Script saved: {output_path}")
    return output_path


def generate_test_description_basic(recording: Dict[str, Any]) -> str:
    """Generate a basic natural language test description (no LLM)."""
    session_id = recording.get("session_id", "unknown")
    meta = recording.get("meta", {})
    events = recording.get("events", [])
    
    lines = [
        f"# Test: {session_id}",
        "",
        f"**App**: {meta.get('app', 'unknown')}",
        f"**Device**: {meta.get('device', 'unknown')}",
        f"**OS**: {meta.get('os_version', 'unknown')}",
        "",
        "## Steps",
        "",
    ]
    
    for i, event in enumerate(events):
        event_type = event.get("type", "unknown")
        element_id = event.get("element_id", "")
        element_text = event.get("element_text", "")
        value = event.get("value")
        llm_desc = event.get("llm_description", "")
        
        if llm_desc:
            lines.append(f"{i + 1}. {llm_desc}")
        elif event_type == "tap":
            element_desc = element_text or element_id or "element"
            lines.append(f"{i + 1}. Tap on **{element_desc}**")
        elif event_type == "input":
            element_desc = element_text or element_id or "element"
            lines.append(f'{i + 1}. Enter "{value}" into **{element_desc}**')
        else:
            lines.append(f"{i + 1}. {event_type}")
    
    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestRun AI Generator - Convert recordings to DroidRun scripts"
    )
    
    parser.add_argument("--input", "-i", required=True, help="Recording JSON file")
    parser.add_argument("--output", "-o", help="Output script path")
    parser.add_argument("--description", "-d", action="store_true", help="Generate markdown description")
    parser.add_argument("--use-llm", action="store_true", help=f"Use LLM ({GROQ_MODEL}) for enhancement")
    
    args = parser.parse_args()
    
    # Load recording
    recording = load_recording(args.input)
    
    if not validate_recording(recording):
        print("[Generator] ERROR: Invalid recording format")
        exit(1)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        session_id = recording.get("session_id", "test")
        output_path = f"artifacts/{session_id}_test.py"
    
    # Generate and save script
    script = generate_droidrun_script(recording, args.use_llm)
    save_script(script, output_path)
    
    # Optionally generate description
    if args.description:
        desc_path = output_path.replace(".py", "_description.md")
        
        if args.use_llm:
            client = get_groq_client()
            if client:
                description = generate_test_description_with_llm(recording, client)
            else:
                description = generate_test_description_basic(recording)
        else:
            description = generate_test_description_basic(recording)
        
        with open(desc_path, "w") as f:
            f.write(description)
        print(f"[Generator] Description saved: {desc_path}")
    
    print("[Generator] Done!")


if __name__ == "__main__":
    main()
