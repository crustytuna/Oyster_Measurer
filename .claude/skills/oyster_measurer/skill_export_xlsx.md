# Skill: Export Oyster Measurements to XLSX

Writes all oyster measurements to an Excel workbook on the user's Desktop. One tab per image, plus a Summary tab. Each tab embeds the annotated image directly in the sheet.

---

## TRIGGER

Activate this sub-skill when:
- Oyster measurements are ready to be saved
- The user asks where the output file is, or why a previous output looks wrong
- The user wants to understand the column layout or add/change columns

---

## WHAT THIS DOES IN THE CODE

`openpyxl`-based export in `measure_oysters.py`. The batch pipeline (in `batch_yolo_measure.py` / `measure_oysters.py`'s `run()` function) calls `write_sheet()` per image, then saves the workbook to `~/Desktop`.

---

## OUTPUT FILE

**Location:** `~/Desktop/oyster_measurements_<date>.xlsx`

The filename includes the run date so repeated runs don't overwrite previous results.

---

## WORKBOOK STRUCTURE

### Summary tab (first tab)
One row per image processed:

| Column | Content |
|---|---|
| Image | Image number or filename stem |
| Oysters Detected | Total count for that image |
| px/mm | Calibration value used |
| Cal Method | How calibration was determined (caliper ticks / checker bar / silver body / auto-detected) |
| Model | Detection method used (blue mask / YOLOv8 / adaptive threshold) |

A **TOTAL** row at the bottom sums the oyster count across all images.

### Per-image tabs (one per image, named `Img_1`, `Img_2`, …)

**Two rows per oyster** — one for length, one for width — in alternating fill colours:

| Column | Content |
|---|---|
| Image | Image number |
| Site | Site name passed as argument (always provide the actual site; never hard-code) |
| Model | Detection method used |
| Calibration (px/mm) | `<value> [<method>]`, e.g. `7.95 [caliper ticks]` |
| Oyster # | Sequential integer (1, 2, 3 …) assigned in reading order |
| Measurement | `length` or `width` |
| Value (mm) | Float rounded to 2 decimal places |
| Notes | Flagged if aspect ratio > 3.5 (likely two merged oysters or a fragment) |

**Style:**
- Header row: dark blue fill (`1F4E79`), white bold text
- Alternating row fill: light blue (`D9E1F2`) on even-numbered oysters
- Thin grey borders on every cell
- Column widths: pre-sized for readability

**Embedded annotated image:**
Below the data rows, the annotated image (with green length lines, blue width lines, red centroid dots, and oyster numbers) is embedded directly in the sheet as a thumbnail (max 900 px wide), so measurements and the photo are in the same place.

---

## ASPECT RATIO FLAG

If `length_px / width_px > 3.5` for any oyster, the Notes column is filled with `"unusual aspect (X.X)"`. This flags:
- Two oysters that were detected as a single contour
- Very elongated shell fragments
- A segmentation error where the watershed extended too far

Review these rows in the diagnostic image before including them in analysis.

---

## DEPENDENCIES

```
pip3 install openpyxl Pillow
```

Both are included in the full `requirements.txt` at the repo root.

---

## AFTER THE FILE IS SAVED

Always tell the user:
1. The full path to the xlsx file (e.g., `~/Desktop/oyster_measurements_2026-07-06.xlsx`)
2. Total oyster count across all images
3. How many images were processed vs. skipped (calibration failure = skip)
4. Any rows flagged with unusual aspect ratio — how many and which oyster numbers
