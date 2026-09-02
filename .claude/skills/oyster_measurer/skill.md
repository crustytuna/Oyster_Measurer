# Oyster Measurer Skill

Automatically measures individual Pacific oyster (*Crassostrea gigas*) dimensions (length & width in mm) from overhead field photographs taken at **any aquaculture site or location**.

This skill orchestrates four sub-skills in sequence. Read the relevant sub-skill file for full technical detail on each step.

---

## TRIGGER

Activate this skill when the user:
- Provides an oyster image path and asks to measure oyster dimensions
- Asks to "run the oyster measurer" or "measure oysters in [image]"
- Provides a batch folder of raw oyster photos to process

---

## DEPENDENCIES

```bash
pip3 install -r requirements.txt
```

Or directly: `opencv-python-headless numpy scipy Pillow matplotlib openpyxl ultralytics torch torchvision`.

The companion script is at: `.claude/skills/oyster_measurer/measure_oysters.py`

---

## INVOCATION

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    <image_path> \
    [output_dir]  \
    [site_name]   \
    [initials]    \
    [mask_path]   \
    [--px-per-mm VALUE]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `image_path` | Yes | — | Path to the raw oyster JPEG/PNG |
| `output_dir` | No | `~/Desktop` | Where to save the xlsx and diagnostic images |
| `site_name` | No | `Unknown Site` | Written into the xlsx — always provide the actual location |
| `initials` | No | `--` | Measurer initials written into xlsx |
| `mask_path` | No | — | Blue-painted mask PNG — forces blue-mask segmentation *and* red-box calibration |
| `--px-per-mm` | No | — | Manual calibration override; skips auto-detection. Last resort only |

One image per invocation — there is no batch mode. To process a folder, loop in the shell, or use the
Streamlit app (`streamlit run app.py`), which takes several photos at once but requires the user to
type px/mm for each and cannot use masks.

**Example:**
```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    ~/Desktop/oyster_pictures/20260522_bag380_raw.jpeg \
    ~/Desktop \
    "Willapa Bay" \
    AH
```

---

## PIPELINE — FOUR STEPS

Each step is documented in its own sub-skill file under `docs/`.

### Step 1 — Calibration → [`docs/skill_calibration.md`](docs/skill_calibration.md)
Convert the in-frame ruler or scale reference to a pixels-per-millimetre ratio, per image.
Priority: explicit `--px-per-mm` → red box drawn around the ruler in the masked PNG (recommended) →
fixed-ROI tick detection. Within the automatic methods: caliper major ticks (10 mm spacing),
checkered scale bar (10 mm per square), or silver body extent (150 mm span). There is no hardcoded
px/mm constant, and a result outside 1–50 px/mm raises an error instead of producing a wrong number.

### Step 2 — Detect Oysters → [`docs/skill_detect_oysters.md`](docs/skill_detect_oysters.md)
Locate individual oysters and return one contour per oyster.
Priority order: **(1)** blue-painted mask + per-blob watershed, **(2)** trained YOLOv8n-seg model (`models/oyster_model.pt`), **(3)** adaptive threshold + global watershed fallback.
Area filter: `MIN_OYSTER_PX = 2,000` to `MAX_OYSTER_PX = 500,000` — that is the only shape filter.

### Step 3 — Measure Dimensions → [`docs/skill_measure_dimensions.md`](docs/skill_measure_dimensions.md)
Fit an ellipse to each contour (`cv2.fitEllipse`): major axis = length, minor axis = width in
pixels, then divide by px/mm. The centre is the image-moment centroid. Ellipse fitting averages over
all contour points so shell bumps don't inflate the measurement.
Draws green (length) and blue (width) lines through each oyster centre on the annotated image.

### Step 4 — Export to XLSX → [`docs/skill_export_xlsx.md`](docs/skill_export_xlsx.md)
Write `<stem>_measured.xlsx` into `output_dir` — a single sheet, two rows per oyster (length + width).
The annotated image and the diagnostic figure are saved as separate PNGs, not embedded. The Notes
column is written empty; nothing is flagged automatically.

---

## AFTER RUNNING — always report

1. How many oysters were detected
2. The calibration value (px/mm), which method produced it, and whether it falls in the expected 3–25 px/mm range
3. Which detection method was used (blue mask / YOLO / adaptive threshold) — the script prints this
4. Full paths to all three output files (xlsx, annotated PNG, diagnostic PNG)
5. That the output is unvalidated: nothing in the repo has been checked against the 84 hand-measured
   oysters in `oyster_test/`, so do not offer an accuracy figure. Point the user at panel ② of the
   diagnostic figure to sanity-check calibration and panel ⑤ to eyeball the measurement lines.

---

## NOTES ON MEASUREMENT CONVENTIONS

- **Length** = major axis of the fitted ellipse (anterior-posterior or dorsal-ventral depending on orientation)
- **Width** = minor axis of the fitted ellipse
- Measurements are **2D projections** — a tilted shell reads shorter than its true length
- Lay oysters flat before photographing for best accuracy
- The ruler must be in the same focal plane as the oysters
- This skill works for Pacific oyster from **any site or region** — never assume or hard-code a location
