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

`calibrate_ruler()` in `measure_oysters.py` (lines 59–155). The result feeds every `lpx / px_per_mm` and `wpx / px_per_mm` division in the measurement step.

---

## HOW CALIBRATION WORKS — THREE METHODS (in priority order)

### Method 1 — Caliper tick marks (default)
Used for any image where a standard vernier caliper is visible.

1. Crop the ruler region of interest (ROI): controlled by `RULER_ROI_FRAC` constant in the script
2. Convert ROI to grayscale
3. **Hough line detection** — find nearly-vertical dark lines spanning ≥ 30% of ROI height. These are the major (cm) graduation marks.
4. Cluster nearby detections within 8 px into single marks
5. **Fallback:** if Hough yields < 3 marks, switch to column-projection peak detection (Savitzky-Golay smoothed column sum → `scipy.signal.find_peaks`)
6. Filter out outlier spacings (keep within 50% of median)
7. `px/mm = median_spacing / 10` — each major caliper tick is **10 mm** apart

For images 21–50: the caliper is inside a red box drawn in the masked image. The script crops the raw image to that bounding box, then runs the same tick-detection on the crop.

### Method 2 — Checkered scale bar (images 7 & 8)
Used when a black-and-white checker-pattern scale bar is in frame instead of a caliper.

- Same peak-detection approach, but peaks are the transitions between black and white squares
- Each square = **10 mm**, so spacing between alternating peaks ÷ 2 gives px/mm

### Method 3 — Silver body extent (images 19 & 20)
Fallback when tick detection fails entirely (caliper too far from camera, out of frame, or at an extreme angle).

1. Isolate the silver/metallic body of the caliper using HSV range `[0,0,100]–[180,60,255]`
2. Project the silver mask onto the dominant axis; find the span of occupied pixels
3. `px/mm = span_px / 150` — the caliper body is assumed to be ~150 mm long

---

## HARDCODED CALIBRATION TABLE (images 1–20)

These values were manually verified and are stored directly in the script:

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

Images 21–50 are auto-detected from the red box in the corresponding masked PNG.

---

## PLAUSIBILITY CHECK

After calibration, verify the result is reasonable:
- **Expected range:** 3–25 px/mm for a typical field photo
- **Too low (< 3):** ruler is very far from camera, or wrong ROI — results will be wildly over-sized
- **Too high (> 25):** ruler is extremely close, or a minor tick was detected instead of a major one — results will be undersized
- Panel ② of the diagnostic figure shows the detected tick positions and a 10 mm scale bar overlay — always inspect this panel

---

## CONFIGURATION

| Constant | Default | Purpose |
|---|---|---|
| `RULER_ROI_FRAC` | `(0.818, 0.52, 0.836, 0.64)` | `(x0, y0, x1, y1)` as image fractions — crop this region to find the ruler |
| `RULER_KNOWN_MM` | `10` | mm between major caliper graduation marks |

Adjust `RULER_ROI_FRAC` if the ruler is not in the default position. Check panel ② to see where the current crop lands.

---

## TROUBLESHOOTING

| Problem | Cause | Fix |
|---|---|---|
| `RuntimeError: Ruler calibration failed` | ROI doesn't contain the ruler | Adjust the four `RULER_ROI_FRAC` values to better frame the ruler |
| px/mm is ~10× too high | Minor (1 mm) ticks detected instead of major (10 mm) marks | Increase `min_dist` in `find_peaks` call, or narrow the ROI to exclude minor ticks |
| px/mm looks right but panel ② shows no tick dots | Hough fallback was used — dots won't appear for projection peaks | Normal; check the scale bar overlay instead |
| Silver body method used unexpectedly | Caliper not close to camera, or at steep angle | Move caliper closer and parallel to the image plane |

---

## OUTPUT

Returns `px_per_mm` (float) — passed directly into the measure-dimensions step.
