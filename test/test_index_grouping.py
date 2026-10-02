import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from core import config, index, schematic, spec

ROOT = Path(__file__).resolve().parents[1]


def element_entries(table):
    entries = []
    for row in table:
        if row[-1] == 'title' or not row[0]:
            continue
        refs = schematic.expand_references(row[0])
        if row[1]:
            entries.append([row[1], int(row[2]), refs])
        else:
            entries[-1][2].extend(refs)
    return entries


class ElementListGroupingTests(unittest.TestCase):
    def setUp(self):
        config.SETTINGS.clear()
        config.load(str(ROOT / 'altidoc.conf'))

    def build_tables(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bom.csv'
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['Designator', 'Comment'])
                writer.writerow([])
                writer.writerows(rows)
            return index.build(str(path))[0], spec.build(str(path))

    def test_grouped_csv_rows_preserve_all_four_designators_and_quantity(self):
        table, specification = self.build_tables([
            ['C22, C26', 'LKT0805B106K500R'],
            ['C23, C27', 'OTHER'],
            ['C31, C34', 'LKT0805B106K500R'],
        ])
        entry = next(r for r in element_entries(table) if r[0] == 'LKT0805B106K500R')
        self.assertEqual(entry[1:], [4, ['C22', 'C26', 'C31', 'C34']])
        row = next(r for r in specification if r[3] == entry[0])
        self.assertEqual(int(row[5]), entry[1])
        self.assertCountEqual(schematic.expand_references(row[6]), entry[2])
        first = next(i for i, r in enumerate(table) if r[1] == entry[0])
        self.assertEqual(table[first][0:3], ['C22, C26, C31', entry[0], '4'])
        self.assertEqual(table[first + 1][0:3], ['C34', '', ''])

    def test_interleaved_ranges_are_sorted_and_counted(self):
        table, _ = self.build_tables([['R1, R7-R9', 'RES'], ['R2-R4', 'RES']])
        entry = element_entries(table)[0]
        self.assertEqual(entry[1], 7)
        self.assertEqual(entry[2], ['R1', 'R2', 'R3', 'R4', 'R7', 'R8', 'R9'])

    def test_same_name_with_different_reference_types_does_not_drop_components(self):
        config.set('fields', 'type', 'MissingType')
        table, _ = self.build_tables([['C1, C2', 'SAME'], ['R1, R2', 'SAME']])
        self.assertCountEqual([ref for entry in element_entries(table) for ref in entry[2]],
                             ['C1', 'C2', 'R1', 'R2'])

    def test_every_designator_and_quantity_in_grouped_fixture_reaches_element_list(self):
        fixture = ROOT / 'test' / 'fixtures' / 'spec-grouped.csv'
        with fixture.open(newline='') as stream:
            source = list(csv.DictReader(stream))
        entries = element_entries(index.build(str(fixture))[0])
        actual = Counter(ref for entry in entries for ref in entry[2])
        expected = Counter(ref for row in source for ref in
                           schematic.expand_references(row['Designator']))
        self.assertEqual(actual, expected)
        self.assertEqual(sum(entry[1] for entry in entries), sum(int(r['Quantity']) for r in source))
        for _, quantity, refs in entries:
            self.assertEqual(quantity, len(refs))


if __name__ == '__main__':
    unittest.main()
