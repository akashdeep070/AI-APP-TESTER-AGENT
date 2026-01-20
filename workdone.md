# TestRun AI - Work Done Summary

## Project Overview
**TestRun AI** is a DroidRun-powered automated mobile testing pipeline that converts manual app testing into automated, repeatable test suites.

**Tech Stack:**
- Python 3.11
- DroidRun (Android automation via ADB)
- Groq API with `moonshotai/kimi-k2-instruct` LLM
- Streamlit (web demo UI)
- Jinja2 (template engine)
- scikit-image (visual regression)

---

## Completed Implementation

### 1. Project Structure
```
QA_AI_Tester/
├── recorder/
│   └── recorder.py          # DroidRun-based UI event recorder
├── generator/
│   ├── generate.py          # LLM-enhanced test script generator
│   └── templates/
│       └── droidrun_template.py.j2
├── runner/
│   └── run_tests.py         # Test executor with pass/fail reporting
├── visual/
│   └── visual_diff.py       # SSIM-based visual regression detection
├── web_demo/
│   └── streamlit_app.py     # 4-tab web UI (Record, Generate, Run, Results)
├── recordings/              # JSON recordings
├── artifacts/               # Generated test scripts
├── .env                     # API keys (GROQ_API_KEY)
├── requirements.txt
├── TRD.md                   # Technical Requirements Document
└── demo_app_spec.md         # Demo Android app specification
```

---

### 2. Recorder Module (`recorder/recorder.py`)

**Features:**
- Integrates with DroidRun `AdbTools` for real device interaction
- Async API using `asyncio`
- Captures UI state via `get_state()` (returns element index, resourceId, className, bounds)
- Records tap, input, swipe, screenshot actions
- Interactive recording mode with CLI commands
- Fallback to ADB subprocess when DroidRun unavailable

**Key Code:**
```python
from droidrun import AdbTools
tools = AdbTools(serial="emulator-5554")
state = await tools.get_state()  # Returns tuple: (description, screenshot, elements_list, metadata)
await tools.tap_by_index(5)
await tools.input_text(3, "test@example.com")
```

**Recording JSON Schema:**
```json
{
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
    }
  ]
}
```

---

### 3. Generator Module (`generator/generate.py`)

**Features:**
- Converts recording JSON → executable DroidRun Python script
- Uses Jinja2 template (`droidrun_template.py.j2`)
- **Groq LLM Integration** with `moonshotai/kimi-k2-instruct`:
  - `enhance_recording_with_llm()` - Adds descriptions, assertions, wait conditions
  - `generate_test_description_with_llm()` - Creates markdown test documentation
  - `generate_test_assertions_with_llm()` - Generates Python assertions

**LLM API Usage:**
```python
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # Loads GROQ_API_KEY from .env

client = Groq(api_key=os.environ["GROQ_API_KEY"])
response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct",
    messages=[
        {"role": "system", "content": "You are a mobile test automation expert."},
        {"role": "user", "content": "<prompt with recording data>"}
    ],
    temperature=0.3,
    max_tokens=2000
)
```

**CLI Usage:**
```bash
# Without LLM (template-only)
python generator/generate.py -i recordings/demo1.json -o artifacts/demo1_test.py

# With LLM enhancement
python generator/generate.py -i recordings/demo1.json --use-llm --description
```

---

### 4. Runner Module (`runner/run_tests.py`)

**Features:**
- Executes generated Python test scripts via subprocess
- Captures stdout/stderr
- Reports PASS/FAIL based on exit code
- Saves results to JSON

**Usage:**
```bash
python runner/run_tests.py --script artifacts/demo1_test.py
python runner/run_tests.py --all  # Run all tests in artifacts/
```

---

### 5. Visual Diff Module (`visual/visual_diff.py`)

**Features:**
- SSIM (Structural Similarity Index) comparison using scikit-image
- Generates diff images with highlighted changes
- Batch directory comparison
- Configurable threshold (default 0.95)

**Usage:**
```bash
python visual/visual_diff.py --baseline base.png --current curr.png --output diff.png
```

---

### 6. Streamlit Web Demo (`web_demo/streamlit_app.py`)

**4 Tabs:**
1. **📹 Record** - Create demo recordings, capture screenshots, view UI state
2. **⚡ Generate** - Select recording, preview JSON, generate test script with code preview
3. **▶️ Run** - Execute tests, view output logs
4. **📊 Results** - Screenshots gallery, visual diff comparison

**Launch:**
```bash
streamlit run web_demo/streamlit_app.py
```

---

### 7. Environment Setup

**Dependencies (`requirements.txt`):**
```
jinja2>=3.1.0
streamlit>=1.30.0
pillow>=10.0.0
scikit-image>=0.22.0
numpy>=1.24.0
droidrun>=0.4.0
groq>=0.4.0
python-dotenv
```

**API Keys (`.env`):**
```
GROQ_API_KEY=gsk_your_key_here
```

**DroidRun Setup:**
```bash
pip install 'droidrun[google]'
droidrun setup  # Installs portal APK on emulator
```

---

## Verified Test Results

```
✅ Emulator: emulator-5554 connected
✅ DroidRun Portal: v0.5.3 installed
✅ UI State Detection: 19 elements found
✅ LLM Model: moonshotai/kimi-k2-instruct working
✅ Test Execution: 5/5 steps passed (4.5s)
```

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `recorder/recorder.py` | DroidRun UI recorder with async API |
| `generator/generate.py` | LLM-enhanced test script generator |
| `generator/templates/droidrun_template.py.j2` | Jinja2 template for test scripts |
| `runner/run_tests.py` | Test executor with result reporting |
| `visual/visual_diff.py` | SSIM-based visual regression |
| `web_demo/streamlit_app.py` | 4-tab Streamlit web interface |
| `.env` | Groq API key storage |
| `TRD.md` | Technical Requirements Document |
| `demo_app_spec.md` | Demo Android app element IDs |

---

## How to Run Full Demo

```bash
cd /Users/akashdeep/QA_AI_Tester
source venv/bin/activate

# 1. Start emulator (if not running)
emulator -avd flutter_emulator &

# 2. Setup DroidRun
droidrun setup

# 3. Create demo recording
python recorder/recorder.py demo

# 4. Generate test with LLM
export GROQ_API_KEY="your-key"
python generator/generate.py -i recordings/demo1.json --use-llm --description

# 5. Run test
python runner/run_tests.py -s artifacts/demo1_test.py

# 6. Launch Streamlit UI
streamlit run web_demo/streamlit_app.py
```

---

## Next Steps (Optional)

- [ ] Add real Android demo app matching `demo_app_spec.md`
- [ ] Implement coordinate-based tap actions
- [ ] Add visual regression to test runner
- [ ] Support more action types (swipe, long press)
- [ ] Add assertion validation in generated scripts
