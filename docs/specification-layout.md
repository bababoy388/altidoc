# PDF/LaTeX specification layout

Specification export uses `core/spec_latex.py` and `template/specification.tex`.
Other document types retain `template/template.tex`.

The form follows GOST R 2.106-2019, Amendment 1, Appendix A (forms 1/1a),
and GOST R 2.104-2023, Appendix B (title blocks 2/2a).

- A4 portrait; frame at x=20/205 mm and y=5/292 mm.
- Graph widths: 6, 6, 8, 70, 63, 10, 22 mm; total 185 mm.
- Header height: 15 mm. Physical rows: 8 mm (last subsequent-sheet row: 9 mm).
- First sheet: 29 rows above the 40 mm title block.
- Subsequent sheets: 32 rows above the 15 mm title block.
- Main lines: 0.5 mm; thin lines: 0.25 mm.
- Bundled GOST_A font: 10.5 pt, approximately 2.5 mm capital height, with 0.15 slant.
- Document number, product title and organization: 18 pt italic, matching the element list.
- Additional graphs 19–23: 5/7 mm wide; heights 25/35/25/25/35 mm.
- Graph 25 is printed when first-usage data is provided. Revision graphs remain empty.

Notes list at most three actual designators per physical row; ranges are expanded.
Very long designators may require fewer than three. Position and total quantity
are written once; continuation rows hold only the remaining text. Text is wrapped
using bundled TrueType font advances, with allowance for LaTeX math glyphs.
Headings stay with their following entries when the group fits a sheet.

In sections “Прочие изделия”, “Стандартные изделия”, and “Материалы”, purchasing
marks are combined with the name in the export, rather than placed in the
“Обозначение” graph (4.2.17). UI data and other export formats are preserved.

This controls presentation. It does not validate BOM quantities, procurement
references, section classification, drawing identifiers or signatures.
Specification grouping compares the purchasing mark as well as the name, type,
document and comment. Grouped CSV designators are expanded before counting,
so L1/L2/L3 has quantity 3, and different component marks remain separate positions.

Sources:
- https://protect.gost.ru/gost/details/a65c2b20-2cfb-4326-abd5-3aad62db747c
- https://meganorm.ru/Data/708/70838.pdf (2024 edition with Amendment 1)
- https://files.stroyinf.ru/Data/816/81679.pdf

Validation: `python3 -m unittest discover -s test -p 'test_spec*.py'`.
The grouped-CSV regression fixture checks every mark, designator and quantity
against the full generated specification, including 9 capacitor and 5 resistor positions.
The reference two-sheet specification and a six-sheet stress sample were compiled
with LuaLaTeX, rendered for visual review, and checked for graph coordinates and
text staying within ruled rows/columns. The element-list export was also compiled.

PDF title line breaks: enter the literal `\n` in the UI “Наименование” field,
for example `Устройство\nинициирования`. Actual line breaks from CSV metadata
are accepted too. Both the specification and element-list export support this.
The element-list title block wraps automatically to its graph width; exceptionally
long title blocks are reduced to fit the available height.

Title regressions: `python3 -m unittest discover -s test -p "test_stamp_title.py"`.
Automatic, explicit and long-title element lists were compiled with LuaLaTeX.

The element list and specification share grouped-designator expansion. CSV rows
with lists or ranges are expanded before combining groups or calculating quantities.
Reference type is part of the element-list grouping key; all individual designators
are sorted before rendering ranges and continuation rows. The regression for
`C22, C26` plus `C31, C34` requires all four designators and quantity 4.
The complete RFID CSV was checked against both exports: 105 components, including
31 capacitors, with no missing or extra designators.

Purchasing-mark priority is shared by the specification and element list:
`Part Number` → `PartNumber` → `Comment`. Missing columns, blank/whitespace values
and Altium’s `~` placeholder fall through to the next field. The default
specification `number = Comment` mapping resolves this selected mark, which is
rendered in the PDF Name graph; a separately configured designation and filled
descriptive name are preserved. Grouping uses the selected mark too, so different
part numbers with the same Comment remain separate.
Validation includes fallback cases, grouping, PDF Name cells and the full RFID CSV
(105 components with matching selected marks in both tables).
