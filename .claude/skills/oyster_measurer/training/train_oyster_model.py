"""
train_oyster_model.py — YOLOv8 training pipeline for Pacific oyster detection
Pacific Oyster Lab — any aquaculture site

Usage:
  python3 train_oyster_model.py [--images 1-15] [--resume path/to/model.pt]

Steps performed:
  1. Read blue-painted mask images → extract oyster polygons per image
  2. Write YOLO-format label files (class 0 = oyster)
  3. Copy raw images into dataset folder
  4. Train YOLOv8n-seg from pretrained base (or resume from existing model)
  5. Save best.pt to --out_model path

Inputs:
  Raw images:    <raw_dir>/{n}_raw.jpeg
  Masked images: <mask_dir>/{n}_masked.png
    - Blue regions (HSV H:100-130) = oyster outlines
    - Red box (HSV H:0-8 or 168-180) = caliper/ruler location (used elsewhere)

Output:
  <out_model>          Best trained model weights (.pt)
  <dataset_dir>/       YOLO dataset used for training
  <runs_dir>/          Training logs, metrics, plots
"""

import argparse, re, shutil, cv2, numpy as np
from pathlib import Path
from ultralytics import YOLO

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_RAW_DIR     = Path.home() / "Desktop/oyster_pictures/Raw_jepg"
DEFAULT_MASK_DIR    = Path.home() / "Desktop/oyster_pictures/Masked_png"
DEFAULT_DATASET_DIR = Path.home() / "Desktop/oyster_yolo_dataset"
DEFAULT_RUNS_DIR    = Path.home() / "Desktop/oyster_yolo_runs"
DEFAULT_OUT_MODEL   = Path.home() / "Desktop/oyster_model.pt"
BASE_MODEL          = "yolov8n-seg.pt"   # pretrained base; overridden by --resume

BLUE_LOWER = np.array([100, 70,  50])
BLUE_UPPER = np.array([130, 255, 255])

# ── Step 1 & 2: Convert blue masks → YOLO polygon labels ─────────────────────
def convert_masks_to_yolo(image_ids, raw_dir, mask_dir, dataset_dir):
    (dataset_dir / "images/train").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "labels/train").mkdir(parents=True, exist_ok=True)

    converted = 0
    total_polygons = 0

    for n in image_ids:
        raw_path  = next(raw_dir.glob(f"{n}_raw.*"),    None)
        mask_path = next(mask_dir.glob(f"{n}_masked.*"), None)
        if not raw_path or not mask_path:
            print(f"  [{n}] missing raw or mask — skipped"); continue

        raw_img  = cv2.imread(str(raw_path))
        mask_img = cv2.imread(str(mask_path))
        H, W = raw_img.shape[:2]

        hsv     = cv2.cvtColor(mask_img, cv2.COLOR_BGR2HSV)
        blue    = cv2.inRange(hsv, BLUE_LOWER, BLUE_UPPER)
        kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(blue, cv2.MORPH_OPEN, kernel, iterations=1)

        cnts, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        lines = []
        for c in cnts:
            if cv2.contourArea(c) < 500: continue
            eps  = 0.005 * cv2.arcLength(c, True)
            poly = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
            if len(poly) < 3: continue
            coords = []
            for x, y in poly:
                coords.extend([round(x / W, 6), round(y / H, 6)])
            lines.append("0 " + " ".join(map(str, coords)))

        if not lines:
            print(f"  [{n}] no blue polygons found — skipped"); continue

        suffix = raw_path.suffix
        shutil.copy2(raw_path, dataset_dir / f"images/train/{n}{suffix}")
        (dataset_dir / f"labels/train/{n}.txt").write_text("\n".join(lines))

        print(f"  [{n}] {len(lines):>4} oyster polygons")
        total_polygons += len(lines)
        converted += 1

    # Write dataset.yaml
    yaml_path = dataset_dir / "dataset.yaml"
    yaml_path.write_text(
        f"path: {dataset_dir}\n"
        f"train: images/train\n"
        f"val:   images/train\n\n"
        f"nc: 1\n"
        f"names:\n  0: oyster\n"
    )
    print(f"\n  Converted {converted} images, {total_polygons} total polygons")
    print(f"  Dataset → {dataset_dir}")
    return yaml_path

# ── Step 3: Train YOLOv8 ──────────────────────────────────────────────────────
def train(yaml_path, base_model, runs_dir, run_name, epochs=100):
    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"\n  Training on device: {device}")
    print(f"  Base model:  {base_model}")
    print(f"  Run name:    {run_name}")
    print(f"  Epochs:      {epochs}")

    model   = YOLO(str(base_model))
    results = model.train(
        data      = str(yaml_path),
        epochs    = epochs,
        imgsz     = 1024,
        batch     = 4,
        device    = device,
        project   = str(runs_dir),
        name      = run_name,
        patience  = 20,
        augment   = True,
        degrees   = 15,
        flipud    = 0.5,
        fliplr    = 0.5,
        mosaic    = 0.5,
        verbose   = False,
    )
    best = Path(results.save_dir) / "weights/best.pt"
    print(f"\n  Best model → {best}")
    return best

# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_range(s):
    """Parse '1-15' or '1,2,3' into a sorted list of ints."""
    ids = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            ids.extend(range(int(a), int(b) + 1))
        else:
            ids.append(int(part))
    return sorted(set(ids))

def main():
    p = argparse.ArgumentParser(description="Train YOLOv8 oyster detector")
    p.add_argument("--images",    default="1-20",
                   help="Image range to train on, e.g. '1-15' or '1-20'")
    p.add_argument("--resume",    default=None,
                   help="Path to existing .pt to continue training from")
    p.add_argument("--epochs",    type=int, default=100)
    p.add_argument("--raw_dir",   default=str(DEFAULT_RAW_DIR))
    p.add_argument("--mask_dir",  default=str(DEFAULT_MASK_DIR))
    p.add_argument("--dataset_dir", default=str(DEFAULT_DATASET_DIR))
    p.add_argument("--runs_dir",  default=str(DEFAULT_RUNS_DIR))
    p.add_argument("--out_model", default=str(DEFAULT_OUT_MODEL))
    p.add_argument("--run_name",  default=None,
                   help="Name for this training run (default: oyster_v<n>)")
    args = p.parse_args()

    image_ids   = parse_range(args.images)
    raw_dir     = Path(args.raw_dir)
    mask_dir    = Path(args.mask_dir)
    dataset_dir = Path(args.dataset_dir)
    runs_dir    = Path(args.runs_dir)
    out_model   = Path(args.out_model)

    # Clear and rebuild dataset for this image set
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    dataset_dir.mkdir(parents=True)

    run_name = args.run_name or f"oyster_imgs{'_'.join(args.images.split(','))}"
    base     = Path(args.resume) if args.resume else BASE_MODEL

    print(f"\n{'='*60}")
    print(f"  Oyster-Measurer — YOLOv8 Training")
    print(f"  Images: {image_ids}")
    print(f"  Resume: {base}")
    print(f"{'='*60}\n")

    print("Step 1/2 — Converting masks to YOLO labels...")
    yaml_path = convert_masks_to_yolo(image_ids, raw_dir, mask_dir, dataset_dir)

    print("\nStep 2/2 — Training YOLOv8n-seg...")
    best_pt = train(yaml_path, base, runs_dir, run_name, epochs=args.epochs)

    shutil.copy2(best_pt, out_model)
    print(f"\n{'='*60}")
    print(f"  Training complete — model saved to {out_model}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
