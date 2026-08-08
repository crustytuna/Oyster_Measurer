# Skill: Oyster Ruler Calibration

Converts an oyster field photograph's ruler or scale reference into a **pixels-per-millimetre (px/mm)** ratio. Every downstream measurement depends on this number being correct.

---

## TRIGGER

Activate this sub-skill when:
- A new image needs a calibration value before oyster measurement can begin
- The user asks "what is the px/mm for this image?"
- A previous calibration value looks implausible (outside ~3–25 px/mm for a typical field photo)
- A new ruler type or scale bar is introduced

---

## WHAT THIS DOES IN THE CODE

`calibrate_ruler()` and `calibrate_from_red_box()` in `measure_oysters.py`. The result feeds every `lpx / px_per_mm` and `wpx / px_per_mm` division in the measurement step.

---

## CALIBRATION PRIORITY (how the script picks a method)

The script tries these in order — the first one that succeeds is used:

### 1. `--px-per-mm` CLI flag (explicit manual override)
```bash
python3 measure_oysters.py 5_raw.jpeg ~/Desktop "Willapa Bay" AH --px-per-mm 3.90
```
Use this only when auto-detection cannot find the ruler. The script prints a visible warning so you know you are overriding. There is no silent hardcoded constant anymore — the old `MANUAL_PX_PER_MM = 2.15` has been deleted.

### 2. Red box in the masked image (preferred automatic method)
If a `mask_path` is provided, the script calls `calibrate_from_red_box()`:
1. Find the red rectangle drawn around the caliper/ruler in the masked PNG
2. Crop the raw image to that bounding box
3. Run robust tick-spacing detection on the crop (see methods below)
4. Return `px/mm`

This is the same approach used automatically for images 21–50 in the batch pipeline. **This is the recommended workflow** — draw a red box around the ruler in every masked image.

### 3. ROI-based fallback (no mask available)
If no mask is provided, `calibrate_ruler()` crops to `RULER_ROI_FRAC = (0.818, 0.52, 0.836, 0.64)` and runs Hough line + column-projection peak detection on that region. This only works reliably when the ruler happens to be in that position. For any other photo, provide a mask with a red box instead.

---

## HOW TICK DETECTION WORKS (methods 2 and 3)

### Caliper major tick marks (default)
Used for any image where a standard vernier caliper is visible.

- Project pixel intensities along both horizontal and vertical axes of the cropped ruler region
- Smooth with a Savitzky-Golay filter
- Run `scipy.signal.find_peaks` at four different minimum-distance thresholds (6, 12, 20, 35 px)
- Score each result: more peaks + lower spacing variation = higher score
- Best-scoring result gives the median tick spacing
- `px/mm = median_spacing / 10` — each major caliper tick is **10 mm** apart

### Checkered scale bar (images 7 & 8)
Same peak-detection approach — the transitions between black and white squares register as peaks. Each square = **10 mm**.

### Silver body extent fallback
Used when tick detection fails (caliper too far from camera, extreme angle, etc.):
1. Isolate the silver/metallic caliper body using HSV range `[0,0,100]–[180,60,255]`
2. Find the span of occupied pixels along the dominant axis
3. `px/mm = span_px / 150` — the caliper body is assumed ~150 mm long

---

## HARDCODED CALIBRATION TABLE (batch pipeline only, images 1–20)

The **batch** script uses pre-verified values for images 1–20. The single-image `measure_oysters.py` script no longer has any hardcoded constant — it always auto-detects.

```python
CALIBRATION = {
    1: 7.95,  2: 11.90,  3:  9.40,  4:  9.25,
    5: 3.90,  6:  3.40,  7:  5.20,  8:  6.20,
    9: 3.30, 10:  3.70, 11: 10.60, 12:  7.15,
   13: 9.40, 14:  6.60, 15: 12.50, 16:  9.65,
   17:13.80, 18: 11.80, 19:  6.48, 20:  4.91,
}
CAL_METHOD = {
    7: "checker bar", 8: "checker bar",
   19: "silver body", 20: "silver body"
}
```

---

## PLAUSIBILITY CHECK

After calibration, the script checks the result automatically:
- **Expected range:** 3–25 px/mm for a typical field photo
- **If outside 1–50 px/mm:** the script raises an error and stops — it does not silently produce wrong measurements
- Panel ② of the diagnostic figure shows the detected tick positions and a 10 mm scale bar overlay — always inspect this panel

---

## CONFIGURATION

| Constant | Default | Purpose |
|---|---|---|
| `RULER_ROI_FRAC` | `(0.818, 0.52, 0.836, 0.64)` | Fallback ROI used only when no mask is provided. `(x0, y0, x1, y1)` as fractions of image size. |
| `RULER_KNOWN_MM` | `10` | mm between major caliper graduation marks |

`RULER_ROI_FRAC` only matters when running without a mask. With a mask and red box, the ruler is located automatically and this constant is ignored.

---

## TROUBLESHOOTING

| Problem | Cause | Fix |
|---|---|---|
| "No red box found in mask" | Red rectangle not drawn in the masked PNG, or too small | Draw a red rectangle around the ruler in the masked image before running |
| "Calibration result X px/mm is implausible" | Tick detection found wrong spacing, or ROI missed the ruler | Check panel ② of the diagnostic; provide `--px-per-mm` as an explicit override |
| ROI-based fallback gives wrong value | `RULER_ROI_FRAC` doesn't frame the ruler in this photo | Provide a mask with a red box instead — that auto-locates the ruler regardless of position |
| Silver body method used unexpectedly | Caliper not close to camera, or at steep angle | Move caliper closer and parallel to the image plane for future photos |

---

## OUTPUT

Returns `px_per_mm` (float) — passed directly into the measure-dimensions step.
