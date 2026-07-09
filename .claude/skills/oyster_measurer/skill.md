# Oyster Measurer Skill

Automatically measures individual oyster dimensions (length & width in mm) from overhead photographs using ruler-based pixel calibration, watershed segmentation, and PCA axis fitting. Outputs an xlsx data file and annotated diagnostic images.

---

## TRIGGER

Activate this skill when the user:
- Provides an oyster image path and asks to measure oyster dimensions
- Asks to "run the oyster measurer" or "measure oysters in [image]"
- Provides a bag number, image name, or folder path containing oyster photos

---

## DEPENDENCIES

Check and install before running:
```
pip3 install opencv-python-headless openpyxl scipy Pillow matplotlib
```

The companion script is at:
`.claude/skills/oyster_measurer/measure_oysters.py`

---

## INVOCATION

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    <image_path> \
    [output_dir]  \
    [site_name]   \
    [initials]
```

**Arguments:**
| Argument | Required | Default | Description |
|---|---|---|---|
| `image_path` | Yes | — | Path to the raw oyster JPEG/PNG |
| `output_dir` | No | `~/Desktop` | Where to save xlsx + diagnostic images |
| `site_name` | No | `Goose Point` | Site name written into xlsx |
| `initials` | No | `CC` | Measurer initials written into xlsx |

**Example:**
```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    ~/Desktop/oyster_pictures/20260522_bag380_raw.jpeg \
    ~/Desktop \
    "Goose Point" \
    AH
```

---

## PIPELINE (6 steps — all shown in diagnostic figure)

### Step ① — Load Image
Read the JPEG/PNG using OpenCV. Print pixel dimensions for reference.

### Step ② — Ruler Calibration
- Crop the ruler region-of-interest (bottom-right quadrant by default; controlled by `RULER_ROI_FRAC` constant in the script)
- Convert to grayscale → Otsu threshold to isolate dark tick marks on a light ruler background
- Project pixel intensities column-wise onto the x-axis to create a 1D tick profile
- Smooth with Savitzky-Golay filter → find peaks (each peak = one 1 mm tick mark)
- **px/mm = median spacing between adjacent tick peaks**
- Visualised in panel ② of the diagnostic: yellow ROI box, red dots on detected ticks, scale bar overlay

### Step ③ — Oyster Segmentation
- Convert to LAB colour space; use the L (lightness) channel
- Adaptive Gaussian thresholding (block size 51 px) to separate dark oysters from the light table surface
- Morphological close + open to fill gaps and remove small noise
- Distance transform → sure foreground / sure background regions
- **Watershed algorithm** to split touching/overlapping oysters into individuals
- Filter regions by area: `MIN_OYSTER_PX` (800 px²) to `MAX_OYSTER_PX` (120,000 px²)
- Visualised in panel ③ (mask) and panel ④ (colour-coded watershed regions)

### Step ④ — Dimension Measurement per Oyster
For each segmented contour:
- Run **PCA (Principal Component Analysis)** on all contour pixel coordinates
- Eigenvector 1 = major axis (longest direction) → **Length**
- Eigenvector 2 = minor axis (perpendicular) → **Width**
- Project contour points onto each axis → span = dimension in pixels → divide by px/mm
- Ensure Length ≥ Width (swap if needed)
- Draw green line (length) and blue line (width) through the oyster centre on the annotated image
- Visualised in panel ⑤; scatter plot in panel ⑥

### Step ⑤ — Export xlsx
Writes one xlsx file matching the reference format:

| Column | Value |
|---|---|
| Site | from argument |
| Image Date | parsed from filename (YYYYMMDD) |
| Initials | from argument |
| Image Name | filename with `_raw` replaced by `_annotated` |
| Tag ID | bag number parsed from filename |
| Oyster | sequential integer (1, 2, 3 …) |
| Measurement | `length` or `width ` |
| Value mm  | float rounded to 2 decimal places |
| Notes  | empty |

Two rows per oyster (length row then width row), alternating fill colours.

### Step ⑥ — Diagnostic Figure
6-panel PNG saved to `output_dir`:
1. Raw image
2. Ruler calibration overlay (tick marks + scale bar + intensity projection inset)
3. Threshold mask
4. Watershed segmentation (colour-coded individuals)
5. Measurement lines overlay (green=length, blue=width, red dot=centre)
6. Scatter plot: length vs width per oyster (numbered)

---

## OUTPUT FILES

| File | Description |
|---|---|
| `<stem>_measured.xlsx` | Data file — one row per measurement |
| `<stem>_annotated_measured.png` | Annotated image with measurement lines |
| `<stem>_diagnostic.png` | 6-panel diagnostic showing every pipeline step |

---

## CONFIGURATION (edit constants in measure_oysters.py)

| Constant | Default | Purpose |
|---|---|---|
| `RULER_ROI_FRAC` | `(0.55, 0.65, 0.85, 0.95)` | ROI for ruler detection as (x0,y0,x1,y1) image fractions |
| `RULER_KNOWN_MM` | `10` | Expected mm span measured on ruler |
| `MIN_OYSTER_PX` | `800` | Minimum contour area (px²) to count as an oyster |
| `MAX_OYSTER_PX` | `120000` | Maximum contour area (px²) — excludes table, ruler, bucket |

---

## AFTER RUNNING — report to the user

After the script finishes, always:
1. State how many oysters were detected
2. Report the calibration value (px/mm) and whether it looks reasonable (expect 5–25 px/mm for a typical field photo)
3. Show or describe the diagnostic image panels
4. Tell the user where the xlsx and annotated image were saved
5. Flag any warnings: calibration failure, unusually high/low oyster count, very small or very large detections that may be noise

---

## TROUBLESHOOTING

| Problem | Likely cause | Fix |
|---|---|---|
| "Could not find ruler tick marks" | `RULER_ROI_FRAC` doesn't cover the ruler | Adjust the four fractions to better crop the ruler region |
| Too few oysters detected | `MIN_OYSTER_PX` too large or threshold too aggressive | Lower `MIN_OYSTER_PX`; try different lighting correction |
| Too many detections (noise) | `MIN_OYSTER_PX` too small | Raise `MIN_OYSTER_PX` |
| Touching oysters merged into one | Watershed failing | Lower the distance threshold inside `segment_oysters()` (currently `0.35 * dist.max()`) |
| px/mm value looks wrong | Ruler is partially obscured or ROI incorrect | Check panel ② of diagnostic; adjust `RULER_ROI_FRAC` |

---

## NOTES ON OYSTER-SPECIFIC MEASUREMENT CONVENTIONS

- **Length** = the longest axis through the oyster body (corresponds to the dorsal-ventral or anterior-posterior axis depending on orientation)
- **Width** = the axis perpendicular to length, measured through the same centre point
- These are **2D projected dimensions** from a top-down photograph — not caliper measurements; slight overestimation occurs if oysters are tilted
- Oysters should be laid flat before photography for best accuracy
- The ruler must be in the same focal plane as the oysters for calibration to be valid
