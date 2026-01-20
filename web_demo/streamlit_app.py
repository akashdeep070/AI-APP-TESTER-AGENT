#!/usr/bin/env python3
"""
TestRun AI - QA Prompt Testing Demo
Streamlit interface for AI-powered mobile app testing.

Usage:
    streamlit run web_demo/streamlit_app.py
"""

import streamlit as st
import json
import os
import sys
import subprocess
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env at startup
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Verify API key is loaded
if not os.getenv("GROQ_API_KEY"):
    print("[WARNING] GROQ_API_KEY not found in environment")

# Page config
st.set_page_config(
    page_title="TestRun AI - QA Prompt Testing",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #00cc66;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .main-header {
        text-align: center;
        padding: 1rem 0 2rem 0;
    }
    .big-button {
        font-size: 1.2rem;
        padding: 1rem 2rem;
    }
</style>
""", unsafe_allow_html=True)


def check_device_connected(device_id: str = "emulator-5554") -> bool:
    """Check if device is connected via ADB."""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return device_id in result.stdout
    except:
        return False


def get_ui_state(device_id: str = "emulator-5554") -> List[Dict]:
    """Get current UI state from device."""
    try:
        result = subprocess.run(
            [sys.executable, "recorder/recorder.py", "state", "--device", device_id],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except:
        return ""


def main():
    """Main Streamlit app - QA Prompt Testing focused."""
    
    # Header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🧪 TestRun AI")
    st.markdown("**AI-Powered Mobile App Testing with Natural Language Prompts**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        device_id = st.text_input(
            "Device ID",
            value="emulator-5554",
            help="ADB device identifier"
        )
        
        st.markdown("---")
        
        # Device Status
        st.subheader("📱 Device Status")
        
        if check_device_connected(device_id):
            st.success("✅ Device connected")
        else:
            st.error("❌ No device connected")
            st.code(f"adb devices", language="bash")
        
        # DroidRun Status
        try:
            from droidrun import AdbTools
            st.success("✅ DroidRun ready")
        except ImportError:
            st.warning("⚠️ DroidRun not installed")
        
        # Groq API Status
        try:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / ".env")
        except:
            pass
        
        if os.environ.get("GROQ_API_KEY"):
            st.success("✅ Groq API configured")
        else:
            st.error("❌ GROQ_API_KEY missing")
        
        st.markdown("---")
        st.markdown("**Model:** `meta-llama/llama-4-maverick-17b-128e-instruct`")
        
        # Show current UI state
        with st.expander("📋 Current UI State"):
            if st.button("Refresh UI State"):
                output = get_ui_state(device_id)
                st.code(output, language="text")
    
    # Main Content - Two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📱 Upload & Configure")
        
        # APK Upload
        uploaded_apk = st.file_uploader(
            "Upload Android APK",
            type=["apk"],
            help="Upload the APK file you want to test"
        )
        
        if uploaded_apk:
            st.success(f"✅ **{uploaded_apk.name}** ({uploaded_apk.size / 1024 / 1024:.2f} MB)")
        
        st.markdown("---")
        
        # QA Prompt
        st.subheader("💬 Test Prompt")
        
        qa_prompt = st.text_area(
            "Describe what to test",
            value="Open the app and test the main functionality",
            height=120,
            help="Use natural language to describe the test you want to run"
        )
        
        # Example prompts
        st.markdown("**Quick prompts:**")
        prompt_col1, prompt_col2 = st.columns(2)
        
        with prompt_col1:
            if st.button("🔐 Test Login", use_container_width=True):
                st.session_state["qa_prompt"] = "Test login with email test@example.com and password demo123"
                st.rerun()
            if st.button("⚙️ Toggle Dark Mode", use_container_width=True):
                st.session_state["qa_prompt"] = "Open settings and toggle dark mode on"
                st.rerun()
        
        with prompt_col2:
            if st.button("📷 Open Camera", use_container_width=True):
                st.session_state["qa_prompt"] = "Open camera app and take a photo"
                st.rerun()
            if st.button("🔍 Search Test", use_container_width=True):
                st.session_state["qa_prompt"] = "Open search and search for 'test query'"
                st.rerun()
        
        # Update prompt from session state
        if "qa_prompt" in st.session_state:
            qa_prompt = st.session_state["qa_prompt"]
        
        st.markdown("---")
        
        # Run button
        run_disabled = not qa_prompt.strip()
        
        if st.button("🚀 Run QA Analysis", type="primary", use_container_width=True, disabled=run_disabled):
            # Save APK if uploaded
            apk_path = None
            if uploaded_apk:
                with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tmp:
                    tmp.write(uploaded_apk.getvalue())
                    apk_path = tmp.name
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            logs = []
            
            def update_log(msg):
                logs.append(f"• {msg}")
                log_area.code("\n".join(logs[-8:]), language="text")
            
            try:
                from web_demo.qa_analysis import run_qa_analysis
                
                status_text.text("Starting QA analysis...")
                progress_bar.progress(10)
                
                # If no APK, still run on current app
                if apk_path is None:
                    apk_path = ""  # Will skip install step
                
                update_log("Initializing analysis...")
                progress_bar.progress(30)
                
                # Run analysis (async function)
                import asyncio
                result = asyncio.run(run_qa_analysis(
                    apk_path=apk_path if apk_path else "/dev/null",
                    qa_prompt=qa_prompt,
                    device_id=device_id,
                    progress_callback=update_log
                ))
                
                progress_bar.progress(100)
                status_text.text("Complete!")
                
                # Store result
                st.session_state["qa_result"] = asdict(result)
                
            except Exception as e:
                st.error(f"Analysis failed: {e}")
            finally:
                # Cleanup
                if apk_path and apk_path != "" and os.path.exists(apk_path):
                    try:
                        os.unlink(apk_path)
                    except:
                        pass
            
            st.rerun()
    
    with col2:
        st.subheader("📊 Analysis Results")
        
        if "qa_result" in st.session_state:
            result = st.session_state["qa_result"]
            
            # Status banner
            if result["status"] == "PASS":
                st.success("## ✅ PASS")
                st.balloons()
            elif result["status"] == "FAIL":
                st.error("## ❌ FAIL")
            else:
                st.warning(f"## ⚠️ {result['status']}")
                if result.get("error_message"):
                    st.error(result["error_message"])
            
            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Steps", result["steps_total"])
            with m2:
                st.metric("Passed", result["steps_passed"])
            with m3:
                st.metric("Failed", result["steps_failed"])
            with m4:
                st.metric("Time", f"{result['execution_time']:.1f}s")
            
            st.markdown("---")
            
            # Test details
            st.markdown(f"**App:** `{result['app_package']}`")
            st.markdown(f"**Prompt:** _{result['prompt']}_")
            
            # Steps breakdown
            if result.get("steps"):
                st.markdown("### 🔍 Test Steps")
                for i, step in enumerate(result["steps"]):
                    action = step.get("action", "unknown")
                    target = step.get("target", "")
                    st.markdown(f"**{i+1}.** `{action}` → {target}")
            
            # Screenshots
            screenshots = result.get("screenshots", [])
            if screenshots:
                st.markdown("### 📷 Screenshots")
                cols = st.columns(min(len(screenshots), 3))
                for i, path in enumerate(screenshots[:6]):
                    if Path(path).exists():
                        with cols[i % 3]:
                            st.image(path, caption=f"Step {i+1}", use_container_width=True)
            
            # Clear button
            if st.button("🗑️ Clear Results", use_container_width=True):
                del st.session_state["qa_result"]
                st.rerun()
        
        else:
            # Empty state
            st.info("Enter a test prompt and click **Run QA Analysis** to see results.")
            
            st.markdown("### How it works")
            st.markdown("""
            1. **Upload APK** _(optional)_ - Upload your Android app
            2. **Write prompt** - Describe what to test in plain English
            3. **Run analysis** - AI interprets and executes the test
            4. **View results** - See pass/fail, steps, and screenshots
            """)
            
            st.markdown("### Example prompts")
            st.code("""
• "Test login with email user@test.com and password secret123"
• "Open settings, find dark mode toggle, and enable it"
• "Navigate to profile screen and update the username"
• "Open camera and take a photo"
• "Search for 'shoes' and add first result to cart"
            """, language="text")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**TestRun AI** | Powered by DroidRun + Groq | "
        "Model: `meta-llama/llama-4-maverick-17b-128e-instruct` | "
        "Built for Hackathon 🚀"
    )


if __name__ == "__main__":
    main()
