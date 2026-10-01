import csv
import tempfile
import unittest
from pathlib import Path
from core import config, index, schematic, spec, spec_latex

ROOT = Path(__file__).resolve().parents[1]


class PartNumberPriorityTests(unittest.TestCase):
    def setUp(self):
        config.SETTINGS.clear()
        config.load(str(ROOT / 'altidoc.conf'))

    def component(self, fields):
        component = schematic.Component(None)
        component.reference = 'C1'
        component.fields = fields
        return component

    def tables(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bom.csv'
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['Designator', 'Comment', 'PartNumber', 'Part Number', 'name'])
                writer.writeheader()
                stream.write('\n')
                writer.writerows(rows)
            return index.build(str(path))[0], spec.build(str(path))

    def test_missing_blank_and_whitespace_fields_follow_priority(self):
        cases = [
            ({'Part Number': 'FIRST', 'PartNumber': 'SECOND', 'Comment': 'THIRD'}, 'FIRST'),
            ({'Part Number': '', 'PartNumber': 'SECOND', 'Comment': 'THIRD'}, 'SECOND'),
            ({'PartNumber': 'SECOND', 'Comment': 'THIRD'}, 'SECOND'),
            ({'Part Number': ' \t ', 'PartNumber': ' SECOND ', 'Comment': 'THIRD'}, 'SECOND'),
            ({'Part Number': '~', 'PartNumber': 'SECOND', 'Comment': 'THIRD'}, 'SECOND'),
            ({'Part Number': '', 'PartNumber': '', 'Comment': 'THIRD'}, 'THIRD'),
            ({'Comment': 'THIRD'}, 'THIRD'),
            ({'PartNumber': ' ', 'Comment': ''}, ''),
            ({}, ''),
        ]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                component = self.component(fields)
                self.assertEqual(component.getIndexValue('name'), expected)
                self.assertEqual(component.getSpecValue('number'), expected)

    def test_different_parts_with_identical_comments_remain_separate(self):
        table, specification = self.tables([
            dict(Designator='C1, C2', Comment='GENERIC', PartNumber='SECOND', **{'Part Number': 'FIRST'}),
            dict(Designator='C3', Comment='GENERIC', PartNumber='OTHER'),
            dict(Designator='C4', Comment='GENERIC'),
        ])
        parts = [row for row in specification if row[2] and row[6]]
        self.assertEqual([(r[3], r[5], r[6]) for r in parts],
                         [('FIRST', '2', 'C1, C2'), ('OTHER', '1', 'C3'), ('GENERIC', '1', 'C4')])
        self.assertEqual([(r[1], r[2]) for r in table if r[0] and r[1]],
                         [('FIRST', '2'), ('OTHER', '1'), ('GENERIC', '1')])

    def test_equal_selected_parts_merge_despite_different_comments(self):
        _, table = self.tables([
            dict(Designator='C1', Comment='OLD_A', **{'Part Number': 'SAME'}),
            dict(Designator='C2', Comment='OLD_B', PartNumber='SAME'),
        ])
        parts = [r for r in table if r[2] and r[6]]
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0][3:7], ['SAME', '', '2', 'C1, C2'])

    def test_pdf_name_uses_selected_mark_and_preserves_descriptive_name(self):
        _, table = self.tables([
            dict(Designator='C1', Comment='OLD', name='Description', **{'Part Number': 'SELECTED'}),
        ])
        metrics = spec_latex.FontMetrics(ROOT / 'template' / 'GOST_A.TTF')
        cells = [cells for block in spec_latex.row_blocks(table, metrics) for cells, _ in block
                 if cells[6] == 'C1'][0]
        self.assertEqual(cells[3:5], ['', 'SELECTED Description'])
        self.assertNotIn('OLD', cells)

    def test_custom_designation_mapping_is_preserved(self):
        config.set('fields_spec', 'number', 'Drawing')
        component = self.component({'Drawing': 'DOC.001', 'Part Number': 'PART', 'Comment': 'OLD'})
        self.assertEqual(component.getSpecValue('number'), 'DOC.001')


if __name__ == '__main__':
    unittest.main()
