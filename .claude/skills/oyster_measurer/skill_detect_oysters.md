# Skill: Oyster Detection

Finds individual oysters in a raw field photograph and returns a list of contours — one per oyster. Three methods are tried in priority order: **blue mask → trained YOLO model → adaptive threshold**.

---

## TRIGGER

Activate this sub-skill when:
- A raw oyster image (and optionally a blue-painted mask image) is available and oysters need to be located
- The user reports missed oysters, merged oysters, or too many false detections
- Switching between detection methods (e.g., user wants to force mask-based detection)

---

## WHAT THIS DOES IN THE CODE

Three functions in `measure_oysters.py`:
- `segment_from_blue_mask()` — blue mask path
- `segment_from_yolo()` — YOLO model path
- `segment_oysters()` — adaptive threshold fallback

The `run()` function selects which one to call:

```python
if mask_path is not None:
    contours, blue_binary = segment_from_blue_mask(img, mask_img)
elif yolo_model_available():
    contours = segment_from_yolo(img)
    if contours is None:                 # model present but unloadable
        contours = segment_oysters(img)
else:
    contours = segment_oysters(img)
```

Note `segment_from_yolo()` returns `None` when the model cannot be used at all, but an empty list
when the model ran and found nothing — only the former triggers the fallback.

---

## METHOD 1 — Blue-painted mask (most accurate; requires prep work)

**When to use:** the user has provided a masked PNG where each oyster is hand-painted solid blue, with a deliberate unpainted gap between every touching pair.

**How it works:**
1. Convert mask image to HSV; threshold to isolate blue pixels:
   - `BLUE_HSV_LOWER = [100, 70, 50]`
   - `BLUE_HSV_UPPER = [130, 255, 255]`
2. Remove tiny speckles with `MORPH_OPEN` (3×3 ellipse, 1 iteration) — **no MORPH_CLOSE**, which would bridge the intentional gaps between oysters
3. Find all connected blue blobs with `connectedComponents`
4. **Per-blob watershed** — each blob is processed independently:
   - Distance transform on the blob mask
   - Threshold at **40% of that blob's local maximum** (not a global threshold — this is critical so small oysters beside large ones still get their own watershed seed)
   - `sure_fg` = pixels well inside the blob; `sure_bg` = dilated blob (7×7 ellipse × 3 iterations)
   - Watershed splits touching sub-regions within the blob into individual oysters
5. Extract contours from each watershed label; filter by area

**Why per-blob?** A single global `dist.max()` threshold is dominated by the largest oyster in the image — all smaller neighbours fail to get a seed and merge into it. Per-blob ensures every painted region gets its own fair split.

**Blue mask painting guide:**
- Paint each oyster solid blue — fill the entire shell outline
- Leave a visible gap (even 1–2 px) between every touching pair; the algorithm relies on this gap
- Do not paint the caliper, ruler, or background blue
- Use the same image dimensions as the raw photo

---

## METHOD 2 — Trained YOLOv8n-seg model (no prep work needed)

**When to use:** no mask is available; this is the default for new photos from any site.

**Model file:** `.claude/skills/oyster_measurer/oyster_model.pt` (must be in the same folder as the script)

**How it works:**
1. Resize the raw image so the longest side = 1024 px (preserves aspect ratio)
2. Run `model.predict()` with:
   - `conf = 0.25` (minimum detection confidence)
   - `iou = 0.4` (non-maximum suppression overlap threshold)
   - `max_det = 500`
   - Device: Apple MPS if available, otherwise CPU
3. Scale the predicted mask polygons back to the original image size
4. Filter contours by area; sort in reading order

**Failure handling (no longer silent):**
- `ultralytics` not installed → prints install instruction, falls back to Method 3
- `oyster_model.pt` missing → prints file location, falls back to Method 3
- Model file corrupt / version mismatch → prints the actual exception, falls back to Method 3

**Training history:**
- v1 (images 1–15): mAP50 = 0.506
- v2 (images 1–20, continued from v1): mAP50 = 0.591
- v3 (images 1–50, continued from v2, 4031 oyster polygons, 52 epochs): mAP50 = 0.209 — current
  production model; `oyster_model.pt` is byte-identical to `oyster_model_v3.pt`

**Do not read that as v3 being worse.** Every one of those numbers was measured on the model's own
training images, not a held-out split, so they are not comparable: v3's lower figure most likely
reflects a harder and more varied 50-image set. Nothing in the repo establishes which checkpoint
actually generalizes better, and no model card exists. Establishing that is roadmap M3 — until then
do not tell the user one model beats another, and do not quote these as accuracy figures.

To retrain: `python3 train_oyster_model.py --images 1-50 --resume oyster_model.pt --epochs 150`

---

## METHOD 3 — Adaptive threshold fallback (weakest; no extra files needed)

**When to use:** automatically used when neither a mask nor the YOLO model is available.

**How it works:**
1. Convert to LAB colour space; extract the L (lightness) channel
2. Adaptive Gaussian threshold (`blockSize=51`, `C=8`, inverted) — dark oysters on a light table become white regions
3. `MORPH_CLOSE` (5×5 ellipse × 2 iterations) to fill shell gaps; `MORPH_OPEN` (5×5 × 1) to remove small noise
4. **Global** watershed — distance transform on the full cleaned mask, threshold at 55% of global maximum, watershed to split touching individuals
5. Filter by area; sort in reading order

**Limitation:** the global distance threshold means large oysters can suppress small neighbours. Results are noticeably worse than the YOLO or mask methods — use only when neither is available.

---

## AREA FILTER (applied by all three methods)

```python
MIN_OYSTER_PX = 2_000    # contours smaller than this are noise / shell fragments
MAX_OYSTER_PX = 500_000  # contours larger than this are merged groups / table background
```

---

## READING-ORDER SORT (applied by all three methods)

Contours are sorted so oyster numbering matches the natural top-to-bottom, left-to-right reading order a human would use:

```python
sort_key = (cy // 80, cx)   # row bucket of 80 px height, then left-to-right within the row
```

---

## TROUBLESHOOTING

| Problem | Cause | Fix |
|---|---|---|
| Oysters merged into one contour (blue mask) | Painted gap too small or MORPH_OPEN bridged it | Re-paint with a wider gap; the gap only needs to be a few pixels |
| Too few oysters detected (YOLO) | Low confidence, overlapping shells | Lower `conf` to 0.15, or lower `iou` to 0.3 in `segment_from_yolo()` |
| Noise detected as oysters | `MIN_OYSTER_PX` too low | Raise `MIN_OYSTER_PX` |
| Real oysters missed | `MIN_OYSTER_PX` too high | Lower `MIN_OYSTER_PX` |
| YOLO silently degraded to adaptive threshold | Missing `ultralytics` or `oyster_model.pt` | Check the `[YOLO]` warning printed to stdout; install/download accordingly |

---

## OUTPUT

Returns a list of OpenCV contours (each is a `numpy` array of shape `[N, 1, 2]`) sorted in reading order. This list is passed directly into the measure-dimensions step.
