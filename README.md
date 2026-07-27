# Agentic_AI_Summer2026
This repository is dedicated to the development of Agentic AI skills focusing on analyzing biochemical pathways of Pacific oysters when encountering environmental stressors.

## How to use the oyster measurer

The repository includes an oyster measurement workflow at `.claude/skills/oyster_measurer/measure_oysters.py` for extracting oyster length and width measurements from overhead images.

### 1. Install dependencies

```bash
pip3 install opencv-python-headless openpyxl scipy Pillow matplotlib
```

If you want to use the bundled YOLO model automatically when it is available, also install:

```bash
pip3 install ultralytics
```

### 2. Run the script

From the repository root, run:

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    oyster_test/20260522_bag380_raw.jpeg \
    oyster_test \
    "Goose Point" \
    "CC"
```

Optional fifth argument:

- `mask_path`: path to a blue-painted mask image for the same oysters. If omitted, the script uses the YOLO model when present, then falls back to adaptive thresholding.

### 3. Review outputs

The script writes these files to the output directory:

- `<image_stem>_measured.xlsx`
- `<image_stem>_annotated_measured.png`
- `<image_stem>_diagnostic.png`

### Notes

- The script expects a ruler in the image for pixel-to-millimeter calibration.
- Site name and initials are written into the generated spreadsheet.
- Sample input files are available in `oyster_test/`.
