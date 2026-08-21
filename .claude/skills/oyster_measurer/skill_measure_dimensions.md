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

> **History:** this step used PCA axis fitting until commit `fa43402`, which replaced it with the
> minimum-area rectangle described below because PCA span overestimated length on irregular shells.
> Older notes describing `cv2.PCACompute` no longer match the code.

---

## HOW MEASUREMENT WORKS — MINIMUM-AREA BOUNDING RECTANGLE

For each contour:

1. **Moment centroid** — `cv2.moments()`, then `cx = m10/m00`, `cy = m01/m00`. This is used as the
   centre for drawing. It is more stable than a PCA mean on asymmetric or partially-detected masks.
   A zero-area contour falls back to `(0, 0)`.
2. **Fit the rectangle** — `cv2.minAreaRect(contour)` returns `(centre), (rw, rh), rect_angle`: the
   smallest rectangle of any rotation that encloses the contour.
3. **Assign length and width by side, not by axis order:**
   ```python
   if rw >= rh:
       length_px, width_px, long_angle = rw, rh, rect_angle
   else:
       length_px, width_px, long_angle = rh, rw, rect_angle + 90.0
   ```
   Length ≥ width always holds by construction — there is no separate swap step, and no random axis
   assignment on near-circular shells.
4. **Rebuild unit vectors** from `long_angle` for drawing:
   ```python
   ev0 = [cos(θ),  sin(θ)]   # along the length
   ev1 = [-sin(θ), cos(θ)]   # along the width
   ```
   These are returned in an `eigvec`-shaped array purely so `draw_measurements()` keeps its old
   interface — they are rectangle-side directions, not eigenvectors.
5. **Convert to mm:** `length_mm = length_px / px_per_mm`

Returns: `(cx, cy, length_px, width_px, angle_deg, eigvec)`.

Note that the rectangle is fitted around the contour, while the centre comes from the moments, so the
two are computed independently. On a strongly asymmetric shell the drawn lines are centred slightly
off the rectangle's own centre.

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
- **Green line** = length axis, drawn from the centroid ± half-length along `ev0`
- **Blue line** = width axis, drawn from the centroid ± half-width along `ev1`
- **Red dot** = centroid `(cx, cy)`
- **Oyster number** = white text with a dark outline, positioned near the centroid

The line lengths equal the measured values exactly, so a line that visibly overshoots or undershoots
the shell is a real sign the measurement is wrong — that is the intended visual check.

---

## KNOWN LIMITATIONS

- **The rectangle circumscribes the shell.** A curved or banana-shaped oyster needs a rectangle longer
  than its straight-line shell length, so length is still biased slightly high — less so than the
  previous PCA span, but not zero.
- **Merged contours read as one oyster.** Two shells detected as a single contour produce one long
  rectangle. Nothing flags this automatically; it has to be caught by eye in the annotated image.
- **Unquantified.** No version of this step has been compared against the 84 hand-measured oysters in
  `oyster_test/20260522_bag380_data.xlsx`, so the size of any bias is unknown (roadmap M2). Do not
  quote an accuracy figure.

---

## OUTPUT

Each call to `measure_oyster(contour)` returns a tuple:

```
(cx, cy, length_px, width_px, angle_deg, eigvec)
```

A list of these tuples — one per oyster — is passed into the export step. `length_px / px_per_mm` and `width_px / px_per_mm` give the final millimetre values.
