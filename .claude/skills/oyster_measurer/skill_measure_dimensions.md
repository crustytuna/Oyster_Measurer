# Skill: Oyster Dimension Measurement

Takes the list of oyster contours from the detection step and computes the **length** (longest axis) and **width** (shortest axis) of each oyster in millimetres using PCA axis fitting.

---

## TRIGGER

Activate this sub-skill when:
- Oyster contours have been detected and need to be measured
- The user asks why a measurement looks too long, too short, or why length ≈ width on an elongated oyster
- Adjusting what counts as length vs. width

---

## WHAT THIS DOES IN THE CODE

`measure_oyster()` in `measure_oysters.py` (lines 394–417), called once per contour. `draw_measurements()` (lines 420–457) renders the result onto the image.

---

## HOW MEASUREMENT WORKS — PCA AXIS FITTING

For each contour:

1. **Extract contour coordinates** — reshape the `[N, 1, 2]` contour array to `[N, 2]` as float32
2. **Run PCA** with `cv2.PCACompute(pts, mean=None)`:
   - Returns `mean` (centroid of the shell outline) and `eigvec` (two orthogonal eigenvectors)
   - Eigenvector 0 = direction of greatest variance = the **major axis** (length direction)
   - Eigenvector 1 = direction of least variance = the **minor axis** (width direction)
3. **Project all points onto each axis:**
   ```python
   centered = pts - mean
   proj0 = centered @ eigvec[0]   # scalar projection onto major axis
   proj1 = centered @ eigvec[1]   # scalar projection onto minor axis
   ```
4. **Span = dimension in pixels:**
   ```python
   length_px = proj0.max() - proj0.min()
   width_px  = proj1.max() - proj1.min()
   ```
5. **Ensure length ≥ width** — swap if needed (happens when the oyster is nearly circular and PCA randomly assigns the axes)
6. **Convert to mm:** `length_mm = length_px / px_per_mm`

Returns: `(cx, cy, length_px, width_px, angle_deg, eigvec)` — centroid coordinates, pixel dimensions, orientation angle, and the eigenvectors used for drawing.

---

## WHAT IS MEASURED — BIOLOGICAL CONVENTION

- **Length** = the longest axis through the oyster body, corresponding to the anterior-posterior or dorsal-ventral axis depending on how the shell is oriented
- **Width** = the perpendicular axis through the same centroid
- These are **2D projected dimensions** from a top-down photograph — not caliper measurements
- A tilted shell will appear shorter than its true length; lay oysters flat before photographing

---

## HOW IT IS DRAWN ON THE ANNOTATED IMAGE

`draw_measurements()` renders onto the raw image:
- **Green line** = length axis, drawn from centroid ± half-length along eigvec[0]
- **Blue line** = width axis, drawn from centroid ± half-width along eigvec[1]
- **Red dot** = centroid `(cx, cy)`
- **Oyster number** = white text with dark outline, positioned at the centroid

The axis lines extend to the actual detected edge of the shell outline — they are not approximations.

---

## KNOWN LIMITATION — PCA SPAN ON IRREGULAR SHELLS

PCA projects all contour *boundary* points and takes the full span. On a very irregular or concave shell (like an oyster with a pronounced curvature or a large notch), the outermost boundary points along the major axis may be farther apart than the true "straight-line" shell length, causing a slight overestimate.

This is a known issue documented in the roadmap (M4) as a candidate for a min-area-rect or convex-hull comparison.

---

## OUTPUT

Each call to `measure_oyster(contour)` returns a tuple:

```
(cx, cy, length_px, width_px, angle_deg, eigvec)
```

A list of these tuples — one per oyster — is passed into the export step. `length_px / px_per_mm` and `width_px / px_per_mm` give the final millimetre values.
