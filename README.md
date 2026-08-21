# Agentic AI — Summer 2026

Agentic AI tooling for Pacific oyster (*Magallana gigas* / *Crassostrea gigas*) research. The repo
holds a computer-vision pipeline that measures individual oyster length and width in millimetres from
overhead field photographs.

There are three ways to run it:

| Entry point | Use it for | Calibration |
|---|---|---|
| **Streamlit web app** (`app.py`) | Students / field staff, several photos at a time | You type px/mm per photo |
| **CLI script** (`measure_oysters.py`) | One photo, full diagnostics, scripting | Automatic from the in-frame ruler |
| **Claude Code skill** (`/oyster_measurer`) | Conversational use inside Claude Code | Same as the CLI |

See [ROADMAP.md](ROADMAP.md) for the development milestones and [USER_MANUAL.md](USER_MANUAL.md) for
the step-by-step, non-programmer guide to the web app.

---

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Conda users can substitute `conda env create -f environment.yml`.

`ultralytics` and `torch` are large (~1–2 GB) but strongly recommended: without them the pipeline
falls back to adaptive thresholding, which is considerably less accurate than the trained
segmentation model. `requirements-app.txt` is a slimmer subset used for Streamlit Cloud deployment —
use `requirements.txt` for local work and training.

---

## Web app

```bash
streamlit run app.py
```

Opens at <http://localhost:8501>. Upload one or more photos, enter the px/mm ratio for each, add site
and initials, then **Run Analysis** to get annotated images, per-photo tables, and a combined XLSX
download (one sheet per photo).

The app is deliberately simpler than the CLI: it asks you for px/mm instead of detecting the ruler,
uses the YOLO model (falling back to adaptive threshold), and does not support blue masks or produce
the diagnostic figure. Full walkthrough, including how to read px/mm off a caliper, is in
[USER_MANUAL.md](USER_MANUAL.md).

---

## CLI

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py \
    oyster_test/20260522_bag380_raw.jpeg results/ "Goose Point" AH
```

Positional arguments: `image_path`, then optional `output_dir` (default `~/Desktop`), `site`
(default `Unknown Site`), `initials` (default `--`), and `mask_path`. Plus one flag,
`--px-per-mm <value>`, to override calibration.

Passing `mask_path` — an image of the same oysters hand-painted solid blue, with a red rectangle
drawn around the ruler — switches segmentation to the mask and calibration to the red box. This is
the most accurate mode and the reliable escape hatch when automatic detection misses or merges
oysters.

**Pipeline:** load image → calibrate px/mm → segment individual oysters → fit a minimum-area
bounding rectangle per oyster for length (long side) and width (short side) → export `.xlsx` →
render a 6-panel diagnostic figure showing every step.

**Outputs** (in `output_dir`, named from the filename stem with `_raw` stripped):
`<stem>_measured.xlsx`, `<stem>_annotated_measured.png`, `<stem>_diagnostic.png`.

### Calibration

Calibration is per-image and never reused. The script tries, in order:

1. `--px-per-mm` if given — prints a loud warning that it is overriding detection.
2. **Red box in the mask** (`calibrate_from_red_box`) — crops the raw image to the red rectangle and
   finds the most regular tick or checker-square spacing, treating one major interval as 10 mm.
   Falls back within this method to the silver caliper body span ÷ 150 mm. This is the recommended
   workflow.
3. **Fixed ROI tick detection** (`calibrate_ruler`) when no mask is given — uses the hardcoded
   `RULER_ROI_FRAC = (0.818, 0.52, 0.836, 0.64)`, which is tuned to the bag 380 photo and will miss
   the ruler in a differently framed image.

A result outside 1–50 px/mm raises an error rather than producing a wrong number. Values in the
3–25 px/mm range are typical for a field photo — check panel ② of the diagnostic figure before
trusting output from route 3.

### Segmentation

Three tiers, in priority order: **(1)** blue-painted mask + per-blob watershed, **(2)** the trained
YOLOv8n-seg model `oyster_model.pt`, **(3)** adaptive threshold + watershed. Contours are filtered to
2,000–500,000 px² and sorted into reading order. The script prints which tier ran.

Full argument reference and troubleshooting: [`.claude/skills/oyster_measurer/skill.md`](.claude/skills/oyster_measurer/skill.md),
plus one sub-skill file per pipeline stage in the same directory.

---

## Model

`oyster_model.pt` is a YOLOv8n-seg model, byte-identical to `oyster_model_v3.pt`;
`oyster_model_v1.pt` and `oyster_model_v2.pt` are earlier checkpoints kept for comparison.
`train_oyster_model.py` reproduces the training run: it reads blue-painted masks from
`~/Desktop/oyster_pictures/`, converts them to YOLO polygon labels, and fine-tunes from a pretrained
base or an existing checkpoint.

```bash
python3 .claude/skills/oyster_measurer/train_oyster_model.py --images 1-50
```

| Checkpoint | Training images | Recorded mAP50 |
|---|---|---|
| v1 | 1–15 | 0.506 |
| v2 | 1–20 (from v1) | 0.591 |
| v3 = current | 1–50 (from v2), 4031 polygons, 52 epochs | 0.209 |

Those numbers are **not comparable and not accuracy estimates** — each was measured on the model's own
training set rather than a held-out split. v3's much lower figure most likely reflects a harder,
more varied 50-image set rather than a worse model, but nothing in the repo establishes that. With no
model card and no held-out evaluation, the weights cannot yet be audited or ranked (roadmap M3).
Known false-positive sources: barnacles, rocks, and debris on similar-toned backgrounds.

---

## Test data

`oyster_test/` holds one photo of bag 380 (2026-05-22, Goose Point) — raw JPEG, the ImageJ-annotated
TIFF and flattened PNG, and **84 oysters measured by hand** in `20260522_bag380_data.xlsx`
(169 rows: length + width per oyster). This is the ground truth for the validation harness.

---

## Known limitations

- **Accuracy is unquantified.** Nothing in the repo compares output against the 84 hand-measured
  oysters, so there is no MAE, bias, or detection precision/recall number for any version of the
  pipeline or the model. This is roadmap M2 and it gates every claim about accuracy.
- **No batch mode, tests, or CI.** One image per invocation; real field work is many bags × dates.
- **No per-oyster QC columns** — the Notes column is written empty, so nothing flags which rows a
  student should re-check by hand.
- **Unstable oyster IDs.** Reading-order numbering buckets by `cy // 80`, so a small shift can
  renumber everything and break per-oyster comparison against ImageJ numbering.
- **ROADMAP.md is a snapshot** from 2026-07-27 at commit `9188d52`. Its "current state" section
  predates the calibration fix, the measurement change, and the web app, so read it for the
  milestones rather than the assessment.

### Photo protocol

Accuracy is mostly won at capture time:

- Lay oysters flat and non-overlapping; a tilted shell reads short.
- Include a ruler or caliper **in the same focal plane** as the oysters.
- Shoot straight down, consistent height, diffuse light, no hard shadows.
- Name files `YYYYMMDD_bag<NNN>_raw.jpeg` — the date and tag ID are parsed from the filename, and
  default to 0 if the pattern does not match.

---

## Security

**Never commit private keys, tokens, or credentials.** A private SSH key was previously committed to
this repo. The file has been deleted from the working tree, but **it has not been purged from git
history** and remains reachable in commit `0876578` on `main`, `Week_1`, and
`oyster_metabolic_pathway`. Treat that key as compromised and revoke it at GitHub if that has not
already been done — deleting the file does not neutralize the exposure. `.gitignore` now blocks the
common credential filenames, but it is not a substitute for checking `git status` before you commit.

---

## Layout

```
app.py                            Streamlit web app
USER_MANUAL.md                    non-programmer guide to the web app
ROADMAP.md                        assessment and development milestones
requirements.txt                  full environment (CLI + app + training)
requirements-app.txt              slim subset for Streamlit Cloud
environment.yml                   conda alternative
.claude/skills/oyster_measurer/
    measure_oysters.py            CLI pipeline
    train_oyster_model.py         YOLOv8 training pipeline
    oyster_model.pt               current weights (= v3); v1, v2 kept for comparison
    skill.md                      skill orchestrator
    skill_*.md                    one sub-skill per pipeline stage
oyster_test/                      test image + ImageJ annotations + hand-measured ground truth
```
