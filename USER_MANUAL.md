# Oyster Measurement Tool — User Manual

Measure oyster length and width from field photographs using a browser-based web app.
You upload photos, type in the px/mm calibration for each one, and download an XLSX
file matching the lab's data format.

---

## What you need

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.9 | [python.org/downloads](https://www.python.org/downloads/) |
| Git | any | Needed to clone the repository |
| A modern browser | Chrome / Firefox / Safari / Edge | The app opens here automatically |

No paid software or cloud account is required. Everything runs on your own computer.

---

## Installation (one-time setup)

Open a terminal (Mac: **Terminal**; Windows: **Command Prompt** or **PowerShell**).

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/Agentic_AI_Summer2026.git
cd Agentic_AI_Summer2026
```

Replace `<your-org>` with the actual GitHub organisation or username.

### 2. Create a virtual environment

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` appear at the start of your terminal prompt.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs OpenCV, NumPy, PyTorch, YOLOv8 (ultralytics), openpyxl, and Streamlit.
The download is ~1–2 GB on the first run (mostly PyTorch). Subsequent runs are instant.

> **Slow internet?** You can skip the large packages for a first test:
> ```bash
> pip install opencv-python-headless numpy scipy Pillow openpyxl matplotlib streamlit
> ```
> The app will fall back to adaptive-threshold segmentation instead of YOLOv8.
> Accuracy will be lower, but it will run.

---

## Starting the app

Every time you want to use the tool:

```bash
# 1. Activate the virtual environment (if not already active)
source .venv/bin/activate          # Mac / Linux
# .venv\Scripts\activate           # Windows

# 2. Launch the web app
streamlit run app.py
```

Your browser will open automatically at **http://localhost:8501**.
If it doesn't, copy that address and paste it into your browser manually.

To stop the app, press **Ctrl + C** in the terminal.

---

## Using the app

### Step 1 — Upload photos

Click **Browse files** and select one or more field photos (JPEG or PNG).
You can select multiple files at once. Each photo should show oysters and a
caliper in the frame.

### Step 2 — Enter px/mm for each photo

For each uploaded photo you will see a thumbnail and a number input labelled **px/mm**.

**How to measure px/mm:**

1. Open the photo in any image viewer that shows pixel coordinates
   (e.g. Preview on Mac, Paint on Windows, or ImageJ).
2. Find two caliper tick marks that are exactly **1 mm apart** (adjacent minor
   graduations on a standard caliper).
3. Note the x-coordinate (or y-coordinate if the caliper is vertical) of each mark.
4. Subtract to get the pixel distance, e.g. 342 − 337 = **5 px per mm**.
5. Type that number into the **px/mm** field for that photo.

> Typical values: **2–10 px/mm** depending on how close the camera was to the tray.
> If the caliper spans roughly the whole frame, px/mm will be higher (~8–15).

### Step 3 — Metadata

Enter the **site name** (default: *Goose Point*) and your **initials**.
These appear in the XLSX output. Both fields are optional.

### Step 4 — Run & download

Click **▶ Run Analysis**. The app will:

1. Detect oysters in each photo using the trained YOLOv8 model.
2. Measure the length (major axis) and width (minor axis) of each oyster using PCA.
3. Display an annotated image showing every detected oyster with its measurement lines.
4. Show a table of length and width in millimetres for each oyster.

When processing is complete, a **📥 Download XLSX** button appears.
Click it to save a spreadsheet with one sheet per photo, matching the lab's data format:

| Column | Contents |
|---|---|
| Site | Site name you entered |
| Image Date | Parsed from filename (YYYYMMDD) |
| Initials | Your initials |
| Image Name | Filename |
| Tag ID | Bag number parsed from filename (e.g. `bag380` → 380) |
| Oyster | Oyster number (1, 2, 3 …) |
| Measurement | `length` or `width` |
| Value mm | Measurement in millimetres |
| Notes | Empty (fill in manually if needed) |

---

## Troubleshooting

### "YOLOv8 model not found" warning

The app looks for the segmentation model at
`.claude/skills/oyster_measurer/oyster_model.pt`.
Make sure you cloned the full repository and that file is present:

```bash
ls .claude/skills/oyster_measurer/oyster_model.pt
```

If missing, re-clone or ask the project maintainer for the model file.

### No oysters detected in my photo

- The photo may be too dark, blurry, or the tray background is very similar in
  colour to the oysters.
- Try increasing the ambient light or rephotographing with the tray at a slight angle.
- The YOLOv8 model was trained on a specific tray style (Goose Point white mesh).
  Oysters on a very different background may need a retrained model.

### Installation fails on Apple Silicon (M1/M2/M3)

PyTorch supports Apple Silicon natively. If you get an error, try:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Port 8501 already in use

Another Streamlit session is running. Either stop it (Ctrl+C in the original
terminal) or run on a different port:

```bash
streamlit run app.py --server.port 8502
```

---

## Updating the app

```bash
git pull
pip install -r requirements.txt   # picks up any new dependencies
streamlit run app.py
```

---

## File naming convention

The app automatically parses **date** and **bag number** from the filename if
it follows the pattern:

```
YYYYMMDD_bag###_raw.jpeg
```

Example: `20260522_bag380_raw.jpeg` → date 20260522, tag ID 380.

If your filename does not follow this pattern, the date and tag ID columns in
the XLSX will be 0. You can fill them in manually after downloading.
