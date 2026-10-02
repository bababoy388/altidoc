import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from core import config, schematic, spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'test' / 'fixtures' / 'spec-grouped.csv'


class SpecificationGroupingTests(unittest.TestCase):
    def setUp(self):
        config.SETTINGS.clear()
        config.load(str(ROOT / 'altidoc.conf'))

    def component(self, refs, number, fitted=True):
        component = schematic.Component(None)
        component.reference = refs
        component.fields = {'Comment': number}
        component.fitted = fitted
        return component

    def test_different_marks_are_not_merged_when_names_are_empty(self):
        group = schematic.CompRangeSpec(None, self.component('C1, C3', 'CAP_A'))
        self.assertFalse(group.append(self.component('C2', 'CAP_B')))
        self.assertEqual(list(group), ['C1', 'C3'])
        self.assertEqual(group.lenFitted(), 2)

    def test_identical_marks_merge_and_count_every_designator(self):
        group = schematic.CompRangeSpec(None, self.component('R1, R3', 'RES_A'))
        self.assertTrue(group.append(self.component('R5-R7', 'RES_A')))
        self.assertEqual(group.lenFitted(), 5)
        self.assertEqual(set(group), {'R1', 'R3', 'R5', 'R6', 'R7'})

    def test_not_fitted_references_are_excluded_from_quantity_and_notes(self):
        group = schematic.CompRangeSpec(None, self.component('R1, R2', 'RES_A'))
        self.assertTrue(group.append(self.component('R3, R4', 'RES_A', fitted=False)))
        self.assertEqual(len(group), 4)
        self.assertEqual(group.lenFitted(), 2)
        self.assertEqual(group.getRefRangeFittedString(), 'R1, R2')

    def test_range_and_single_reference_inputs(self):
        self.assertEqual(schematic.CompRangeSpec._expand_references('C3-C1, C5–7; C9'),
                         ['C1', 'C2', 'C3', 'C5', 'C6', 'C7', 'C9'])
        group = schematic.CompRangeSpec(None, self.component('DD1', 'IC'))
        self.assertEqual(group.getRefRangeFittedString(), 'DD1')
        self.assertEqual(group.lenFitted(), 1)

    def test_nonadjacent_identical_marks_merge_in_complete_specification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bom.csv'
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['Designator', 'Comment'])
                writer.writerow([])
                writer.writerows([['R1', 'RES_A'], ['R2', 'RES_B'], ['R3', 'RES_A']])
            table = spec.build(str(path))
        parts = [row for row in table if row[3] in ('RES_A', 'RES_B')]
        self.assertEqual(len(parts), 2)
        a = next(row for row in parts if row[3] == 'RES_A')
        self.assertEqual(a[5:7], ['2', 'R1, R3'])

    def test_every_source_mark_reference_and_quantity_reaches_specification(self):
        with FIXTURE.open(newline='') as stream:
            source = list(csv.DictReader(stream))
        table = spec.build(str(FIXTURE))
        parts = [row for row in table if row[2] and row[3] in {p['Comment'] for p in source}]
        self.assertEqual(len(parts), len(source))
        by_mark = {row[3]: row for row in parts}
        source_refs, output_refs = [], []
        for component in source:
            refs = [ref.strip() for ref in component['Designator'].split(',')]
            result = by_mark[component['Comment']]
            self.assertEqual(int(result[5]), int(component['Quantity']))
            actual = schematic.CompRangeSpec._expand_references(result[6])
            self.assertCountEqual(actual, refs)
            source_refs.extend(refs)
            output_refs.extend(actual)
        self.assertEqual(Counter(output_refs), Counter(source_refs))
        self.assertEqual(len([r for r in parts if r[6].startswith('C')]), 9)
        self.assertEqual(len([r for r in parts if r[6].startswith('R')]), 5)


if __name__ == '__main__':
    unittest.main()
