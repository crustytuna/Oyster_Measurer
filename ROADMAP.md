# Oyster Measurement Repo — Evaluation & Development Roadmap

_Assessment date: 2026-07-27 · commit `9188d52`_

---

## Part 1 — Current state

### What exists

| Component | Location | Status |
|---|---|---|
| Measurement script | `.claude/skills/oyster_measurer/measure_oysters.py` | Works on one image; heavily tuned to it |
| Skill definition | `.claude/skills/oyster_measurer/skill.md` | Out of sync with the script |
| Trained YOLOv8n-seg model | `.claude/skills/oyster_measurer/oyster_model.pt` | 6.8 MB, no provenance |
| Test image + ground truth | `oyster_test/` | 1 image, 84 manually measured oysters |

The pipeline is sound in outline: ruler calibration → segmentation (YOLO / blue mask / adaptive threshold)
→ PCA major/minor axis → xlsx export matching the lab's format → 6-panel diagnostic figure. The
three-tier segmentation fallback and the human-in-the-loop blue-mask mode are good design choices.

### Blocking issues

**B1 — A private SSH key is committed.** `Documents` is an OpenSSH private key,
`Documents.pub` its public half (`ChristinaR270225@gmail.com`), pushed to a GitHub remote in commit
`0876578`. Must be revoked and purged before any other work.

**B2 — Calibration is hardcoded and unverified.** `MANUAL_PX_PER_MM = 2.15` at
`measure_oysters.py:43` is a module-level constant that unconditionally overrides
`calibrate_ruler()` for *every* image (`measure_oysters.py:640`). Every new photo silently inherits
bag 380's scale, so every measurement on a new photo is wrong by the ratio of the two scales, with
no warning. `RULER_ROI_FRAC = (0.818, 0.52, 0.836, 0.64)` is likewise pixel-tuned to that one photo.
The underlying reason the override exists: `calibrate_ruler()` assumes each detected graduation is
`RULER_KNOWN_MM = 10` apart, but peak detection on a real ruler finds 1 mm ticks — a systematic 10×
error. Fix the root cause, then delete the override.

**B3 — No accuracy measurement.** `oyster_test/20260522_bag380_data.xlsx` contains 84 hand-measured
oysters (lengths ~78–105 mm) — a genuine ground-truth set that nothing in the repo compares against.
Until there is a number for "how close is this to the human measurement," every change to thresholds
or models is a guess.

> A smoke run on 2026-07-27 detected **91** oysters against the ground truth's 84, with lengths
> ranging past **128 mm** where the manual maximum is 105 mm. So the current pipeline is both
> over-detecting and over-measuring on the one image it was tuned for. Whether that is calibration
> (B2), PCA span overestimating on irregular shells, or model false positives is exactly what M2
> exists to disentangle — the numbers above are not yet a diagnosis.

### Significant issues

- **Docs drift.** `skill.md` documents 4 CLI args (the script takes 5), `MIN_OYSTER_PX` 800 /
  `MAX_OYSTER_PX` 120000 (actual: 2000 / 500000), a different `RULER_ROI_FRAC`, and never mentions
  the YOLO model or `MANUAL_PX_PER_MM` at all.
- **Silent degradation.** `_get_yolo_model()` catches every exception and marks the model
  unavailable (`measure_oysters.py:162-170`); a missing `ultralytics` install quietly downgrades to
  the much weaker adaptive-threshold path. The user sees a line of stdout, not a failure.
- **No dependency spec.** No `requirements.txt` / `environment.yml`. `skill.md`'s pip line omits
  `ultralytics`, `torch`, and `numpy`. None of the deps are installed in the current environment.
- **Model has no provenance.** No training script, dataset, label set, hyperparameters, or held-out
  metrics. It can't be retrained, audited, or improved — and a `.pt` is executable pickle data.
- **Unstable oyster IDs.** Reading-order sort uses `cy // 80` row buckets
  (`measure_oysters.py:212`); a small shift moves an oyster between buckets and renumbers everything
  downstream, which also makes per-oyster comparison against ImageJ numbering unreliable.
- **Repo hygiene.** 156 MB with 30–36 MB PNG/TIFF committed directly; no `.gitattributes`/LFS, no
  `.gitignore`, no LICENSE. Default output goes to `~/Desktop` (`measure_oysters.py:623`).
- **No batch mode, no tests, no CI.** Real field work is many bags × many dates.
- **No QC signal in the output.** No per-oyster confidence, area, edge-touching flag, or
  aspect-ratio outlier flag — nothing to tell a student which of 84 rows to check by hand.

---

## Part 2 — Milestones

### M0 — Secure and stabilize the repo — **mostly done** _(2026-07-27)_

- [x] Delete `Documents` and `Documents.pub` from the working tree and index.
- [x] `.gitignore` — credentials, Python scratch, pipeline outputs, training runs, macOS cruft.
- [x] `.gitattributes` — line-ending normalization and binary markers.
- [x] `requirements.txt` + `environment.yml`; verified installing clean into a fresh venv
      (torch 2.8.0, ultralytics 8.4.107, numpy 1.26.4 on Python 3.9) and running the pipeline
      end-to-end on bag 380.
- [x] MIT LICENSE.
- [x] README rewritten to cover the measurement pipeline, with setup, photo protocol, and the calibration caveat.
- [ ] **Revoke the leaked SSH key at GitHub** — owner action, not yet confirmed. This is what
      actually neutralizes the exposure; the file deletion does not.
- [ ] **Purge the key from history** — deferred by decision. The key remains reachable in commit
      `0876578` on `main`, `Week_1`, and `oyster_metabolic_pathway`. Requires
      `pip install git-filter-repo`, a rewrite, and a coordinated force-push.
- [ ] **Git LFS** — deferred. `git-lfs` is not installed on the dev machine, and enabling the filters
      in `.gitattributes` before every collaborator has it installed breaks their checkouts. The LFS
      block is present but commented out with instructions. Revisit when the image set grows (M3).

Done when: the key is revoked and purged, and `pip install -r requirements.txt` reproduces a working
environment from a clean machine (second half: confirmed).

### M1 — Trustworthy calibration _(~1–2 days)_

Key features:
- Rewrite `calibrate_ruler()` to detect the tick *period* rather than assume a 10 mm interval:
  find the fundamental spacing (FFT or autocorrelation of the tick projection), classify minor vs.
  major ticks by peak prominence, and derive px/mm from the minor-tick period.
- Auto-locate the ruler instead of a hardcoded ROI — either a detected high-frequency periodic
  region, or a printed ArUco/April fiducial of known size placed in-frame (strongly recommended for
  new field photos: robust, cheap, and eliminates ROI tuning entirely).
- Demote `MANUAL_PX_PER_MM` to an opt-in `--px-per-mm` CLI flag; hard-fail (not warn) when
  auto-calibration fails and no override is given.
- Plausibility gate: reject a calibration implying an unreasonable field of view or median oyster
  size outside 20–200 mm.

Done when: bag 380 calibrates automatically to within 2% of the value implied by ground truth, and a
deliberately mis-cropped ruler produces an error rather than a wrong number.

### M2 — Validation harness _(~2 days; the highest-leverage milestone)_

Key features:
- `validate.py`: run the pipeline on an image, match predictions to ground-truth oysters by centroid
  (Hungarian assignment, not index order), and report per-image **MAE / bias / 95% limits of
  agreement** for length and width, plus detection precision/recall and count error.
- Bland–Altman and predicted-vs-manual scatter plots written alongside the diagnostic figure.
- `tests/` with pytest: unit tests for `measure_oyster()` on synthetic ellipses of known size and
  angle, `export_xlsx()` schema conformance against the reference workbook, and a regression test
  asserting bag 380 MAE stays under an agreed threshold.
- GitHub Actions running the tests on push.

Done when: `python validate.py oyster_test/20260522_bag380_raw.jpeg` prints an accuracy table, and
CI fails if a change makes bag 380 worse.

### M3 — Reproducible model _(~3–5 days)_

Key features:
- `training/` with dataset prep (ImageJ ROI / mask → YOLO-seg labels), `train.py`, config, and a
  MODEL_CARD.md recording dataset size, split, hyperparameters, and held-out metrics.
- Expand the labeled set beyond one bag: target ≥20 images spanning sites, dates, lighting, and
  wet/dry shells; hold out whole images (never oysters within an image) for the test split.
- Publish the weights as a GitHub Release asset with a SHA-256 checksum and download-on-first-use,
  rather than a blob in the tree.
- Make the fallback chain loud: log which segmentation tier ran, and let `--strict` turn a fallback
  into an error.

Done when: `python training/train.py` reproduces a model matching the published metrics, and M2's
harness shows it beats the current weights on held-out images.

### M4 — Field-usable tool _(~3–4 days)_

Key features:
- Batch mode: `measure_oysters.py <dir> --out results/` over a folder, with a combined workbook, a
  tidy long-format CSV (one row per measurement) for downstream stats, and a per-run manifest
  recording input hash, model version, calibration, and git commit.
- Per-oyster QC columns: detection confidence, contour area, solidity, aspect ratio, touches-frame-
  edge flag, and an `outlier` flag from a robust z-score — so a student reviews 5 rows, not 84.
- Structured metadata: parse or accept `--site`, `--date`, `--tag`, `--initials`; stop inferring
  everything from filenames, but keep filename parsing as the default.
- Replace positional CLI args with `argparse`, and move tuning constants into a YAML config so
  per-site profiles are versioned rather than edited in place.
- Convex-hull or min-area-rect option alongside PCA span, since PCA span overestimates on irregular
  shells — report both and pick per validation results.

Done when: a full field day of photos is processed with one command and produces an analysis-ready
CSV plus a QC review list.

### M5 — Correction loop and reporting _(~3–5 days)_

Key features:
- Review UI: an HTML or notebook view of the annotated image where a user confirms, edits, or
  deletes each detection; corrections write back to the workbook *and* accumulate as new training
  labels — closing the loop from M4 into M3.
- Growth analysis: join measurements across dates by tag ID; per-bag growth curves, size-frequency
  distributions, and site comparisons.
- Optional: a shell-area / estimated-biomass metric from contour area, calibrated against a weighed
  subsample.

Done when: a corrected measurement session feeds directly back into the training set with no manual
file shuffling.

### M6 — Repo as a teaching artifact _(~2 days, ongoing)_

Key features:
- Put library code in `src/oyster_measure/` with the skill as a thin wrapper.
- A worked tutorial notebook: raw photo → calibration → segmentation → measurement → validation, with
  the bag 380 data.
- CONTRIBUTING.md covering the photo protocol (flat oysters, ruler in the focal plane, fiducial
  marker, consistent height, no shadows) — most accuracy is won at capture time, not in code.
- CHANGELOG and semantic version tags so a published measurement can cite the exact tool version.

---

## Recommended order

M0 → M2 → M1 → M3 → M4 → M5 → M6.

M2 before M1 is deliberate: build the ruler that measures accuracy before changing the thing whose
accuracy you are trying to improve. M0 is not optional and not sequenceable — it happens today.
