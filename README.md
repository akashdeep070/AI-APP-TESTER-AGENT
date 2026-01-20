# 🧪 AI App Tester Agent

<div align="center">

![AI App Tester](https://img.shields.io/badge/AI-Powered-blueviolet?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Android-green?style=for-the-badge&logo=android)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**An agentic AI-powered QA testing framework that uses vision language models to autonomously test Android applications with natural language prompts.**

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [How It Works](#-how-it-works) • [API](#-api)

</div>

---

## 🎯 Overview

AI App Tester Agent revolutionizes mobile app testing by combining:

- **🤖 Agentic AI** - Autonomous decision-making that adapts to any UI state
- **👁️ Vision LLM** - Understands screenshots to identify UI elements intelligently  
- **💬 Natural Language** - Describe tests in plain English, no coding required
- **📱 Real Device Control** - Executes actions on actual Android devices/emulators

Unlike traditional test automation that requires brittle element selectors, this system **sees** the screen and **thinks** about what to do next—just like a human tester.

---

## ✨ Features

### 🔄 Agentic Iterative Testing
```
Traditional: Generate all steps → Execute blindly → Often fails
     
AI Agent:   Analyze screen → Decide next step → Execute → Repeat
```

The agent captures a screenshot after each action, analyzes the new state, and intelligently decides the next step until the test objective is complete.

### 👁️ Vision-Based Understanding
- Uses **Meta Llama 4 Maverick** model with vision capabilities
- Analyzes screenshots to identify buttons, text fields, and UI elements
- No need for element IDs or XPath selectors

### 💬 Natural Language Prompts
```
"Open the shopping app and add an item to the cart"
"Test login with username 'demo@test.com' and password 'secret123'"  
"Navigate to settings and enable dark mode"
```

### 📊 Comprehensive Results
- Step-by-step execution logs
- Screenshots at each step
- Pass/Fail status with detailed assertions
- Execution time metrics

---

## 🎬 Demo

<div align="center">

### Streamlit Dashboard
The intuitive web interface for running QA tests:

| Configuration | Test Execution | Results |
|:---:|:---:|:---:|
| Device connection | Real-time logs | Pass/Fail status |
| Model selection | Step progress | Screenshots |
| Prompt input | Action preview | Metrics |

</div>

---

## 🚀 Installation

### Prerequisites

- Python 3.9+
- Android SDK with ADB
- Android device/emulator connected
- Groq API key (for LLM access)

### Setup

```bash
# Clone the repository
git clone https://github.com/akashdeep070/AI-APP-TESTER-AGENT.git
cd AI-APP-TESTER-AGENT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Required: Groq API Key
GROQ_API_KEY=your_groq_api_key_here
```

---

## 📖 Usage

### Start the Web Interface

```bash
streamlit run web_demo/streamlit_app.py
```

Open `http://localhost:8501` in your browser.

### Using the Dashboard

1. **Connect Device** - Ensure your Android device/emulator is connected via ADB
2. **Enter Prompt** - Describe what you want to test in natural language
3. **Run Analysis** - Click the button and watch the AI work
4. **Review Results** - See step-by-step execution with screenshots

### Quick Prompts

| Prompt | What It Tests |
|--------|---------------|
| `Test login with email and password` | Authentication flow |
| `Open settings and toggle dark mode` | Settings navigation |
| `Search for 'shoes' and add to cart` | E-commerce flow |
| `Open camera and take a photo` | Camera functionality |

### Command Line

```bash
# Direct testing via CLI
python web_demo/qa_analysis.py /path/to/app.apk "Test the main functionality"
```

---

## 🧠 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI App Tester Agent                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Streamlit  │───▶│  QA Analysis │───▶│   DroidRun   │       │
│  │      UI      │    │    Engine    │    │   (ADB)      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                             │                    │               │
│                             ▼                    ▼               │
│                    ┌──────────────┐    ┌──────────────┐         │
│                    │  Vision LLM  │    │   Android    │         │
│                    │  (Groq API)  │    │    Device    │         │
│                    └──────────────┘    └──────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Agentic Loop

```python
while not test_complete:
    # 1. Capture current screen
    screenshot = capture_screenshot(device)
    
    # 2. Send to Vision LLM with context
    next_action = llm.analyze(
        screenshot=screenshot,
        objective=user_prompt,
        completed_steps=history
    )
    
    # 3. Execute action on device
    execute(next_action)  # tap, input, swipe, verify
    
    # 4. Check if test is complete
    if next_action == "DONE":
        test_complete = True
```

### Key Components

| Component | File | Description |
|-----------|------|-------------|
| **QA Engine** | `web_demo/qa_analysis.py` | Core agentic testing logic |
| **Web UI** | `web_demo/streamlit_app.py` | Streamlit dashboard |
| **Recorder** | `recorder/recorder.py` | UI state capture |
| **Generator** | `generator/generate.py` | Test generation templates |
| **Visual Diff** | `visual/visual_diff.py` | Screenshot comparison |

---

## 🔧 API

### `run_qa_analysis()`

Main entry point for running tests.

```python
from web_demo.qa_analysis import run_qa_analysis
import asyncio

result = asyncio.run(run_qa_analysis(
    apk_path="/path/to/app.apk",  # Optional
    qa_prompt="Open the app and test login",
    device_id="emulator-5554",
    progress_callback=lambda msg: print(msg)
))

print(f"Status: {result.status}")
print(f"Steps: {result.steps_passed}/{result.steps_total}")
```

### `QAResult` Object

```python
@dataclass
class QAResult:
    status: str           # PASS, FAIL, ERROR
    app_package: str      # Package name
    prompt: str           # Original prompt
    steps_total: int      # Total steps executed
    steps_passed: int     # Successful steps
    steps_failed: int     # Failed steps
    execution_time: float # Time in seconds
    steps: List[Dict]     # Detailed step info
    screenshots: List[str] # Screenshot paths
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.9+** | Core language |
| **Streamlit** | Web interface |
| **Groq API** | LLM inference |
| **Meta Llama 4 Maverick** | Vision-language model |
| **DroidRun** | Android automation |
| **ADB** | Device communication |

---

## 📁 Project Structure

```
AI-APP-TESTER-AGENT/
├── web_demo/
│   ├── qa_analysis.py      # Core QA engine
│   └── streamlit_app.py    # Web interface
├── generator/
│   ├── generate.py         # Test generation
│   └── templates/          # Jinja2 templates
├── recorder/
│   └── recorder.py         # UI state capture
├── runner/
│   └── run_tests.py        # Test execution
├── visual/
│   └── visual_diff.py      # Screenshot comparison
├── requirements.txt        # Dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Groq](https://groq.com/) for lightning-fast LLM inference
- [DroidRun](https://github.com/nicholasanastasi/droidrun) for Android automation
- [Streamlit](https://streamlit.io/) for the beautiful UI framework

---

<div align="center">

**Built with ❤️ for the future of QA automation**

[⬆ Back to Top](#-ai-app-tester-agent)

</div>
