# Agentic AI — Summer 2026

Agentic AI tooling for Pacific oyster (*Magallana gigas* / *Crassostrea gigas*) research. The repo
holds two related lines of work:

1. **Oyster measurement** — a computer-vision pipeline that measures individual oyster length and
   width in millimetres from overhead field photographs.
2. **Biochemical pathway analysis** — Claude Code skills that map environmental stressors to KEGG
   pathways and construct experimental designs around them.

Both are packaged as [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills) so they
can be invoked conversationally, but the measurement pipeline also runs as a plain CLI script.

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

## 1. Oyster measurement

Measures each oyster in an overhead photo and writes a workbook matching the lab's data format.

```bash
python3 .claude/skills/oyster_measurer/measure_oysters.py oyster_test/20260522_bag380_raw.jpeg results/ "Goose Point" AH
```

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

## 2. Biochemical pathway skills

In `Claude_Code_Folder/Skills/`:

| Skill | Purpose |
|---|---|
| `oyster_stress_pathway.md` | Maps an environmental stressor (heat, hypoxia, cadmium, low salinity, pathogens…) to the relevant KEGG pathways and interprets the physiological response |
| `oyster_design_experiment.md` | Takes a desired oyster trait and constructs an experimental design grounded in KEGG pathway logic |

Both query the live [KEGG REST API](https://rest.kegg.jp/) for *C. gigas* (`crg`) pathways.

> **Note:** these files are not in `.claude/skills/`, so Claude Code does not currently auto-load
> them as skills. Relocating them is roadmap M6.

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
Claude_Code_Folder/Skills/        KEGG pathway skills
oyster_test/                      test image + hand-measured ground truth
ROADMAP.md                        assessment and development milestones
```
