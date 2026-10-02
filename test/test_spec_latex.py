import copy
import tempfile
import unittest
from pathlib import Path
from core import config, output, spec_latex as spec

FONT = Path(__file__).resolve().parents[1] / 'template' / 'GOST_A.TTF'

class SpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = spec.FontMetrics(FONT)

    def test_actual_designators_in_ranges_are_split_into_ruled_rows(self):
        self.assertEqual(spec.note_lines('C1, C2, C4, C5, C9-C12, C17', self.metrics),
                         ['C1, C2, C4', 'C5, C9, C10', 'C11, C12, C17'])

    def test_long_designators_use_fewer_than_three_when_needed(self):
        lines = spec.note_lines('C1234, C1235, C1236, C1237', self.metrics)
        self.assertEqual(', '.join(lines), 'C1234, C1235, C1236, C1237')
        self.assertTrue(all(self.metrics.width(line) <= 19.4 for line in lines))

    def test_adjustment_marks_and_prose_are_preserved(self):
        lines = spec.note_lines('R1*-R5*, Формовать выводы', self.metrics)
        self.assertEqual(lines[:2], ['R1*, R2*, R3*', 'R4*, R5*'])
        self.assertEqual(' '.join(lines[2:]), 'Формовать выводы')
        self.assertEqual(' '.join(spec.note_lines('Установить по чертежу', self.metrics)), 'Установить по чертежу')

    def test_continuations_do_not_repeat_position_and_total(self):
        table = [['', '', '3', 'CC0805KRX7R9BB104', '', '9', 'C1, C2, C4, C5, C9-C12, C17', '']]
        original = copy.deepcopy(table)
        rows = spec.row_blocks(table, self.metrics)[0]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0][2:6], ['3', 'CC0805KRX7R9BB104', '', '9'])
        self.assertTrue(all(not any(cells[:6]) for cells, _ in rows[1:]))
        self.assertEqual(table, original)

    def test_purchased_parts_move_to_name_and_documents_keep_designations(self):
        table = [['', '', '', '', 'Документация', '', '', 'section_title'],
                 ['А3', '', '', 'ЛАБФ.001 Э3', 'Схема', '', '', ''],
                 ['', '', '', '', 'Прочие изделия', '', '', 'section_title'],
                 ['', '', '1', 'STM32L452CCU6', 'Микросхема', '1', 'DD1', '']]
        original = copy.deepcopy(table)
        blocks = spec.row_blocks(table, self.metrics)
        self.assertEqual(blocks[1][0][0][3], 'ЛАБФ.001 Э3')
        self.assertEqual(blocks[3][0][0][3:5], ['', 'STM32L452CCU6 Микросхема'])
        self.assertEqual(table, original)

    def test_long_part_numbers_are_not_changed_or_lost(self):
        number = 'ABCDEFGHIJ1234567890-' * 8
        lines = self.metrics.wrap(number, 60.2)
        self.assertEqual(''.join(lines), number)
        self.assertTrue(all(self.metrics.width(line) <= 60.2 for line in lines))

    def test_heading_and_following_entry_move_together(self):
        blank = [([''] * 7, '')]
        heading = [(['', '', '', '', 'Конденсаторы', '', ''], 'title')]
        component = [(['', '', '1', 'A', '', '4', 'C1, C2, C3'], ''), (['', '', '', '', '', '', 'C4'], '')]
        pages = spec.paginate([blank for _ in range(27)] + [heading, blank, component])
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(pages[0]), 27)
        self.assertEqual(pages[1][0][1], 'title')
        self.assertEqual(pages[1][2][0][2], '1')

    def test_page_capacity_and_no_trailing_empty_sheet(self):
        entry = [(['', '', str(n), 'PART', '', '1', 'R1'], '') for n in range(80)]
        pages = spec.paginate([[row] for row in entry])
        self.assertEqual([len(page) for page in pages], [29, 32, 19])
        pages = spec.paginate([[row] for row in entry[:61]] + [[([''] * 7, '')]])
        self.assertEqual(len(pages), 2)
        self.assertEqual(sum(bool(any(cells)) for page in pages for cells, _ in page), 61)

    def test_math_symbols_have_room_for_the_latex_math_font(self):
        self.assertGreater(self.metrics.width('±'), 3.0)
        text = 'TEST_1 Изделие \"Пример\" & проверка 50% ± 5 × 10'
        lines = self.metrics.wrap(text, 60.2)
        self.assertNotIn('± 5', lines[0])
        self.assertEqual(' '.join(lines), text)

    def test_tex_metacharacters_are_safe(self):
        self.assertEqual(spec.escape('"СейсмикЛаб" & 50%'), r'\textquotedbl{}СейсмикЛаб\textquotedbl{} \& 50\%')
        self.assertEqual(spec.escape('A_B{C}\\'), r'A\_B\{C\}\textbackslash{}')

    def test_export_selects_new_spec_template_without_mutating_table(self):
        config.load(str(FONT.parents[1] / 'altidoc.conf'))
        config.SETTINGS.set('output', 'template_path', str(FONT.parent))
        stamp = dict(type='', number='ЛАБФ.464211.001', title='Изделие', company='ООО "Лаб"',
                     developer='Новиков', verifier='', inspector='', approver='', first_usage='')
        table = [['', '', '1', 'PART', '', '4', 'C1-C4', '']]
        original = copy.deepcopy(table)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'spec.tex'
            output.latex(table, stamp, str(path))
            tex = path.read_text()
            self.assertIn(r'\SpecPage{1}{29}', tex)
            self.assertNotIn(r'\begin{longtable}', tex)
            self.assertIn('C1, C2, C3', tex)
            self.assertIn('C4', tex)
            self.assertNotIn('${', tex)
        self.assertEqual(table, original)

if __name__ == '__main__':
    unittest.main()
