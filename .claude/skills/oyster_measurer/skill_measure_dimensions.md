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

## HOW MEASUREMENT WORKS — FITTED ELLIPSE

For each contour:

1. **Moment centroid** — `cv2.moments()`, then `cx = m10/m00`, `cy = m01/m00`. This is used as the
   centre for drawing. It is more stable than a PCA mean on asymmetric or partially-detected masks.
   A zero-area contour falls back to `(0, 0)`.
2. **Fit an ellipse** — `cv2.fitEllipse(contour)` returns `(cx, cy), (axes[0], axes[1]), angle`:
   the best-fit ellipse through all contour points. `angle` is the rotation of `axes[0]` from the
   horizontal. Requires ≥ 5 contour points; falls back to `minAreaRect` for tiny contours.
3. **Assign length and width:**
   ```python
   length_px = max(axes[0], axes[1])
   width_px  = min(axes[0], axes[1])
   # angle points along axes[0]; rotate 90° if axes[1] is the longer one
   if axes[0] >= axes[1]:
       long_angle = angle
   else:
       long_angle = angle + 90.0
   ```
   Because the ellipse averages over all contour points, shell bumps and protrusions do not inflate
   the measurement the way a circumscribed rectangle does. This matches ImageJ's "Fit Ellipse"
   measurement convention.
4. **Rebuild unit vectors** from `long_angle` for drawing:
   ```python
   ev0 = [cos(θ),  sin(θ)]   # along the length
   ev1 = [-sin(θ), cos(θ)]   # along the width
   ```
5. **Convert to mm:** `length_mm = length_px / px_per_mm`

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
- **Green line** = length axis (major ellipse axis), drawn from the centroid ± half-length along `ev0`
- **Blue line** = width axis (minor ellipse axis), drawn from the centroid ± half-width along `ev1`; color constants are defined in BGR and display correctly as green/blue after BGR→RGB conversion in Streamlit or cv2.imwrite
- **Red dot** = centroid `(cx, cy)`
- **Oyster number** = solid white text on a dark filled rectangle, centered on the centroid; font scale 3.5–5.0× proportional to oyster size

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
