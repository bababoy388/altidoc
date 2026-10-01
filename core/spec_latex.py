"""Specification forms 1/1a (GOST R 2.106), with fixed physical rows."""
import re
import string
import struct
from pathlib import Path

COLUMN_WIDTHS = (6, 6, 8, 70, 63, 10, 22)
FIRST_PAGE_ROWS = 29
NEXT_PAGE_ROWS = 32
BODY_PT = 10.5  # GOST_A capital height approximately 2.5 mm.


class FontMetrics:
    """Read Unicode advances from the bundled TrueType font, without GUI dependencies."""
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        u16, u32 = self.u16, self.u32
        tables = {self.data[12 + i * 16:16 + i * 16].decode('ascii'): u32(20 + i * 16)
                  for i in range(u16(4))}
        self.units = u16(tables['head'] + 18)
        cmap = tables['cmap']
        offsets = [cmap + u32(cmap + 8 + i * 8)
                   for i in range(u16(cmap + 2))
                   if u16(cmap + 4 + i * 8) in (0, 3)]
        self.glyphs = {}
        for offset in offsets:
            if u16(offset) == 4:
                count = u16(offset + 6) // 2
                end = offset + 14
                start = end + count * 2 + 2
                delta = start + count * 2
                ranges = delta + count * 2
                for i in range(count):
                    shift = self.i16(delta + 2 * i)
                    ro = u16(ranges + 2 * i)
                    for code in range(u16(start + 2 * i), min(u16(end + 2 * i), 65534) + 1):
                        glyph = ((code + shift) & 65535) if not ro else u16(
                            ranges + 2 * i + ro + 2 * (code - u16(start + 2 * i)))
                        if ro and glyph:
                            glyph = (glyph + shift) & 65535
                        self.glyphs[code] = glyph
            elif u16(offset) == 12:
                for i in range(u32(offset + 12)):
                    first, last, glyph = struct.unpack_from('>III', self.data, offset + 16 + 12 * i)
                    self.glyphs.update((code, glyph + code - first) for code in range(first, last + 1))
        metric_count = u16(tables['hhea'] + 34)
        advances = [u16(tables['hmtx'] + 4 * i) for i in range(metric_count)]
        self.advances = advances

    def u16(self, offset):
        return struct.unpack_from('>H', self.data, offset)[0]

    def i16(self, offset):
        return struct.unpack_from('>h', self.data, offset)[0]

    def u32(self, offset):
        return struct.unpack_from('>I', self.data, offset)[0]

    def width(self, text, size=BODY_PT):
        # Math escapes use Computer Modern rather than GOST_A; reserve their full width.
        units = sum(max(self.advances[min(self.glyphs.get(ord(ch), 0), len(self.advances) - 1)],
                        self.units * 0.9 if ch in '±×' else 0) for ch in text)
        return units / self.units * size * 25.4 / 72.27

    def wrap(self, text, width, size=BODY_PT):
        """Wrap text to physical lines, preserving explicit breaks and every character."""
        result = []
        for paragraph in str(text).split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = (line + ' ' + word).strip()
                if self.width(candidate, size) <= width:
                    line = candidate
                    continue
                if line:
                    result.append(line)
                    line = ''
                while self.width(word, size) > width:
                    cut = 1
                    while cut < len(word) and self.width(word[:cut + 1], size) <= width:
                        cut += 1
                    # Prefer an existing punctuation boundary; never add hyphens to part numbers.
                    breaks = [j + 1 for j, ch in enumerate(word[:cut]) if ch in '-/']
                    cut = breaks[-1] if breaks else cut
                    result.append(word[:cut])
                    word = word[cut:]
                line = word
            result.append(line)
        return result or ['']


REF = re.compile(r'([A-Za-zА-Яа-я]+)(\d+)(\*?)(?:\s*[-–—]\s*([A-Za-zА-Яа-я]*)(\d+)(\*?))?\Z')


def note_lines(text, metrics):
    """At most three actual designators per ruled line; keep prose as prose."""
    references = []
    remainder = []
    parsing_refs = True
    for token in re.split(r',\s*|\n', str(text)):
        token = token.strip()
        match = REF.fullmatch(token) if parsing_refs else None
        if match:
            prefix, first, star, last_prefix, last, last_star = match.groups()
            if last and (not last_prefix or last_prefix == prefix) and int(last) >= int(first):
                if int(last) - int(first) > 10000:
                    raise ValueError('Слишком большой диапазон позиционных обозначений: ' + token)
                references.extend(prefix + str(n) + (star or last_star)
                                  for n in range(int(first), int(last) + 1))
            else:
                references.append(token)
        else:
            parsing_refs = False
            if token:
                remainder.append(token)
    lines, group = [], []
    for ref in references:
        if group and (len(group) == 3 or metrics.width(', '.join(group + [ref])) > 19.4):
            lines.append(', '.join(group))
            group = []
        # Unusually long designators must also fit the notes column.
        pieces = metrics.wrap(ref, 19.4)
        if len(pieces) > 1:
            if group:
                lines.append(', '.join(group))
                group = []
            lines.extend(pieces)
        else:
            group.append(ref)
    if group:
        lines.append(', '.join(group))
    if remainder:
        lines.extend(metrics.wrap(', '.join(remainder), 19.4))
    return lines or ['']


def escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
                    '"': r'\textquotedbl{}', '±': r'\ensuremath{\pm}',
                    '×': r'\ensuremath{\times}'}
    return ''.join(replacements.get(ch, ch) for ch in str(text))


def row_blocks(table, metrics):
    """Position and total quantity appear once, in the first physical line."""
    blocks = []
    section = ''
    for original in table:
        row = list(original[:7]) + [''] * max(0, 7 - len(original[:7]))
        style = original[7] if len(original) > 7 else ''
        if style == 'section_title':
            section = row[4].strip()
        if section in ('Прочие изделия', 'Стандартные изделия', 'Материалы') and row[3]:
            # These sections use the Name graph for purchasing designations (4.2.17).
            row[4] = row[3] if row[3] == row[4] else ' '.join(filter(None, (row[3], row[4])))
            row[3] = ''
        lines = [metrics.wrap(value, width - (1.2 if width <= 10 else 2.8)) for value, width in zip(row, COLUMN_WIDTHS)]
        lines[6] = note_lines(row[6], metrics)
        rows = []
        for i in range(max(map(len, lines))):
            rows.append(([column[i] if i < len(column) else '' for column in lines], style))
        blocks.append(rows)
    return blocks


def paginate(blocks):
    """Keep entries together when possible; never strand a heading at the page bottom."""
    pages, page = [], []
    capacity = FIRST_PAGE_ROWS
    for index, block in enumerate(blocks):
        needed = len(block)
        if block[0][1] in ('title', 'section_title'):
            # Reserve through consecutive headings/blank lines to the first entry.
            for following in blocks[index + 1:]:
                needed += len(following)
                if any(any(cells) for cells, _ in following) and following[0][1] not in ('title', 'section_title'):
                    break
        if page and needed <= NEXT_PAGE_ROWS and len(page) + needed > capacity:
            pages.append(page)
            page, capacity = [], NEXT_PAGE_ROWS
        for physical in block:
            if len(page) == capacity:
                pages.append(page)
                page, capacity = [], NEXT_PAGE_ROWS
            page.append(physical)
    if page or not pages:
        pages.append(page)
    # Explicit trailing blank rows must not create an otherwise empty sheet.
    while len(pages) > 1 and not any(any(cells) for cells, _ in pages[-1]):
        pages.pop()
    return pages


def write(table, stamp, output, template_dir):
    directory = Path(template_dir).resolve()
    metrics = FontMetrics(directory / 'GOST_A.TTF')
    pages = paginate(row_blocks(table, metrics))
    rendered = []
    x_positions = (20, 26, 32, 40, 110, 173, 183)
    for number, rows in enumerate(pages, 1):
        content = []
        for index, (cells, style) in enumerate(rows):
            y = 277 - 8 * index - 4
            for column, (x, width, text) in enumerate(zip(x_positions, COLUMN_WIDTHS, cells)):
                if not text:
                    continue
                align = 'c' if column in (0, 1, 2, 5) or (column == 4 and style in ('title', 'section_title')) else 'l'
                value = escape(text)
                if column == 4 and style in ('title', 'section_title'):
                    value = r'\uline{' + value + '}'
                content.append(r'\SpecCell{%s}{%s}{%s}{%s}{%s}' % (x, y, width, align, value))
        rendered.append(r'\SpecPage{%d}{%d}{%s}' % (number, FIRST_PAGE_ROWS if number == 1 else NEXT_PAGE_ROWS, '\n'.join(content)))
    template = string.Template((directory / 'specification.tex').read_text(encoding='utf8'))
    def multiline(value, width, size=BODY_PT):
        return r'\\'.join(escape(line) for line in metrics.wrap(value, width, size))
    values = {
        'TemplatePath': directory.as_posix() + '/',
        'DocumentNumber': multiline(stamp['number'], 97.4, 18),
        'Title': multiline(stamp['title'], 67.4, 18),
        'Organization': multiline(stamp['company'], 47.4, 18),
        'Author': multiline(stamp['developer'], 20.4),
        'Checker': multiline(stamp['verifier'], 20.4),
        'Normcontr': multiline(stamp['inspector'], 20.4),
        'Approver': multiline(stamp['approver'], 20.4),
        'FirstUsage': escape(stamp.get('first_usage', '')),
        'Sheets': str(len(pages)),
        'Content': '\n\\newpage\n'.join(rendered),
    }
    Path(output).write_text(template.substitute(values), encoding='utf8')
