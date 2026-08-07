# Agentic AI — Summer 2026

Agentic AI tooling for Pacific oyster (*Magallana gigas* / *Crassostrea gigas*) research. The repo
holds a computer-vision pipeline that measures individual oyster length and width in millimetres from
overhead field photographs.

The pipeline is packaged as a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills)
so it can be invoked conversationally, and it also runs as a plain CLI script.

See [ROADMAP.md](ROADMAP.md) for the current assessment and development milestones.

---

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Conda users can substitute `conda env create -f environment.yml`.

`ultralytics` and `torch` are large but strongly recommended: without them the pipeline falls back
to adaptive thresholding, which is considerably less accurate than the trained segmentation model.

---

## Oyster measurement

Measures each oyster in an overhead photo and writes a workbook matching the lab's data format.

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py oyster_test/20260522_bag380_raw.jpeg results/ "Goose Point" AH
```

Arguments are positional: `image_path`, then optional `output_dir` (default `~/Desktop`),
`site` (default `Goose Point`), `initials` (default `CC`), and `mask_path`. Passing `mask_path` —
an image of the same oysters hand-painted solid blue — forces mask-based segmentation instead of
the model, which is the reliable escape hatch when automatic detection misses or merges oysters.

**Pipeline:** load image → calibrate px/mm from the in-frame ruler → segment individual oysters
(trained YOLOv8n-seg model, a hand-painted blue mask, or adaptive threshold + watershed) → fit PCA
axes per oyster for length (major) and width (minor) → export `.xlsx` → render a 6-panel diagnostic
figure showing every step.

**Outputs:** `<stem>_measured.xlsx`, `<stem>_annotated_measured.png`, `<stem>_diagnostic.png`.

Full argument reference and troubleshooting: [`.claude/skills/oyster_measurer/skill.md`](.claude/skills/oyster_measurer/skill.md).

### ⚠ Known limitation — calibration is currently hardcoded

`MANUAL_PX_PER_MM = 2.15` in `measure_oysters.py` overrides automatic ruler calibration for *every*
image. It was derived from `20260522_bag380_raw.jpeg`, so **measurements on any other photo are
currently wrong** unless you edit that constant to match. Automatic calibration is milestone M1 in
the roadmap. Until then, check panel ② of the diagnostic figure before trusting any output.

### Photo protocol

Accuracy is mostly won at capture time:

- Lay oysters flat and non-overlapping; a tilted shell reads short.
- Include a ruler **in the same focal plane** as the oysters.
- Shoot straight down, consistent height, diffuse light, no hard shadows.
- Name files `YYYYMMDD_bag<NNN>_raw.jpeg` — the date and tag ID are parsed from the filename.

### Test data

`oyster_test/` holds one photo of bag 380 (2026-05-22, Goose Point) plus **84 oysters measured by
hand in ImageJ** in `20260522_bag380_data.xlsx`. This is the ground truth for the validation harness
(roadmap M2).

---

## Security

**Never commit private keys, tokens, or credentials.** A private SSH key was previously committed to
this repo and has been removed; if you cloned before that cleanup, delete your clone and re-clone.
`.gitignore` now blocks the common credential filenames, but it is not a substitute for checking
`git status` before you commit.

---

## Layout

```
.claude/skills/oyster_measurer/   measurement skill: script, model weights, skill.md
oyster_test/                      test image + hand-measured ground truth
ROADMAP.md                        assessment and development milestones
```
