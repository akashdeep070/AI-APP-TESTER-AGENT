# Technical Requirements Document (TRD)
## Project: TestRun AI
### DroidRun-powered Automated Mobile Testing Pipeline

---

## 1. Overview

TestRun AI is a developer-focused system that converts **manual mobile app testing** into **automated, repeatable DroidRun test suites**.  
The system records a QA engineer’s interactions on a mobile app, generates executable DroidRun scripts, replays them for regression testing, detects UI regressions, and auto-produces bug reports.

This document defines the technical requirements for building the MVP in **Cursor** during a hackathon.

---

## 2. Goals

- Eliminate repetitive manual mobile testing
- Auto-generate reliable regression tests from real user behavior
- Detect UI regressions visually and functionally
- Provide a demo-ready web interface for judges
- Keep the system simple, deterministic, and demo-safe

---

## 3. In-Scope

- Manual test recorder
- Test script generator
- Test runner using DroidRun
- Visual regression detection
- Bug report generation
- Web-based demo UI
- Local emulator support
- Optional cloud execution using Mobilerun

---

## 4. Out of Scope

- Full SaaS authentication
- Billing and subscriptions
- Large-scale device farm orchestration
- Deep ML-based UI understanding
- Production-grade security hardening

---

## 5. Target Users

- Mobile app developers
- QA engineers
- Startup engineering teams
- Hackathon judges and evaluators

---

## 6. High-Level Architecture

Manual Tester
↓
Recorder (screenshots + actions)
↓
Recording JSON
↓
Generator (LLM + templates)
↓
DroidRun Script
↓
Runner (Emulator / Cloud)
↓
Artifacts + Screenshots
↓
Verifier (Visual Diff)
↓
Bug Report + Dashboard

yaml
Copy code

---

## 7. Functional Requirements

### FR-1: Recorder

- Capture screenshots during manual testing
- Capture user actions:
  - Tap
  - Text input
  - Navigation
- Store session metadata:
  - Device
  - OS version
  - App package
- Output a structured JSON recording

---

### FR-2: Test Generator

- Convert recording JSON into:
  - Executable DroidRun Python script
  - Natural language test description
- Prefer element-based selectors over coordinates
- Support deterministic replays

---

### FR-3: Test Runner

- Execute generated DroidRun scripts
- Support Android emulator execution
- Capture:
  - Logs
  - Screenshots
  - Execution status
- Return PASS or FAIL status

---

### FR-4: Regression Detection

- Compare baseline vs current screenshots
- Detect:
  - Layout changes
  - Missing elements
  - Visual shifts
- Use SSIM or perceptual hashing
- Produce diff images

---

### FR-5: Bug Report Generator

- Auto-generate a bug report containing:
  - Title
  - Steps to reproduce
  - Screenshot diffs
  - Device metadata
  - Repro script
- Export as JSON or Markdown

---

### FR-6: Web Demo UI

- Single-page interface
- Actions:
  - Start recording
  - Stop recording
  - Generate tests
  - Run tests
- Display:
  - Generated test code
  - Screenshots
  - Regression diffs
  - Test results

---

## 8. Non-Functional Requirements

- Demo reliability above 90 percent
- End-to-end demo flow under 4 minutes
- Minimal setup steps
- Works fully on laptop with emulator
- Graceful fallback to pre-generated artifacts

---

## 9. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Automation | DroidRun |
| Recorder | adb + uiautomator or DroidRun hooks |
| Templating | Jinja2 |
| Visual Diff | Pillow, scikit-image |
| Web UI | Streamlit |
| LLM | moonshotai/kimi-k2-instruct |
| IDE | Cursor |
| Emulator | Android Studio AVD |
| Optional Cloud | Mobilerun |

---

## 10. Data Models

### Recording JSON

```json
{
  "session_id": "demo1",
  "meta": {
    "device": "emulator-5554",
    "app": "com.demo.shop",
    "os": "android-13"
  },
  "events": [
    {
      "ts": 1680000000,
      "type": "tap",
      "element": "login_button",
      "screenshot": "screens/0001.png"
    }
  ]
}
Bug Report JSON
json
Copy code
{
  "id": "BUG-001",
  "title": "Login button hidden",
  "steps": [
    "Launch app",
    "Enter email",
    "Tap login"
  ],
  "diff": "diffs/login_diff.png",
  "device": "Pixel Emulator",
  "repro_script": "demo1.generated.py"
}
11. LLM Usage Requirements
Primary model: moonshotai/kimi-k2-instruct

Token budget optimized under 500 tokens per request

Cache all generated outputs

Pre-generate demo artifacts

Local fallback model if API quota is exceeded

12. Acceptance Criteria
Manual test can be recorded successfully

Generated DroidRun script replays without human input

Regression is detected after UI change

Bug report is auto-generated

Demo can be completed without internet dependency

13. Demo Flow
Start Streamlit UI

Start recording

Perform manual test on emulator

Stop recording

Generate test script

Run automated test

Introduce UI change

Run regression test

Show visual diff and bug report

14. Risks and Mitigation
Risk	Mitigation
Emulator crash	Backup demo video
LLM quota exceeded	Pre-generated outputs
UI flakiness	Stable demo app
Network failure	Local execution

15. File Structure
Copy code
testrun-ai/
├── recorder/
│   └── recorder.py
├── generator/
│   ├── generate.py
│   └── templates/
├── runner/
│   └── run_tests.py
├── visual/
│   └── visual_diff.py
├── web_demo/
│   └── streamlit_app.py
├── recordings/
├── artifacts/
└── trd.md
16. Success Criteria
Judges clearly understand the problem and solution

Demo runs smoothly in under 4 minutes

Automation value is obvious

Product feels realistic and scalable

17. One-Line Summary
TestRun AI converts manual mobile testing into automated DroidRun regression tests in minutes.