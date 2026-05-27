from . import schematic, config
import re

def build(netlist, auto_num=True):
    '''Построить перечень элементов.'''

    COLUMN_COUNT = 4 + 1
    COL_REF = 0
    COL_NAME = 1
    COL_QTY = 2
    COL_COMMENT = 3
    COL_STYLE = -1
    table = []

    # --------------------------------------------------------------------
    # Методы для построения таблицы
    # --------------------------------------------------------------------
    def pad_or_truncate(lst, target_len):
        return lst[:target_len] + [''] * (target_len - len(lst))

    def gotoNextRow(count=1):
        nonlocal table
        table += count * [[''] * COLUMN_COUNT]

    def fillRow(values, isTitle=False):
        table[-1] = pad_or_truncate(values, COLUMN_COUNT)
        if isTitle:
            table[-1][COL_STYLE] = 'title'
        gotoNextRow()

    # --------------------------------------------------------------------
    # Парсинг строки перечисления позиций
    # --------------------------------------------------------------------
    def _parse_ref_list(ref_str):
        """
        Из строки 'C1, C4, C7-C8, C13, C14' возвращает список сегментов
        [(prefix, start, end), ...].
        """
        if not ref_str:
            return []
        parts = [p.strip() for p in ref_str.split(',')]
        segments = []
        token_re = re.compile(r'^([A-Za-z]+)(\d+)(?:\s*[-–]\s*\1?(\d+))?$')
        for part in parts:
            m = token_re.match(part)
            if m:
                typ = m.group(1)
                start = int(m.group(2))
                end = int(m.group(3)) if m.group(3) else start
                if end < start:
                    start, end = end, start
                segments.append((typ, start, end))
        return segments

    # --------------------------------------------------------------------
    # Функция разбиения на чанки (не более 3 элементов)
    # --------------------------------------------------------------------
    def split_refs_to_chunks(comp_range, max_elements=3):
        """
        Всегда вызывается для получения списка строк.
        Сама определяет, нужно ли разбиение, и возвращает список
        кортежей [(ref_str, qty), ...].
        """
        refs = list(comp_range)

        # Случай: один элемент-строка с запятыми/диапазонами (Altium BOM)
        if len(refs) == 1 and (',' in refs[0] or '-' in refs[0]):
            segments = _parse_ref_list(refs[0])
        else:
            # Обычный случай: отдельные обозначения
            segments = []
            if refs:
                cur_type = comp_range.getRefType(refs[0])
                cur_start = comp_range.getRefNumber(refs[0])
                cur_end = cur_start
                for ref in refs[1:]:
                    t = comp_range.getRefType(ref)
                    n = comp_range.getRefNumber(ref)
                    if t == cur_type and n == cur_end + 1:
                        cur_end = n
                    else:
                        segments.append((cur_type, cur_start, cur_end))
                        cur_type = t
                        cur_start = n
                        cur_end = n
                segments.append((cur_type, cur_start, cur_end))

        if not segments:
            return []

        # Проверяем adjustable
        adjustable_field = config.get("fields", "adjustable")
        adjustable = (comp_range.getFieldValue(adjustable_field) is not None)

        def seg_to_str(seg):
            t, s, e = seg
            star = '*' if adjustable else ''
            if s == e:
                return f"{t}{s}{star}"
            else:
                sep = config.get("table", "ref separator")
                return f"{t}{s}{star}{sep}{t}{e}{star}"

        chunks = []
        for i in range(0, len(segments), max_elements):
            chunk_segs = segments[i:i+max_elements]
            ref_str = ", ".join(seg_to_str(s) for s in chunk_segs)
            qty = sum(e - s + 1 for _, s, e in chunk_segs)
            chunks.append((ref_str, qty))
        return chunks

    # --------------------------------------------------------------------
    # Начало построения таблицы
    # --------------------------------------------------------------------
    sch = schematic.Schematic(netlist, auto_num=auto_num)
    if sch is None:
        return [], []
    compGroups = sch.getSuperGroupedComponentsIndex()
    prevGroup = None
    emptyRowsRef = config.getint('table', 'empty rows between diff ref')
    emptyRowsType = config.getint('table', 'empty rows between diff type')
    classtitle = ''

    gotoNextRow()

    for classgroup in compGroups:
        if config.getboolean('table', 'put class header'):
            if prevGroup is not None:
                emptyRows = 0
                if classgroup[0][0].getRefType() != prevGroup[-1].getRefType():
                    emptyRows = emptyRowsRef
                else:
                    emptyRows = emptyRowsType
                gotoNextRow(emptyRows)
            classtitle = classgroup[0][0].getIndexValue('class', plural=True)
            fillRow(['', classtitle], isTitle=True)
            if config.getboolean('table', 'empty row after class title'):
                gotoNextRow()
            prevGroup = None
        for group in classgroup:
            if prevGroup is not None:
                emptyRows = 0
                if group[0].getRefType() != prevGroup[-1].getRefType():
                    emptyRows = emptyRowsRef
                else:
                    emptyRows = emptyRowsType
                gotoNextRow(emptyRows)
            if len(group) == 1 \
                    and not config.getboolean('table', 'every group has title'):
                comp_obj = group[0]
                compType = comp_obj.getIndexValue('type', singular=True)
                compName = comp_obj.getIndexValue('name')
                compDoc = comp_obj.getIndexValue('doc')
                name = ''
                if compType:
                    name += compType + ' '
                name += compName
                if compDoc:
                    name += ' ' + compDoc
                compComment = comp_obj.getIndexValue('comment')

                # Получаем все чанки
                chunks = split_refs_to_chunks(comp_obj)
                for idx, (ref_str, qty) in enumerate(chunks):
                    # Количество только в первой строке
                    qty_str = str(qty) if idx == 0 else ''
                    fillRow([ref_str, name, qty_str, compComment])
            else:
                titleLines = group.getTitle()
                for title in titleLines:
                    if title and classtitle != title:
                        fillRow(['', title], isTitle=True)
                if config.getboolean('table', 'empty row after group title'):
                    gotoNextRow()
                for compRange in group:
                    compName = compRange.getIndexValue('name')
                    compDoc = compRange.getIndexValue('doc')
                    name = compName
                    if compDoc:
                        for title in titleLines:
                            if title.endswith(compDoc):
                                break
                        else:
                            name += ' ' + compDoc
                    compComment = compRange.getIndexValue('comment')

                    # Получаем все чанки
                    chunks = split_refs_to_chunks(compRange)
                    for idx, (ref_str, qty) in enumerate(chunks):
                        qty_str = str(qty) if idx == 0 else ''
                        fillRow([ref_str, name, qty_str, compComment])
            prevGroup = group

    # --------------------------------------------------------------------
    # Добавление пустых строк для заполнения страниц PDF
    # --------------------------------------------------------------------
    rows_first_page = 27
    rows_other_pages = 29

    total_rows = len(table)
    if total_rows < rows_first_page:
        need = rows_first_page - total_rows
    else:
        remainder = (total_rows - rows_first_page) % rows_other_pages
        need = 0 if remainder == 0 else rows_other_pages - remainder

    for _ in range(need):
        table.append([''] * COLUMN_COUNT)

    return table, sch.fixed_references_log