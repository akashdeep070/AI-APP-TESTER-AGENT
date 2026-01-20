#!/usr/bin/env python3
"""
TestRun AI - Test Runner Module
Executes generated DroidRun scripts and reports PASS/FAIL status.

Usage:
    python runner/run_tests.py --help
    python runner/run_tests.py --script artifacts/demo1_test.py
    python runner/run_tests.py --script artifacts/demo1_test.py --capture-output
"""

import argparse
import subprocess
import sys
import time
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class TestResult:
    """Result of a test execution."""
    script: str
    status: str  # PASS, FAIL, ERROR
    duration_ms: int
    exit_code: int
    stdout: str
    stderr: str
    timestamp: int


def run_test(script_path: str, capture_output: bool = True, timeout: int = 120) -> TestResult:
    """
    Execute a generated test script and return the result.
    
    Args:
        script_path: Path to the Python test script
        capture_output: Whether to capture stdout/stderr
        timeout: Maximum execution time in seconds
        
    Returns:
        TestResult with execution details
    """
    print(f"[Runner] Executing: {script_path}")
    print("-" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT)
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Determine status based on exit code
        if result.returncode == 0:
            status = "PASS"
        else:
            status = "FAIL"
        
        test_result = TestResult(
            script=script_path,
            status=status,
            duration_ms=duration_ms,
            exit_code=result.returncode,
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else "",
            timestamp=int(time.time())
        )
        
        # Print output if captured
        if capture_output and result.stdout:
            print(result.stdout)
        if capture_output and result.stderr:
            print("[STDERR]", result.stderr, file=sys.stderr)
        
        return test_result
        
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"[Runner] ERROR: Test timed out after {timeout}s")
        
        return TestResult(
            script=script_path,
            status="ERROR",
            duration_ms=duration_ms,
            exit_code=-1,
            stdout="",
            stderr=f"Test timed out after {timeout} seconds",
            timestamp=int(time.time())
        )
        
    except FileNotFoundError:
        print(f"[Runner] ERROR: Script not found: {script_path}")
        
        return TestResult(
            script=script_path,
            status="ERROR",
            duration_ms=0,
            exit_code=-1,
            stdout="",
            stderr=f"Script not found: {script_path}",
            timestamp=int(time.time())
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"[Runner] ERROR: {e}")
        
        return TestResult(
            script=script_path,
            status="ERROR",
            duration_ms=duration_ms,
            exit_code=-1,
            stdout="",
            stderr=str(e),
            timestamp=int(time.time())
        )


def run_all_tests(test_dir: str = "artifacts", pattern: str = "*_test.py") -> Dict[str, Any]:
    """
    Run all test scripts matching the pattern in a directory.
    
    Args:
        test_dir: Directory containing test scripts
        pattern: Glob pattern for test files
        
    Returns:
        Summary of all test results
        
    TODO: Add parallel test execution
    TODO: Add retry logic for flaky tests
    """
    test_path = Path(test_dir)
    test_files = list(test_path.glob(pattern))
    
    print(f"[Runner] Found {len(test_files)} test(s) in {test_dir}")
    print("=" * 60)
    
    results = []
    passed = 0
    failed = 0
    errors = 0
    
    for test_file in test_files:
        result = run_test(str(test_file))
        results.append(asdict(result))
        
        if result.status == "PASS":
            passed += 1
        elif result.status == "FAIL":
            failed += 1
        else:
            errors += 1
        
        print("-" * 60)
    
    summary = {
        "total": len(test_files),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "results": results
    }
    
    print("=" * 60)
    print(f"[Runner] Summary: {passed} passed, {failed} failed, {errors} errors")
    print("=" * 60)
    
    return summary


def save_results(results: Dict[str, Any], output_path: str) -> str:
    """
    Save test results to a JSON file.
    
    Args:
        results: Test results dictionary
        output_path: Path to save JSON
        
    Returns:
        Path to saved file
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"[Runner] Results saved: {output_path}")
    return output_path


def print_result(result: TestResult):
    """Print a formatted test result."""
    status_icon = "✅" if result.status == "PASS" else "❌"
    print(f"\n{status_icon} {result.status}")
    print(f"   Script: {result.script}")
    print(f"   Duration: {result.duration_ms}ms")
    print(f"   Exit code: {result.exit_code}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestRun AI Runner - Execute test scripts and report results"
    )
    
    parser.add_argument(
        "--script", "-s",
        help="Path to a single test script to run"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all tests in artifacts directory"
    )
    parser.add_argument(
        "--dir", "-d",
        default="artifacts",
        help="Directory containing test scripts (default: artifacts)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to save results JSON"
    )
    parser.add_argument(
        "--capture-output",
        action="store_true",
        default=True,
        help="Capture stdout/stderr (default: true)"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=120,
        help="Test timeout in seconds (default: 120)"
    )
    
    args = parser.parse_args()
    
    if args.script:
        # Run single test
        result = run_test(args.script, args.capture_output, args.timeout)
        print_result(result)
        
        if args.output:
            save_results({"results": [asdict(result)]}, args.output)
        
        # Exit with appropriate code
        if result.status == "PASS":
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif args.all:
        # Run all tests
        results = run_all_tests(args.dir)
        
        if args.output:
            save_results(results, args.output)
        
        # Exit with failure if any test failed
        if results["failed"] > 0 or results["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python runner/run_tests.py --script artifacts/demo1_test.py")
        print("  python runner/run_tests.py --all")


if __name__ == "__main__":
    main()
