"""
train_caliper_model.py — YOLOv8 detection model for caliper/ruler localization

Reads the red bounding box drawn in each masked PNG, converts it to a YOLO
detection label, then fine-tunes YOLOv8n-det on all 50 images.

Usage:
  python3 train_caliper_model.py [--images 1-50] [--epochs 100]

Output:
  caliper_model.pt   Best trained weights (saved next to this script)
"""

import argparse, re, shutil, cv2, numpy as np, yaml
from pathlib import Path
from ultralytics import YOLO

RAW_DIR     = Path.home() / "Desktop/oyster_pictures/Raw_jepg"
MASK_DIR    = Path.home() / "Desktop/oyster_pictures/Masked_png"
DATASET_DIR = Path.home() / "Desktop/caliper_yolo_dataset"
RUNS_DIR    = Path.home() / "Desktop/caliper_yolo_runs"
OUT_MODEL   = Path(__file__).parent / "caliper_model.pt"
BASE_MODEL  = "yolov8n.pt"   # detection, not segmentation

RED_LOWER1 = np.array([0,   80,  80])
RED_UPPER1 = np.array([8,  255, 255])
RED_LOWER2 = np.array([168, 80,  80])
RED_UPPER2 = np.array([180,255, 255])


def extract_red_box(mask_img):
    """Return (x, y, w, h) of the largest red region, or None."""
    hsv = cv2.cvtColor(mask_img, cv2.COLOR_BGR2HSV)
    red = cv2.bitwise_or(cv2.inRange(hsv, RED_LOWER1, RED_UPPER1),
                         cv2.inRange(hsv, RED_LOWER2, RED_UPPER2))
    cnts, _ = cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c) > 500]
    if not boxes:
        return None
    return max(boxes, key=lambda b: b[2] * b[3])


def build_dataset(image_ids):
    img_dir = DATASET_DIR / "images/train"
    lbl_dir = DATASET_DIR / "labels/train"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for n in image_ids:
        raw_path  = next(RAW_DIR.glob(f"{n}_raw.*"),    None)
        mask_path = next(MASK_DIR.glob(f"{n}_masked.*"), None)
        if not raw_path or not mask_path:
            print(f"  [{n}] missing raw or mask — skipped"); continue

        raw_img  = cv2.imread(str(raw_path))
        mask_img = cv2.imread(str(mask_path))
        H, W = raw_img.shape[:2]

        box = extract_red_box(mask_img)
        if box is None:
            print(f"  [{n}] no red box found — skipped"); continue

        x, y, w, h = box
        # YOLO detection format: class cx cy w h (normalized, 0-1)
        cx = (x + w / 2) / W
        cy = (y + h / 2) / H
        nw = w / W
        nh = h / H

        shutil.copy(raw_path, img_dir / raw_path.name)
        lbl = lbl_dir / (raw_path.stem + ".txt")
        lbl.write_text(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")
        ok += 1
        print(f"  [{n}] box=({x},{y},{w},{h}) → {cx:.3f},{cy:.3f},{nw:.3f},{nh:.3f}")

    print(f"\nDataset: {ok}/{len(image_ids)} images with caliper labels")
    return ok


def write_yaml():
    cfg = {
        "path":  str(DATASET_DIR),
        "train": "images/train",
        "val":   "images/train",   # small dataset — validate on train set
        "nc":    1,
        "names": ["caliper"],
    }
    p = DATASET_DIR / "caliper.yaml"
    with open(p, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return p


def parse_ids(s):
    m = re.match(r"(\d+)-(\d+)$", s.strip())
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    return [int(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images",  default="1-50")
    ap.add_argument("--epochs",  type=int, default=100)
    ap.add_argument("--imgsz",   type=int, default=640)
    args = ap.parse_args()

    ids = parse_ids(args.images)
    print(f"Building caliper detection dataset for images {ids[0]}–{ids[-1]}…")

    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)
    n_ok = build_dataset(ids)
    if n_ok == 0:
        print("No labeled images — aborting."); return

    yaml_path = write_yaml()
    print(f"\nDataset YAML: {yaml_path}")
    print(f"Training YOLOv8n detector for {args.epochs} epochs…\n")

    model = YOLO(BASE_MODEL)
    results = model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=8,
        project=str(RUNS_DIR),
        name="caliper_det",
        exist_ok=True,
        device="mps",   # Apple Silicon; falls back to cpu automatically
    )

    best = Path(results.save_dir) / "weights/best.pt"
    if best.exists():
        shutil.copy(best, OUT_MODEL)
        print(f"\nSaved: {OUT_MODEL}")
    else:
        print("WARNING: best.pt not found — check training logs")


if __name__ == "__main__":
    main()
