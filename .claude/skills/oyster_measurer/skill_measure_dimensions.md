# Skill: Oyster Dimension Measurement

Takes the list of oyster contours from the detection step and computes the **length** (longest axis) and **width** (shortest axis) of each oyster in millimetres from a minimum-area bounding rectangle.

---

## TRIGGER

Activate this sub-skill when:
- Oyster contours have been detected and need to be measured
- The user asks why a measurement looks too long, too short, or why length ≈ width on an elongated oyster
- Adjusting what counts as length vs. width

---

## WHAT THIS DOES IN THE CODE

`measure_oyster()` in `measure_oysters.py`, called once per contour. `draw_measurements()` renders the result onto the image.

> **History:** PCA axis fitting → `minAreaRect` (commit `fa43402`) → `fitEllipse` (commit `7e5921f`).
> The switch to fitEllipse reduced width MAE from ~13.7 mm to ~12.9 mm on the bag380 ground truth
> (78 matched pairs, px/mm = 2.37). Older notes describing `cv2.PCACompute` or `minAreaRect` no
> longer match the code.

---

## HOW MEASUREMENT WORKS — FITTED ELLIPSE (Method B, validated best)

Three methods were compared on bag380 ground truth (78 matched pairs, px/mm=2.37):

| Method | Length MAE | Length bias | Width MAE | Width bias |
|--------|-----------|-------------|-----------|------------|
| minAreaRect | 15.55mm | −1.48mm | 13.66mm | +12.12mm |
| **fitEllipse** | **15.88mm** | **+7.31mm** | **12.89mm** | **+11.14mm** |
| Contour projection | 16.08mm | +6.99mm | 15.84mm | +14.68mm |

fitEllipse gives the best width MAE and best within-10mm counts on both axes.

For each contour:

1. **Moment centroid** — `cv2.moments()`, then `cx = m10/m00`, `cy = m01/m00`.
2. **Fit ellipse** — `cv2.fitEllipse(contour)` returns centre, `(minor_ax, major_ax)`, angle.
   Falls back to `minAreaRect` for contours with fewer than 5 points.
3. **Assign length and width:**
   ```python
   length_px = max(major_ax, minor_ax)
   width_px  = min(major_ax, minor_ax)
   long_angle = angle if minor_ax >= major_ax else angle + 90.0
   ```
4. **Unit vectors** from `long_angle` for drawing:
   ```python
   ev0 = [cos(θ),  sin(θ)]   # along length
   ev1 = [-sin(θ), cos(θ)]   # along width
   ```
5. **Lines clipped to contour mask** — drawn on a temp layer, only pixels inside the
   filled contour are copied back. Lines cannot visually exceed the red outline.
6. **Convert to mm:** `length_mm = length_px / px_per_mm`

Returns: `(cx, cy, length_px, width_px, angle_deg, eigvec)`.

---

## WHAT IS MEASURED — BIOLOGICAL CONVENTION

- **Length** = the long side of the enclosing rectangle, corresponding to the anterior-posterior or dorsal-ventral axis depending on how the shell is oriented
- **Width** = the short side of that same rectangle
- These are **2D projected dimensions** from a top-down photograph — not caliper measurements
- A tilted shell will appear shorter than its true length; lay oysters flat before photographing

---

## HOW IT IS DRAWN ON THE ANNOTATED IMAGE

`draw_measurements()` renders onto the raw image:
- **Grey outline** = the detected contour
- **Red outline** = detected contour boundary (1px), drawn last so it always shows on top
- **Green line** = length axis, connecting the two contour vertices with the greatest span along `ev0`; clipped inside the contour mask so it cannot exceed the red outline
- **Blue line** = width axis, connecting the two contour vertices with the greatest span along `ev1`; clipped inside the contour mask
- **Blue dot** = centroid `(cx, cy)`
- **Oyster number** = white text with dark outline, centered on centroid, no background box; font scale 0.9–1.3× proportional to oyster size
- Color constants are BGR; they display correctly after BGR→RGB conversion in Streamlit or `cv2.imwrite`

The line lengths equal the measured values exactly, so a line that visibly overshoots or undershoots
the shell is a real sign the measurement is wrong — that is the intended visual check.

---

## KNOWN LIMITATIONS

- **Ellipse fitting averages bumps, not true shell outline.** A strongly curved or irregular shell
  may have a fitted ellipse that doesn't perfectly follow its boundary, but this is generally better
  than a circumscribing rectangle.
- **Merged contours read as one oyster.** YOLO sometimes detects 2–3 touching oysters as a single
  mask. The ellipse fitted to that merged contour over-estimates both length and width. Nothing flags
  this automatically; catch it by eye in the annotated image.
- **bag380 validation (78 matched pairs, px/mm = 2.37):**
  - Length MAE = 15.9 mm, bias = +7.3 mm (pipeline over-estimates)
  - Width MAE = 12.9 mm, bias = +11.1 mm
  - Most of the remaining bias is from YOLO merging touching oysters, not from the measurement algorithm.

---

## OUTPUT

Each call to `measure_oyster(contour)` returns a tuple:

```
(cx, cy, length_px, width_px, angle_deg, eigvec)
```

A list of these tuples — one per oyster — is passed into the export step. `length_px / px_per_mm` and `width_px / px_per_mm` give the final millimetre values.
