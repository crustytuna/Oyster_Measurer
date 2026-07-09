"""
measure_oysters.py — Oyster Dimension Measurement Tool
Pacific Oyster Lab — Goose Point

Pipeline:
  1. Load image
  2. Calibrate: detect ruler tick marks → compute px/mm ratio
  3. Detect oysters via adaptive thresholding + watershed
  4. Measure each oyster: PCA axes → length (major) & width (minor)
  5. Export xlsx matching the reference data format
  6. Save annotated diagnostic images showing every step
"""

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from pathlib import Path
from datetime import datetime
import sys
import os
import re

# ── Configuration ─────────────────────────────────────────────────────────────
RULER_KNOWN_MM   = 10          # the span we measure on the ruler
MIN_OYSTER_PX    = 800         # minimum contour area (pixels²) to count as oyster
MAX_OYSTER_PX    = 120_000     # maximum (avoids picking up the whole table)
RULER_ROI_FRAC   = (0.55, 0.65, 0.85, 0.95)  # (x0,y0,x1,y1) as fraction of image

# ── Colours (BGR for OpenCV, then converted) ──────────────────────────────────
COL_LENGTH = (0,   220,  50)   # green
COL_WIDTH  = (50,  120, 255)   # blue
COL_CENTER = (255,  50,  50)   # red
COL_RULER  = (0,  200, 255)    # yellow-ish

# ─────────────────────────────────────────────────────────────────────────────
def load_image(path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {path}")
    return img

# ── STEP 1: Ruler calibration ─────────────────────────────────────────────────
def calibrate_ruler(img, known_mm=RULER_KNOWN_MM, roi_frac=RULER_ROI_FRAC):
    """
    Crop the ruler region-of-interest, find vertical tick marks using
    column-wise intensity projection, then compute px-per-mm.
    Returns (px_per_mm, ruler_roi_coords, tick_positions_in_full_img)
    """
    h, w = img.shape[:2]
    x0 = int(roi_frac[0] * w);  y0 = int(roi_frac[1] * h)
    x1 = int(roi_frac[2] * w);  y1 = int(roi_frac[3] * h)

    roi = img[y0:y1, x0:x1]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # The ruler has dark tick marks on a light background.
    # Invert so ticks are bright, then project onto x-axis.
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    col_proj = thresh.sum(axis=0).astype(float)

    # Smooth and find local maxima (tick positions)
    from scipy.signal import find_peaks, savgol_filter
    smooth = savgol_filter(col_proj, window_length=max(5, len(col_proj)//40 | 1), polyorder=2)
    peaks, props = find_peaks(smooth,
                              distance=max(5, len(smooth)//60),
                              prominence=smooth.max() * 0.12)

    # Use median spacing between peaks as 1 mm; RULER_KNOWN_MM ticks = RULER_KNOWN_MM mm
    if len(peaks) < 2:
        raise RuntimeError("Could not find ruler tick marks. Check RULER_ROI_FRAC.")

    spacings = np.diff(peaks)
    median_spacing = float(np.median(spacings))
    px_per_mm = median_spacing   # each tick = 1 mm

    # Map tick x positions back to full image coords
    tick_x_full = peaks + x0
    tick_y_full = (y0 + y1) // 2

    return px_per_mm, (x0, y0, x1, y1), tick_x_full, tick_y_full, col_proj, smooth, peaks

# ── STEP 2: Oyster segmentation ───────────────────────────────────────────────
def segment_oysters(img):
    """
    Convert to LAB colour space, use the A channel (red-green) to
    separate brownish oysters from the white/grey table surface.
    Watershed is applied to split touching individuals.
    Returns list of contours.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)

    # Oysters tend to be darker (low L) and more saturated (higher B)
    # Build a combined darkness + saturation mask
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)

    # Adaptive threshold on the L channel
    thresh_L = cv2.adaptiveThreshold(
        L, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=51, C=8)

    # Morphological clean-up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(thresh_L, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN,  kernel, iterations=1)

    # --- Watershed to split touching oysters ---
    dist = cv2.distanceTransform(cleaned, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, 0.35 * dist.max(), 255, 0)
    sure_fg = sure_fg.astype(np.uint8)

    sure_bg = cv2.dilate(cleaned, kernel, iterations=3)
    unknown = cv2.subtract(sure_bg, sure_fg)

    _, markers = cv2.connectedComponents(sure_fg)
    markers += 1
    markers[unknown == 255] = 0

    img_ws = img.copy()
    markers = cv2.watershed(img_ws, markers)

    # Extract contours from each watershed region
    contours = []
    for label in np.unique(markers):
        if label <= 1:   # background or border
            continue
        mask = np.zeros(gray.shape, np.uint8)
        mask[markers == label] = 255
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if MIN_OYSTER_PX < area < MAX_OYSTER_PX:
                contours.append(c)

    # Sort left-to-right, top-to-bottom (reading order)
    def sort_key(c):
        M = cv2.moments(c)
        if M["m00"] == 0:
            return (0, 0)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cy // 80, cx)   # row-major buckets of 80 px

    contours.sort(key=sort_key)
    return contours

# ── STEP 3: Measure one oyster via PCA ────────────────────────────────────────
def measure_oyster(contour):
    """
    Fit PCA on contour points to get the major (length) and minor (width) axes.
    Returns (cx, cy, length_px, width_px, angle_deg, eigenvectors)
    """
    pts = contour.reshape(-1, 2).astype(np.float32)
    mean, eigvec = cv2.PCACompute(pts, mean=None)
    cx, cy = float(mean[0, 0]), float(mean[0, 1])

    # Project points onto each eigenvector
    centered = pts - mean
    proj0 = centered @ eigvec[0]   # major axis
    proj1 = centered @ eigvec[1]   # minor axis

    length_px = float(proj0.max() - proj0.min())
    width_px  = float(proj1.max() - proj1.min())

    # Ensure length ≥ width
    if width_px > length_px:
        length_px, width_px = width_px, length_px
        eigvec = eigvec[[1, 0]]   # swap

    angle = float(np.degrees(np.arctan2(eigvec[0, 1], eigvec[0, 0])))
    return cx, cy, length_px, width_px, angle, eigvec

# ── STEP 4: Draw measurement lines on a copy of the image ─────────────────────
def draw_measurements(img, contours, measurements, px_per_mm):
    vis = img.copy()
    for idx, (contour, (cx, cy, lpx, wpx, angle, eigvec)) in \
            enumerate(zip(contours, measurements), start=1):

        # Contour outline
        cv2.drawContours(vis, [contour], -1, (200, 200, 200), 1)

        half_l = lpx / 2
        half_w = wpx / 2

        # Length line (major axis)
        ev0 = eigvec[0]
        p1 = (int(cx + half_l * ev0[0]), int(cy + half_l * ev0[1]))
        p2 = (int(cx - half_l * ev0[0]), int(cy - half_l * ev0[1]))
        cv2.line(vis, p1, p2, COL_LENGTH, 2)

        # Width line (minor axis)
        ev1 = eigvec[1]
        p3 = (int(cx + half_w * ev1[0]), int(cy + half_w * ev1[1]))
        p4 = (int(cx - half_w * ev1[0]), int(cy - half_w * ev1[1]))
        cv2.line(vis, p3, p4, COL_WIDTH, 2)

        # Centre dot
        cv2.circle(vis, (int(cx), int(cy)), 5, COL_CENTER, -1)

        # Label
        label = str(idx)
        font_scale = max(0.45, min(0.75, lpx / 220))
        cv2.putText(vis, label,
                    (int(cx) + 6, int(cy) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(vis, label,
                    (int(cx) + 6, int(cy) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (30, 30, 30), 1, cv2.LINE_AA)
    return vis

# ── STEP 5: Ruler diagnostic ───────────────────────────────────────────────────
def draw_ruler_calibration(img, ruler_roi, tick_x_full, tick_y, px_per_mm):
    vis = img.copy()
    x0, y0, x1, y1 = ruler_roi
    cv2.rectangle(vis, (x0, y0), (x1, y1), COL_RULER, 3)
    # Mark first two ticks used for scale
    for tx in tick_x_full[:20]:
        cv2.line(vis, (tx, tick_y - 18), (tx, tick_y + 18), COL_RULER, 2)
    # Draw a 10 mm scale bar
    bar_x = tick_x_full[0]
    bar_y = tick_y + 30
    bar_end = bar_x + int(10 * px_per_mm)
    cv2.line(vis, (bar_x, bar_y), (bar_end, bar_y), COL_RULER, 3)
    cv2.putText(vis, "10 mm",
                (bar_x, bar_y + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, COL_RULER, 2)
    return vis

# ── STEP 6: Export xlsx ────────────────────────────────────────────────────────
def export_xlsx(measurements, px_per_mm, image_path, out_path,
                site="Goose Point", initials="CC"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    # Parse date + tag from filename  e.g. 20260522_bag380_raw.jpeg
    stem = Path(image_path).stem
    date_match = re.search(r'(\d{8})', stem)
    tag_match  = re.search(r'bag(\d+)', stem)
    image_date = int(date_match.group(1)) if date_match else 0
    tag_id     = int(tag_match.group(1))  if tag_match  else 0
    image_name = stem.replace("_raw", "_annotated")

    # Header row
    headers = ["Site","Image Date","Initials","Image Name",
               "Tag ID","Oyster","Measurement","Value mm ","Notes "]
    hdr_fill = PatternFill("solid", fgColor="1F4E79")
    hdr_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    # Data rows — 2 rows per oyster (length then width)
    alt_fill = PatternFill("solid", fgColor="D9E1F2")
    row_num = 2
    for idx, (_, (_, _, lpx, wpx, *_)) in enumerate(measurements, start=1):
        length_mm = round(lpx / px_per_mm, 2)
        width_mm  = round(wpx / px_per_mm, 2)
        fill = alt_fill if idx % 2 == 0 else PatternFill()

        for meas, val in [("length", length_mm), ("width ", width_mm)]:
            row_data = [site, image_date, initials, image_name,
                        tag_id, idx, meas, val, None]
            for col, v in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col, value=v)
                cell.fill = fill
                cell.border = border
                cell.alignment = Alignment(horizontal="center")
            row_num += 1

    # Column widths
    for col, width in enumerate([14,14,10,34,8,8,12,12,10], 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

    wb.save(str(out_path))
    print(f"  Saved xlsx → {out_path}")

# ── STEP 7: Multi-panel diagnostic figure ─────────────────────────────────────
def save_diagnostic(img_raw, img_ruler, img_segmented, img_measured,
                    col_proj, smooth, peaks, ruler_roi, px_per_mm,
                    measurements, out_path):
    fig = plt.figure(figsize=(22, 20))
    fig.patch.set_facecolor("#0D1B2A")

    title_kw = dict(color="white", fontsize=12, fontweight="bold", pad=8)

    def show(ax, img_bgr, title, cmap=None):
        ax.set_facecolor("#0D1B2A")
        if img_bgr.ndim == 3:
            ax.imshow(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        else:
            ax.imshow(img_bgr, cmap=cmap or "gray")
        ax.set_title(title, **title_kw)
        ax.axis("off")

    # Panel 1: raw image
    ax1 = fig.add_subplot(3, 2, 1)
    show(ax1, img_raw, "① Raw Image")

    # Panel 2: ruler calibration overlay
    ax2 = fig.add_subplot(3, 2, 2)
    show(ax2, img_ruler, f"② Ruler Calibration\n{px_per_mm:.2f} px / mm")
    # inset ruler projection
    ax_ins = ax2.inset_axes([0.0, 0.0, 1.0, 0.22])
    ax_ins.set_facecolor("#0D1B2A")
    x0, y0, x1, y1 = ruler_roi
    roi_w = x1 - x0
    ax_ins.plot(col_proj[:roi_w], color="#8FA3B1", linewidth=0.8, alpha=0.6, label="raw proj")
    ax_ins.plot(smooth[:roi_w],   color="#F1C40F", linewidth=1.2, label="smoothed")
    ax_ins.scatter(peaks[peaks < roi_w], smooth[peaks[peaks < roi_w]],
                   color="#E74C3C", s=18, zorder=5, label="ticks")
    ax_ins.set_xticks([]); ax_ins.set_yticks([])
    ax_ins.spines[:].set_visible(False)

    # Panel 3: thresholded mask
    gray = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
    lab  = cv2.cvtColor(img_raw, cv2.COLOR_BGR2LAB)
    L    = cv2.split(lab)[0]
    mask = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 51, 8)
    ax3 = fig.add_subplot(3, 2, 3)
    show(ax3, mask, "③ Adaptive Threshold Mask\n(oysters = white)", cmap="gray")

    # Panel 4: segmented / watershed
    ax4 = fig.add_subplot(3, 2, 4)
    show(ax4, img_segmented, "④ Watershed Segmentation\n(each colour = 1 oyster)")

    # Panel 5: measurements overlay
    ax5 = fig.add_subplot(3, 2, 5)
    show(ax5, img_measured,
         "⑤ Dimension Measurement Lines\nGreen = Length  |  Blue = Width")

    # Panel 6: scatter of length vs width
    ax6 = fig.add_subplot(3, 2, 6)
    ax6.set_facecolor("#132338")
    lengths = [lpx / px_per_mm for (_, (_, _, lpx, wpx, *_)) in measurements]
    widths  = [wpx / px_per_mm for (_, (_, _, lpx, wpx, *_)) in measurements]
    sc = ax6.scatter(lengths, widths, c=range(len(lengths)),
                     cmap="plasma", s=60, edgecolors="white", linewidths=0.5, alpha=0.9)
    for i, (l, w) in enumerate(zip(lengths, widths), 1):
        ax6.annotate(str(i), (l, w), fontsize=5.5, color="white",
                     ha="center", va="bottom", xytext=(0, 4),
                     textcoords="offset points")
    ax6.set_xlabel("Length (mm)", color="white", fontsize=10)
    ax6.set_ylabel("Width (mm)",  color="white", fontsize=10)
    ax6.set_title("⑥ Length vs Width per Oyster", **title_kw)
    ax6.tick_params(colors="white")
    for s in ax6.spines.values(): s.set_color("#3D5A73")
    plt.colorbar(sc, ax=ax6, label="Oyster #").ax.yaxis.label.set_color("white")

    # Legend patches
    patches = [
        mpatches.Patch(color="#00DC32", label="Length line (major PCA axis)"),
        mpatches.Patch(color="#3278FF", label="Width line (minor PCA axis)"),
        mpatches.Patch(color="#FF3232", label="Centre point"),
    ]
    fig.legend(handles=patches, loc="lower center", ncol=3,
               framealpha=0.2, labelcolor="white", fontsize=9,
               facecolor="#0D1B2A", edgecolor="#3D5A73")

    fig.suptitle(
        f"Oyster Measurement Diagnostic  ·  {Path(img_measured).name if hasattr(img_measured,'__fspath__') else 'Bag 380'}\n"
        f"Calibration: {px_per_mm:.2f} px/mm  ·  Oysters detected: {len(measurements)}",
        color="white", fontsize=14, fontweight="bold", y=0.995
    )
    plt.tight_layout(rect=[0, 0.04, 1, 0.99])
    plt.savefig(str(out_path), dpi=160, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved diagnostic → {out_path}")

# ── Colour-coded segmentation visualisation ───────────────────────────────────
def coloured_segments(img, contours):
    vis = img.copy()
    np.random.seed(42)
    for c in contours:
        col = [int(x) for x in np.random.randint(80, 255, 3)]
        cv2.drawContours(vis, [c], -1, col, cv2.FILLED)
    blended = cv2.addWeighted(img, 0.45, vis, 0.55, 0)
    return blended

# ── Main ──────────────────────────────────────────────────────────────────────
def run(image_path, out_dir=None, site="Goose Point", initials="CC"):
    image_path = Path(image_path)
    if out_dir is None:
        out_dir = Path.home() / "Desktop"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem.replace("_raw", "")
    print(f"\n{'='*60}")
    print(f"  Oyster Measurer — {image_path.name}")
    print(f"{'='*60}")

    # ① Load
    print("\n① Loading image...")
    img = load_image(image_path)
    h, w = img.shape[:2]
    print(f"   {w} × {h} px")

    # ② Calibrate
    print("\n② Calibrating ruler...")
    px_per_mm, ruler_roi, tick_x, tick_y, col_proj, smooth, peaks = \
        calibrate_ruler(img, known_mm=RULER_KNOWN_MM)
    print(f"   Detected {len(peaks)} tick marks")
    print(f"   Calibration: {px_per_mm:.3f} px/mm  (median tick spacing)")
    img_ruler = draw_ruler_calibration(img, ruler_roi, tick_x, tick_y, px_per_mm)

    # ③ Segment
    print("\n③ Segmenting oysters (watershed)...")
    contours = segment_oysters(img)
    print(f"   Detected {len(contours)} oyster individuals")
    img_seg = coloured_segments(img, contours)

    # ④ Measure
    print("\n④ Measuring dimensions...")
    measurements = []
    for i, c in enumerate(contours, 1):
        m = measure_oyster(c)
        cx, cy, lpx, wpx, angle, _ = m
        lmm = lpx / px_per_mm
        wmm = wpx / px_per_mm
        print(f"   Oyster {i:>3d}: length={lmm:6.2f} mm  width={wmm:6.2f} mm  "
              f"(angle={angle:.1f}°)")
        measurements.append((c, m))

    img_meas = draw_measurements(img, contours,
                                  [m for (_, m) in measurements], px_per_mm)

    # ⑤ Export xlsx
    print("\n⑤ Exporting xlsx...")
    xlsx_path = out_dir / f"{stem}_measured.xlsx"
    export_xlsx(measurements, px_per_mm, image_path, xlsx_path,
                site=site, initials=initials)

    # ⑥ Save annotated image
    ann_path = out_dir / f"{stem}_annotated_measured.png"
    cv2.imwrite(str(ann_path), img_meas)
    print(f"  Saved annotated image → {ann_path}")

    # ⑦ Diagnostic figure
    print("\n⑥ Saving diagnostic figure...")
    diag_path = out_dir / f"{stem}_diagnostic.png"
    save_diagnostic(img, img_ruler, img_seg, img_meas,
                    col_proj, smooth, peaks, ruler_roi, px_per_mm,
                    measurements, diag_path)

    print(f"\n{'='*60}")
    print(f"  DONE  —  {len(measurements)} oysters measured")
    print(f"  xlsx       → {xlsx_path}")
    print(f"  annotated  → {ann_path}")
    print(f"  diagnostic → {diag_path}")
    print(f"{'='*60}\n")
    return measurements, px_per_mm

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 measure_oysters.py <image_path> [output_dir] [site] [initials]")
        sys.exit(1)
    img_path  = sys.argv[1]
    out_dir   = sys.argv[2] if len(sys.argv) > 2 else None
    site      = sys.argv[3] if len(sys.argv) > 3 else "Goose Point"
    initials  = sys.argv[4] if len(sys.argv) > 4 else "CC"
    run(img_path, out_dir, site, initials)
