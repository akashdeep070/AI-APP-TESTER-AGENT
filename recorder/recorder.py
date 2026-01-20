#!/usr/bin/env python3
"""
TestRun AI - Recorder Module (DroidRun Integration)
Captures UI events and screenshots using DroidRun's AdbTools.

Usage:
    python recorder/recorder.py --help
    python recorder/recorder.py start --device emulator-5554 --app com.example.app
    python recorder/recorder.py capture --action tap --element 5
    python recorder/recorder.py stop --output recordings/demo1.json
    python recorder/recorder.py demo --output recordings/demo1.json  # fallback demo

Requirements:
    pip install 'droidrun[google]'
    droidrun setup  # Install portal APK on device
"""

import argparse
import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Try to import DroidRun - graceful fallback if not installed
try:
    from droidrun import AdbTools
    DROIDRUN_AVAILABLE = True
except ImportError:
    DROIDRUN_AVAILABLE = False
    print("[Recorder] WARNING: DroidRun not installed. Using fallback mode.")
    print("[Recorder] Install with: pip install 'droidrun[google]'")


@dataclass
class SessionMeta:
    """Metadata about the recording session."""
    device: str
    app: str
    os_version: str = "android-13"
    screen_width: int = 1080
    screen_height: int = 2400


@dataclass
class UIElement:
    """Represents a UI element on screen."""
    index: int
    text: str
    resource_id: str
    class_name: str
    bounds: str  # "[left,top][right,bottom]"
    content_desc: str = ""
    clickable: bool = False
    

@dataclass
class ActionEvent:
    """A single recorded action event."""
    ts: int
    type: str  # tap, input, swipe, screenshot, navigate
    element_index: Optional[int] = None  # Index from UI state
    element_id: Optional[str] = None  # resource-id if available
    element_text: Optional[str] = None  # Text label
    coordinates: Optional[Dict[str, int]] = None  # {"x": int, "y": int}
    value: Optional[str] = None  # For text input actions
    screenshot: Optional[str] = None  # Screenshot path
    ui_state_before: Optional[List[Dict]] = None  # UI elements before action


@dataclass
class Recording:
    """Complete recording session."""
    session_id: str
    meta: SessionMeta
    events: List[ActionEvent] = field(default_factory=list)


# Global session state
_current_session: Optional[Recording] = None
_screenshot_counter: int = 0
_adb_tools: Optional[Any] = None  # DroidRun AdbTools instance


async def init_droidrun(device_id: str = "emulator-5554") -> Optional[Any]:
    """
    Initialize DroidRun AdbTools connection to device.
    
    Args:
        device_id: ADB device identifier
        
    Returns:
        AdbTools instance or None if not available
    """
    global _adb_tools
    
    if not DROIDRUN_AVAILABLE:
        print("[Recorder] DroidRun not available, using fallback mode")
        return None
    
    try:
        _adb_tools = AdbTools(serial=device_id)
        print(f"[Recorder] Connected to device: {device_id}")
        return _adb_tools
    except Exception as e:
        print(f"[Recorder] ERROR: Failed to connect to device: {e}")
        return None


async def get_ui_state() -> List[Dict[str, Any]]:
    """
    Get current UI state from device using DroidRun.
    
    Returns:
        List of UI element dictionaries
    """
    global _adb_tools
    
    if _adb_tools is None:
        return []
    
    try:
        # DroidRun's get_state() returns a tuple:
        # (description_str, screenshot_str, elements_list, metadata_dict)
        state = await _adb_tools.get_state()
        
        # Parse state - handle both tuple and list formats
        elements = []
        raw_elements = []
        
        if isinstance(state, tuple) and len(state) >= 3:
            # New API: tuple format
            raw_elements = state[2] if isinstance(state[2], list) else []
        elif isinstance(state, list):
            # Legacy API: direct list
            raw_elements = state
        
        for elem in raw_elements:
            if isinstance(elem, dict):
                elements.append({
                    "index": elem.get("index", len(elements)),
                    "text": elem.get("text", ""),
                    "resource_id": elem.get("resourceId", elem.get("resource-id", "")),
                    "class_name": elem.get("className", elem.get("class", "")),
                    "bounds": elem.get("bounds", ""),
                    "content_desc": elem.get("content-desc", ""),
                    "clickable": elem.get("clickable", False)
                })
        
        print(f"[Recorder] Found {len(elements)} UI elements")
        return elements
        
    except Exception as e:
        print(f"[Recorder] ERROR getting UI state: {e}")
        return []


async def capture_screenshot_droidrun(output_path: str) -> bool:
    """
    Capture screenshot using DroidRun.
    
    Args:
        output_path: Local path to save screenshot
        
    Returns:
        True if successful
    """
    global _adb_tools
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    if _adb_tools is not None:
        try:
            await _adb_tools.screenshot(output_path)
            print(f"[Recorder] Screenshot saved: {output_path}")
            return True
        except Exception as e:
            print(f"[Recorder] DroidRun screenshot failed: {e}, trying adb fallback")
    
    # Fallback to direct adb
    return capture_screenshot_adb("emulator-5554", output_path)


def capture_screenshot_adb(device_id: str, output_path: str) -> bool:
    """
    Fallback: Capture screenshot via adb subprocess.
    """
    try:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        
        remote_path = "/sdcard/testrun_screenshot.png"
        subprocess.run(
            ["adb", "-s", device_id, "shell", "screencap", "-p", remote_path],
            check=True, capture_output=True
        )
        subprocess.run(
            ["adb", "-s", device_id, "pull", remote_path, output_path],
            check=True, capture_output=True
        )
        subprocess.run(
            ["adb", "-s", device_id, "shell", "rm", remote_path],
            capture_output=True
        )
        print(f"[Recorder] Screenshot (adb): {output_path}")
        return True
    except Exception as e:
        print(f"[Recorder] ADB screenshot failed: {e}")
        return False


def get_device_info(device_id: str) -> dict:
    """Get device information via adb."""
    info = {"device": device_id, "os_version": "android-13", 
            "screen_width": 1080, "screen_height": 2400}
    
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.sdk"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            sdk = result.stdout.strip()
            info["os_version"] = f"android-{sdk}"
        
        # Get screen size
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "wm", "size"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and "x" in result.stdout:
            # Parse "Physical size: 1080x2400"
            size_str = result.stdout.split(":")[-1].strip()
            w, h = size_str.split("x")
            info["screen_width"] = int(w)
            info["screen_height"] = int(h)
    except Exception:
        pass
    
    return info


async def start_session(
    device_id: str,
    app_package: str,
    session_id: Optional[str] = None
) -> Recording:
    """
    Start a new recording session with DroidRun.
    """
    global _current_session, _screenshot_counter, _adb_tools
    
    if session_id is None:
        session_id = f"session_{int(time.time())}"
    
    # Initialize DroidRun
    await init_droidrun(device_id)
    
    device_info = get_device_info(device_id)
    
    meta = SessionMeta(
        device=device_id,
        app=app_package,
        os_version=device_info.get("os_version", "android-13"),
        screen_width=device_info.get("screen_width", 1080),
        screen_height=device_info.get("screen_height", 2400)
    )
    
    _current_session = Recording(
        session_id=session_id,
        meta=meta,
        events=[]
    )
    _screenshot_counter = 0
    
    # Create session directory for screenshots
    session_dir = PROJECT_ROOT / "artifacts" / session_id / "screens"
    os.makedirs(session_dir, exist_ok=True)
    
    print(f"[Recorder] Session started: {session_id}")
    print(f"[Recorder] Device: {device_id}, App: {app_package}")
    print(f"[Recorder] DroidRun: {'Connected' if _adb_tools else 'Fallback mode'}")
    
    return _current_session


async def record_action(
    action_type: str,
    element_index: Optional[int] = None,
    value: Optional[str] = None,
    coordinates: Optional[Dict[str, int]] = None
) -> Optional[ActionEvent]:
    """
    Record a single action with UI state and screenshot.
    
    Args:
        action_type: Type of action (tap, input, swipe, screenshot)
        element_index: UI element index from get_state()
        value: Value for input actions
        coordinates: {"x": int, "y": int} for coordinate-based actions
        
    Returns:
        Recorded ActionEvent
    """
    global _current_session, _screenshot_counter
    
    if _current_session is None:
        print("[Recorder] ERROR: No active session")
        return None
    
    _screenshot_counter += 1
    screenshot_name = f"screens/{_screenshot_counter:04d}.png"
    screenshot_path = str(
        PROJECT_ROOT / "artifacts" / _current_session.session_id / screenshot_name
    )
    
    # Get UI state before action
    ui_state = await get_ui_state()
    
    # Capture screenshot
    await capture_screenshot_droidrun(screenshot_path)
    
    # Extract element info if index provided
    element_id = None
    element_text = None
    if element_index is not None and ui_state:
        for elem in ui_state:
            if elem.get("index") == element_index:
                element_id = elem.get("resource_id", "")
                element_text = elem.get("text", "")
                break
    
    event = ActionEvent(
        ts=int(time.time()),
        type=action_type,
        element_index=element_index,
        element_id=element_id if element_id else None,
        element_text=element_text if element_text else None,
        coordinates=coordinates,
        value=value,
        screenshot=screenshot_name,
        ui_state_before=[e for e in ui_state[:20]] if ui_state else None  # Limit to first 20
    )
    
    _current_session.events.append(event)
    
    element_desc = element_text or element_id or f"index:{element_index}" or "unknown"
    print(f"[Recorder] Recorded: {action_type} on '{element_desc}'")
    
    return event


async def perform_and_record_tap(element_index: int) -> Optional[ActionEvent]:
    """
    Perform a tap action using DroidRun and record it.
    
    This is the main method for recording real interactions.
    """
    global _adb_tools
    
    # Record the action first (captures before state)
    event = await record_action("tap", element_index=element_index)
    
    # Actually perform the tap if DroidRun is available
    if _adb_tools is not None:
        try:
            await _adb_tools.tap_by_index(element_index)
            print(f"[Recorder] Performed tap on element {element_index}")
        except Exception as e:
            print(f"[Recorder] WARNING: Tap failed: {e}")
    
    return event


async def perform_and_record_input(element_index: int, text: str) -> Optional[ActionEvent]:
    """
    Perform text input using DroidRun and record it.
    """
    global _adb_tools
    
    event = await record_action("input", element_index=element_index, value=text)
    
    if _adb_tools is not None:
        try:
            await _adb_tools.input_text(element_index, text)
            print(f"[Recorder] Input text to element {element_index}")
        except Exception as e:
            print(f"[Recorder] WARNING: Input failed: {e}")
    
    return event


def stop_session(output_file: str) -> Optional[str]:
    """
    Stop recording and save to JSON file.
    """
    global _current_session, _adb_tools
    
    if _current_session is None:
        print("[Recorder] ERROR: No active session")
        return None
    
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    # Convert to serializable dict
    def serialize_event(e: ActionEvent) -> dict:
        d = asdict(e)
        # Remove None values for cleaner JSON
        return {k: v for k, v in d.items() if v is not None}
    
    recording_dict = {
        "session_id": _current_session.session_id,
        "meta": asdict(_current_session.meta),
        "events": [serialize_event(e) for e in _current_session.events]
    }
    
    with open(output_file, "w") as f:
        json.dump(recording_dict, f, indent=2)
    
    print(f"[Recorder] Session saved: {output_file}")
    print(f"[Recorder] Total events: {len(_current_session.events)}")
    
    _current_session = None
    _adb_tools = None
    
    return output_file


def create_demo_recording(output_file: str = "recordings/demo1.json") -> str:
    """
    Create a demo recording matching the new schema (no emulator required).
    """
    demo_recording = {
        "session_id": "demo1",
        "meta": {
            "device": "emulator-5554",
            "app": "com.demo.shop",
            "os_version": "android-13",
            "screen_width": 1080,
            "screen_height": 2400
        },
        "events": [
            {
                "ts": 1680000000,
                "type": "tap",
                "element_index": 0,
                "element_id": "com.demo.shop:id/email_field",
                "element_text": "Email",
                "screenshot": "screens/0001.png"
            },
            {
                "ts": 1680000001,
                "type": "input",
                "element_index": 0,
                "element_id": "com.demo.shop:id/email_field",
                "element_text": "Email",
                "value": "test@example.com",
                "screenshot": "screens/0002.png"
            },
            {
                "ts": 1680000002,
                "type": "tap",
                "element_index": 1,
                "element_id": "com.demo.shop:id/password_field",
                "element_text": "Password",
                "screenshot": "screens/0003.png"
            },
            {
                "ts": 1680000003,
                "type": "input",
                "element_index": 1,
                "element_id": "com.demo.shop:id/password_field",
                "element_text": "Password",
                "value": "password123",
                "screenshot": "screens/0004.png"
            },
            {
                "ts": 1680000004,
                "type": "tap",
                "element_index": 2,
                "element_id": "com.demo.shop:id/login_button",
                "element_text": "Login",
                "screenshot": "screens/0005.png"
            }
        ]
    }
    
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(demo_recording, f, indent=2)
    
    print(f"[Recorder] Demo recording created: {output_file}")
    return output_file


async def interactive_record_session(device_id: str, app_package: str, session_id: str):
    """
    Interactive recording session - user enters commands to record actions.
    
    TODO: Replace with GUI-based recording in Streamlit
    """
    await start_session(device_id, app_package, session_id)
    
    print("\n" + "=" * 60)
    print("Interactive Recording Mode")
    print("Commands:")
    print("  state          - Show current UI elements")
    print("  tap <index>    - Tap element by index")
    print("  input <index> <text> - Input text to element")
    print("  screenshot     - Capture screenshot only")
    print("  stop           - Stop and save recording")
    print("=" * 60 + "\n")
    
    while True:
        try:
            cmd = input("[Recorder] > ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split(maxsplit=2)
            action = parts[0].lower()
            
            if action == "state":
                elements = await get_ui_state()
                for elem in elements[:15]:  # Show first 15
                    print(f"  [{elem['index']}] {elem['text'] or elem['resource_id'] or elem['class_name']}")
                    
            elif action == "tap" and len(parts) >= 2:
                idx = int(parts[1])
                await perform_and_record_tap(idx)
                
            elif action == "input" and len(parts) >= 3:
                idx = int(parts[1])
                text = parts[2]
                await perform_and_record_input(idx, text)
                
            elif action == "screenshot":
                await record_action("screenshot")
                
            elif action == "stop":
                output_file = f"recordings/{session_id}.json"
                stop_session(output_file)
                break
                
            else:
                print(f"Unknown command: {cmd}")
                
        except KeyboardInterrupt:
            print("\n[Recorder] Interrupted, saving...")
            stop_session(f"recordings/{session_id}.json")
            break
        except Exception as e:
            print(f"[Recorder] Error: {e}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestRun AI Recorder - Capture test sessions with DroidRun"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start interactive recording")
    start_parser.add_argument("--device", "-d", default="emulator-5554")
    start_parser.add_argument("--app", "-a", default="com.example.app")
    start_parser.add_argument("--session-id", "-s", default=None)
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Create demo recording")
    demo_parser.add_argument("--output", "-o", default="recordings/demo1.json")
    
    # Screenshot command
    screenshot_parser = subparsers.add_parser("screenshot", help="Capture single screenshot")
    screenshot_parser.add_argument("--device", "-d", default="emulator-5554")
    screenshot_parser.add_argument("--output", "-o", default="artifacts/screenshot.png")
    
    # State command - show UI elements
    state_parser = subparsers.add_parser("state", help="Show current UI state")
    state_parser.add_argument("--device", "-d", default="emulator-5554")
    
    args = parser.parse_args()
    
    if args.command == "start":
        session_id = args.session_id or f"session_{int(time.time())}"
        asyncio.run(interactive_record_session(args.device, args.app, session_id))
        
    elif args.command == "demo":
        create_demo_recording(args.output)
        
    elif args.command == "screenshot":
        capture_screenshot_adb(args.device, args.output)
        
    elif args.command == "state":
        async def show_state():
            await init_droidrun(args.device)
            elements = await get_ui_state()
            print(f"\nUI Elements ({len(elements)} found):")
            for elem in elements[:20]:
                clickable = "✓" if elem.get("clickable") else " "
                text = elem.get("text") or elem.get("resource_id") or elem.get("class_name")
                print(f"  [{elem['index']:2d}] [{clickable}] {text[:50]}")
        asyncio.run(show_state())
        
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python recorder/recorder.py demo")
        print("  python recorder/recorder.py start --device emulator-5554 --app com.example.app")
        print("  python recorder/recorder.py state --device emulator-5554")


if __name__ == "__main__":
    main()
