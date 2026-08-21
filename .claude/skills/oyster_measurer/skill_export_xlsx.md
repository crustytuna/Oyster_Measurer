# Skill: Export Oyster Measurements to XLSX

Writes the oyster measurements to an Excel workbook matching the lab's data format — two rows per oyster, one for length and one for width.

---

## TRIGGER

Activate this sub-skill when:
- Oyster measurements are ready to be saved
- The user asks where the output file is, or why a previous output looks wrong
- The user wants to understand the column layout or add/change columns

---

## WHAT THIS DOES IN THE CODE

Two separate `openpyxl` writers exist, and they produce **different** workbooks:

| Writer | Called by | Output |
|---|---|---|
| `export_xlsx()` in `measure_oysters.py` | the CLI / this skill | one sheet, one image per file |
| `_write_sheet()` in `app.py` | the Streamlit app | one sheet per uploaded image, combined into one file |

Everything below describes `export_xlsx()` unless stated otherwise.

---

## OUTPUT FILE

**Location:** `<output_dir>/<stem>_measured.xlsx`, where `output_dir` defaults to `~/Desktop` and
`stem` is the image filename with `_raw` stripped — e.g. `20260522_bag380_measured.xlsx`.

Two more files are written alongside it, as separate PNGs:
`<stem>_annotated_measured.png` and `<stem>_diagnostic.png`.

Re-running on the same image **overwrites** the previous workbook — the filename carries no
timestamp. Pass a different `output_dir` to keep an old run.

---

## WORKBOOK STRUCTURE

A single sheet named `Sheet1`. There is **no Summary tab**, and no image is embedded in the sheet.

**Two rows per oyster** — one for length, one for width — in alternating fill colours:

| Column | Content |
|---|---|
| Site | Site name passed as argument (always provide the actual site; never hard-code) |
| Image Date | `YYYYMMDD` integer parsed from the filename; **0** if the filename has no 8-digit date |
| Initials | Measurer initials passed as argument |
| Image Name | Filename stem with `_raw` replaced by `_annotated` |
| Tag ID | Bag number parsed from `bag<NNN>` in the filename; **0** if absent |
| Oyster | Sequential integer (1, 2, 3 …) assigned in reading order |
| Measurement | `length` or `width ` (note the trailing space on `width `, matching the reference workbook) |
| Value mm | Float rounded to 2 decimal places |
| Notes | **Always empty** — see below |

**Style:**
- Header row: dark blue fill (`1F4E79`), white bold text
- Alternating row fill: light blue (`D9E1F2`) on even-numbered oysters
- Thin grey borders on every cell
- Column widths: pre-sized for readability

This matches the layout of the hand-measured reference workbook
`oyster_test/20260522_bag380_data.xlsx`, so the two can be compared column-for-column.

---

## THE NOTES COLUMN IS NOT POPULATED

`export_xlsx()` writes `None` into Notes for every row. There is no aspect-ratio flag, no solidity
flag, no confidence score, and no outlier detection anywhere in the pipeline.

Do not tell the user to "review the flagged rows" — nothing is flagged. QC columns are roadmap M4.
Until then the review path is visual: open `<stem>_annotated_measured.png` and check for measurement
lines that overshoot a shell or span two shells.

---

## STREAMLIT APP DIFFERENCES

`app.py`'s `_write_sheet()` writes the same nine columns, but:
- One workbook for the whole run: `oyster_measurements_<YYYYMMDD_HHMMSS>.xlsx`, delivered as a browser download
- One sheet per uploaded image, named from the filename stem (truncated to 31 characters)
- `Measurement` values are `length` / `width` with no trailing space
- Still no Summary tab, no embedded images, no Notes content

---

## DEPENDENCIES

```
pip3 install openpyxl
```

Included in the `requirements.txt` at the repo root. `Pillow` is only needed for image handling
elsewhere in the pipeline, not for this export — nothing is embedded in the workbook.

---

## AFTER THE FILE IS SAVED

Always tell the user:
1. The full path to the xlsx file, plus the annotated and diagnostic PNGs
2. Total oyster count
3. The calibration value and which method produced it
4. That Image Date / Tag ID are 0 if the filename did not match `YYYYMMDD_bag<NNN>`
5. That the numbers are unvalidated — no accuracy figure exists for this pipeline
