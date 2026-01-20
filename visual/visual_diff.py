#!/usr/bin/env python3
"""
TestRun AI - Visual Diff Module
Compares baseline vs current screenshots for regression detection using SSIM.

Usage:
    python visual/visual_diff.py --help
    python visual/visual_diff.py --baseline baseline.png --current current.png
    python visual/visual_diff.py --baseline baseline.png --current current.png --output diff.png

Requirements:
    pip install pillow scikit-image numpy
"""

import argparse
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import numpy as np
from PIL import Image, ImageDraw, ImageChops

# Try to import scikit-image for SSIM
try:
    from skimage.metrics import structural_similarity as ssim
    from skimage import img_as_float
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False
    print("[Visual] WARNING: scikit-image not installed, using basic comparison")
    print("[Visual] Install with: pip install scikit-image")


# Default threshold for regression detection
DEFAULT_THRESHOLD = 0.95


def load_image(path: str) -> Optional[np.ndarray]:
    """
    Load an image as numpy array.
    
    Args:
        path: Path to image file
        
    Returns:
        Image as numpy array (RGB), or None if failed
    """
    try:
        img = Image.open(path).convert("RGB")
        return np.array(img)
    except Exception as e:
        print(f"[Visual] ERROR loading image {path}: {e}")
        return None


def resize_to_match(img1: np.ndarray, img2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resize images to match dimensions (use smaller size).
    """
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    
    if h1 != h2 or w1 != w2:
        # Use minimum dimensions
        min_h = min(h1, h2)
        min_w = min(w1, w2)
        
        pil1 = Image.fromarray(img1).resize((min_w, min_h), Image.Resampling.LANCZOS)
        pil2 = Image.fromarray(img2).resize((min_w, min_h), Image.Resampling.LANCZOS)
        
        return np.array(pil1), np.array(pil2)
    
    return img1, img2


def compute_ssim(
    baseline: np.ndarray,
    current: np.ndarray
) -> Tuple[float, Optional[np.ndarray]]:
    """
    Compute Structural Similarity Index (SSIM) between two images.
    
    Args:
        baseline: Baseline image array
        current: Current image array
        
    Returns:
        Tuple of (ssim_score, diff_map)
        ssim_score: 0.0 to 1.0, higher = more similar
        diff_map: Difference map highlighting changes (optional)
    """
    if not SKIMAGE_AVAILABLE:
        # Fallback to basic comparison
        return compute_basic_similarity(baseline, current)
    
    # Ensure same size
    baseline, current = resize_to_match(baseline, current)
    
    # Convert to grayscale for SSIM
    baseline_gray = np.mean(baseline, axis=2)
    current_gray = np.mean(current, axis=2)
    
    # Compute SSIM with full output
    try:
        score, diff_map = ssim(
            baseline_gray,
            current_gray,
            full=True,
            data_range=255
        )
        
        # Normalize diff_map to 0-255 range
        diff_map = ((1 - diff_map) * 255).astype(np.uint8)
        
        return float(score), diff_map
        
    except Exception as e:
        print(f"[Visual] SSIM error: {e}")
        return compute_basic_similarity(baseline, current)


def compute_basic_similarity(
    baseline: np.ndarray,
    current: np.ndarray
) -> Tuple[float, Optional[np.ndarray]]:
    """
    Fallback: Basic pixel-wise similarity comparison.
    """
    baseline, current = resize_to_match(baseline, current)
    
    # Compute absolute difference
    diff = np.abs(baseline.astype(float) - current.astype(float))
    
    # Mean absolute error normalized to 0-1
    mae = np.mean(diff) / 255.0
    
    # Convert MAE to similarity score (0-1, higher = more similar)
    similarity = 1.0 - mae
    
    # Create diff map (grayscale)
    diff_gray = np.mean(diff, axis=2).astype(np.uint8)
    
    return similarity, diff_gray


def generate_diff_image(
    baseline: np.ndarray,
    current: np.ndarray,
    diff_map: np.ndarray,
    output_path: str,
    highlight_color: Tuple[int, int, int] = (255, 0, 0)
) -> str:
    """
    Generate a visual diff image highlighting changes.
    
    Args:
        baseline: Baseline image
        current: Current image  
        diff_map: Difference map (grayscale)
        output_path: Path to save diff image
        highlight_color: RGB color for highlighting differences
        
    Returns:
        Path to saved diff image
    """
    # Ensure same size
    baseline, current = resize_to_match(baseline, current)
    
    # Create side-by-side comparison
    h, w = baseline.shape[:2]
    
    # Create output image: [baseline | diff | current]
    output = np.zeros((h, w * 3, 3), dtype=np.uint8)
    output[:, :w] = baseline
    output[:, w*2:] = current
    
    # Create diff overlay in middle
    # Start with current image
    diff_overlay = current.copy()
    
    # Threshold diff_map to find significant changes
    threshold = 30  # Pixels with diff > threshold are highlighted
    mask = diff_map > threshold
    
    # Apply highlight color to changed regions
    for c in range(3):
        diff_overlay[:, :, c] = np.where(
            mask,
            highlight_color[c],
            current[:, :, c] * 0.7  # Dim unchanged regions
        )
    
    output[:, w:w*2] = diff_overlay
    
    # Add labels
    pil_output = Image.fromarray(output)
    draw = ImageDraw.Draw(pil_output)
    
    # Simple labels (no custom font needed)
    try:
        draw.text((10, 10), "BASELINE", fill=(255, 255, 255))
        draw.text((w + 10, 10), "DIFF", fill=(255, 255, 0))
        draw.text((w * 2 + 10, 10), "CURRENT", fill=(255, 255, 255))
    except Exception:
        pass  # Skip labels if drawing fails
    
    # Save
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    pil_output.save(output_path)
    
    print(f"[Visual] Diff image saved: {output_path}")
    return output_path


def compare_screenshots(
    baseline_path: str,
    current_path: str,
    threshold: float = DEFAULT_THRESHOLD,
    output_diff: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare two screenshots and detect visual regressions.
    
    Args:
        baseline_path: Path to baseline screenshot
        current_path: Path to current screenshot
        threshold: SSIM threshold (0-1), below = regression
        output_diff: Optional path to save diff image
        
    Returns:
        Dict with comparison results:
        {
            "match": bool,           # True if score >= threshold
            "score": float,          # SSIM score (0-1)
            "threshold": float,      # Used threshold
            "regression": bool,      # True if score < threshold
            "diff_image": str|None,  # Path to diff image
            "baseline": str,
            "current": str
        }
    """
    print(f"[Visual] Comparing screenshots...")
    print(f"[Visual]   Baseline: {baseline_path}")
    print(f"[Visual]   Current:  {current_path}")
    
    # Validate paths
    if not os.path.exists(baseline_path):
        return {
            "match": False,
            "score": 0.0,
            "threshold": threshold,
            "regression": True,
            "error": f"Baseline not found: {baseline_path}",
            "baseline": baseline_path,
            "current": current_path
        }
    
    if not os.path.exists(current_path):
        return {
            "match": False,
            "score": 0.0,
            "threshold": threshold,
            "regression": True,
            "error": f"Current not found: {current_path}",
            "baseline": baseline_path,
            "current": current_path
        }
    
    # Load images
    baseline = load_image(baseline_path)
    current = load_image(current_path)
    
    if baseline is None or current is None:
        return {
            "match": False,
            "score": 0.0,
            "threshold": threshold,
            "regression": True,
            "error": "Failed to load images",
            "baseline": baseline_path,
            "current": current_path
        }
    
    # Compute similarity
    score, diff_map = compute_ssim(baseline, current)
    
    # Determine if regression
    match = score >= threshold
    regression = not match
    
    print(f"[Visual] SSIM Score: {score:.4f}")
    print(f"[Visual] Threshold:  {threshold}")
    print(f"[Visual] Result:     {'✓ MATCH' if match else '✗ REGRESSION'}")
    
    result = {
        "match": match,
        "score": round(score, 4),
        "threshold": threshold,
        "regression": regression,
        "baseline": baseline_path,
        "current": current_path,
        "diff_image": None
    }
    
    # Generate diff image if requested or if regression detected
    if output_diff or regression:
        if output_diff is None:
            # Auto-generate diff path
            output_diff = current_path.replace(".png", "_diff.png")
        
        if diff_map is not None:
            generate_diff_image(baseline, current, diff_map, output_diff)
            result["diff_image"] = output_diff
    
    return result


def compare_directories(
    baseline_dir: str,
    current_dir: str,
    threshold: float = DEFAULT_THRESHOLD,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare all screenshots in two directories.
    
    Args:
        baseline_dir: Directory with baseline screenshots
        current_dir: Directory with current screenshots
        threshold: SSIM threshold
        output_dir: Optional directory for diff images
        
    Returns:
        Summary of all comparisons
    """
    print(f"[Visual] Comparing directories...")
    print(f"[Visual]   Baseline: {baseline_dir}")
    print(f"[Visual]   Current:  {current_dir}")
    
    baseline_path = Path(baseline_dir)
    current_path = Path(current_dir)
    
    if not baseline_path.exists():
        return {"error": f"Baseline directory not found: {baseline_dir}"}
    
    if not current_path.exists():
        return {"error": f"Current directory not found: {current_dir}"}
    
    # Find matching files
    baseline_files = {f.name: f for f in baseline_path.glob("*.png")}
    current_files = {f.name: f for f in current_path.glob("*.png")}
    
    results = {
        "total": 0,
        "matches": 0,
        "regressions": 0,
        "missing_baseline": 0,
        "missing_current": 0,
        "details": []
    }
    
    # Compare matching files
    all_files = set(baseline_files.keys()) | set(current_files.keys())
    
    for filename in sorted(all_files):
        results["total"] += 1
        
        if filename not in baseline_files:
            results["missing_baseline"] += 1
            results["details"].append({
                "file": filename,
                "status": "missing_baseline"
            })
            continue
        
        if filename not in current_files:
            results["missing_current"] += 1
            results["details"].append({
                "file": filename,
                "status": "missing_current"
            })
            continue
        
        # Compare
        output_diff = None
        if output_dir:
            output_diff = str(Path(output_dir) / filename.replace(".png", "_diff.png"))
        
        comparison = compare_screenshots(
            str(baseline_files[filename]),
            str(current_files[filename]),
            threshold,
            output_diff
        )
        
        if comparison.get("match"):
            results["matches"] += 1
        else:
            results["regressions"] += 1
        
        results["details"].append({
            "file": filename,
            "status": "match" if comparison.get("match") else "regression",
            "score": comparison.get("score"),
            "diff_image": comparison.get("diff_image")
        })
    
    print(f"\n[Visual] Summary:")
    print(f"[Visual]   Total: {results['total']}")
    print(f"[Visual]   Matches: {results['matches']}")
    print(f"[Visual]   Regressions: {results['regressions']}")
    
    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestRun AI Visual Diff - Detect visual regressions using SSIM"
    )
    
    parser.add_argument("--baseline", "-b", help="Baseline screenshot path")
    parser.add_argument("--current", "-c", help="Current screenshot path")
    parser.add_argument("--output", "-o", help="Output diff image path")
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"SSIM threshold (0-1, default: {DEFAULT_THRESHOLD})"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Compare directories instead of single files"
    )
    parser.add_argument("--baseline-dir", help="Baseline directory for batch")
    parser.add_argument("--current-dir", help="Current directory for batch")
    parser.add_argument("--output-dir", help="Output directory for batch diffs")
    
    args = parser.parse_args()
    
    if args.baseline and args.current:
        # Single file comparison
        result = compare_screenshots(
            args.baseline,
            args.current,
            args.threshold,
            args.output
        )
        
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")
            exit(1)
        
        if result.get("match"):
            print(f"\n✅ Images match (score: {result['score']:.4f})")
            exit(0)
        else:
            print(f"\n⚠️  Visual regression detected (score: {result['score']:.4f})")
            if result.get("diff_image"):
                print(f"   Diff image: {result['diff_image']}")
            exit(1)
            
    elif args.batch and args.baseline_dir and args.current_dir:
        # Directory comparison
        results = compare_directories(
            args.baseline_dir,
            args.current_dir,
            args.threshold,
            args.output_dir
        )
        
        if results.get("error"):
            print(f"\n❌ Error: {results['error']}")
            exit(1)
        
        if results["regressions"] > 0:
            print(f"\n⚠️  {results['regressions']} visual regression(s) detected!")
            exit(1)
        else:
            print(f"\n✅ All {results['matches']} screenshots match")
            exit(0)
            
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python visual/visual_diff.py --baseline base.png --current curr.png")
        print("  python visual/visual_diff.py --baseline base.png --current curr.png --output diff.png")
        print("  python visual/visual_diff.py --batch --baseline-dir baseline/ --current-dir current/")


if __name__ == "__main__":
    main()
