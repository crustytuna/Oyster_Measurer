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
pip3 install opencv-python-headless openpyxl scipy Pillow matplotlib ultralytics torch
```

The companion script is at: `.claude/skills/oyster_measurer/measure_oysters.py`

---

## INVOCATION

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    <image_path> \
    [output_dir]  \
    [site_name]   \
    [initials]    \
    [mask_path]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `image_path` | Yes | — | Path to the raw oyster JPEG/PNG |
| `output_dir` | No | `~/Desktop` | Where to save the xlsx and diagnostic images |
| `site_name` | No | `Unknown Site` | Written into the xlsx — always provide the actual location |
| `initials` | No | `--` | Measurer initials written into xlsx |
| `mask_path` | No | — | Path to a blue-painted mask PNG — forces blue-mask segmentation |

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

Each step is documented in its own sub-skill file in this directory.

### Step 1 — Calibration → [`skill_calibration.md`](skill_calibration.md)
Convert the in-frame ruler or scale reference to a pixels-per-millimetre ratio.
Three methods: caliper major ticks (10 mm spacing), checkered scale bar (10 mm per square), or silver body extent (150 mm span). For images 1–20, hardcoded values are used. Images 21+ auto-detect from a red box drawn around the ruler in the masked PNG.

### Step 2 — Detect Oysters → [`skill_detect_oysters.md`](skill_detect_oysters.md)
Locate individual oysters and return one contour per oyster.
Priority order: **(1)** blue-painted mask + per-blob watershed, **(2)** trained YOLOv8n-seg model (`oyster_model.pt`), **(3)** adaptive threshold + global watershed fallback.
Area filter: `MIN_OYSTER_PX = 2,000` to `MAX_OYSTER_PX = 500,000`.

### Step 3 — Measure Dimensions → [`skill_measure_dimensions.md`](skill_measure_dimensions.md)
Fit PCA axes to each contour to find length (major axis span) and width (minor axis span) in pixels, then divide by px/mm.
Draws green (length) and blue (width) lines through each oyster centroid on the annotated image.

### Step 4 — Export to XLSX → [`skill_export_xlsx.md`](skill_export_xlsx.md)
Write one Excel workbook to `~/Desktop` — one tab per image, a Summary tab, two rows per oyster (length + width), and the annotated image embedded below the data rows. Flags oysters with aspect ratio > 3.5 in the Notes column.

---

## AFTER RUNNING — always report

1. How many oysters were detected across all images
2. The calibration value (px/mm) and whether it falls in the expected 3–25 px/mm range
3. Which detection method was used (blue mask / YOLO / adaptive threshold)
4. Full path to the xlsx file saved on the Desktop
5. Any Notes-column flags (unusual aspect ratio rows) — how many and which oyster numbers

---

## NOTES ON MEASUREMENT CONVENTIONS

- **Length** = longest axis (anterior-posterior or dorsal-ventral depending on orientation)
- **Width** = perpendicular axis through the same centroid
- Measurements are **2D projections** — a tilted shell reads shorter than its true length
- Lay oysters flat before photographing for best accuracy
- The ruler must be in the same focal plane as the oysters
- This skill works for Pacific oyster from **any site or region** — never assume or hard-code a location
