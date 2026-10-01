import tempfile
import unittest
from pathlib import Path
from core import config, output, spec_latex

ROOT = Path(__file__).resolve().parents[1]


class StampTitleTests(unittest.TestCase):
    def setUp(self):
        config.SETTINGS.clear()
        config.load(str(ROOT / 'altidoc.conf'))
        config.set('output', 'template_path', str(ROOT / 'template'))
        self.stamp = dict(type='Перечень элементов', number='ЛАБФ.464974.001 ПЭ3',
                          title='', company='ООО "СейсмикЛаб"', developer='Новиков',
                          verifier='Романов', inspector='Майков', approver='Козырев', first_usage='')

    def export(self, title, doc_type='Перечень элементов'):
        stamp = dict(self.stamp, title=title, type=doc_type)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'document.tex'
            output.latex([], stamp, str(path))
            return path.read_text()

    def test_literal_and_actual_newlines_are_equivalent_in_element_list_title(self):
        literal = self.export(r'Устройство\nинициирования')
        actual = self.export('Устройство\nинициирования')
        title = r'Устройство\\инициирования'
        self.assertIn(title, literal)
        self.assertIn(title, actual)
        self.assertNotIn(r'Устройство\nинициирования', literal)

    def test_manual_breaks_are_supported_in_specification_too(self):
        tex = self.export(r'Устройство\nинициирования', '')
        self.assertIn(r'Устройство\\инициирования', tex)
        self.assertNotIn(r'\textbackslash{}n', tex)

    def test_title_punctuation_is_escaped_while_line_breaks_remain_active(self):
        tex = self.export(r'Устройство & проверка 50%\n"Модель_A"')
        self.assertIn(r'Устройство \& проверка 50\%\\\textquotedbl{}Модель\_A\textquotedbl{}', tex)
        self.assertEqual(spec_latex.normalize_line_breaks('A\r\nB\rC'), 'A\nB\nC')


if __name__ == '__main__':
    unittest.main()
