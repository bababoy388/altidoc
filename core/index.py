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
        else:
            table[-1][COL_STYLE] = ''
        gotoNextRow()

    # --------------------------------------------------------------------
    # Проверка на "не устанавливать" (Н/У, NC + not fitted)
    # --------------------------------------------------------------------
    def _check_not_installed(name):
        if not name:
            return False
        clean = re.sub(r'\s+', '', name).upper()
        return 'Н/У' in clean or 'NC' in clean

    # --------------------------------------------------------------------
    # Парсинг строки перечисления позиций
    # --------------------------------------------------------------------
    def _parse_ref_list(ref_str):
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
        refs = list(comp_range)

        if len(refs) == 1 and (',' in refs[0] or '-' in refs[0]):
            segments = _parse_ref_list(refs[0])
        else:
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

        # ------------------------------------------------------------
        # Разворачиваем сегменты длиной 2 в два одиночных обозначения
        # ------------------------------------------------------------
        expanded_segments = []
        for typ, s, e in segments:
            if e - s == 1:
                expanded_segments.append((typ, s, s))
                expanded_segments.append((typ, e, e))
            else:
                expanded_segments.append((typ, s, e))
        segments = expanded_segments

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

        # ------------------------------------------------------------
        # Разбиваем на чанки с новым правилом:
        # - диапазон (e > s) всегда один в чанке
        # - одиночные группируются до 3 штук
        # ------------------------------------------------------------
        chunks = []
        i = 0
        while i < len(segments):
            typ, s, e = segments[i]
            if e > s:   # диапазон
                chunks.append( (seg_to_str((typ, s, e)), e - s + 1) )
                i += 1
            else:       # одиночные
                singles = []
                qty = 0
                while i < len(segments) and segments[i][1] == segments[i][2] and len(singles) < max_elements:
                    singles.append(segments[i])
                    qty += 1
                    i += 1
                ref_str = ", ".join(seg_to_str(s) for s in singles)
                chunks.append( (ref_str, qty) )

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

                if not comp_obj.fitted or _check_not_installed(name):
                    compComment = "не устанавливать"

                chunks = split_refs_to_chunks(comp_obj)
                total_qty = sum(qty for _, qty in chunks)

                for idx, (ref_str, _) in enumerate(chunks):
                    if idx == 0:
                        qty_str = str(total_qty)
                        name_str = name
                    else:
                        qty_str = ''
                        name_str = ''
                    fillRow([ref_str, name_str, qty_str, compComment])
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

                    if not compRange.isFitted() or _check_not_installed(name):
                        compComment = "не устанавливать"

                    chunks = split_refs_to_chunks(compRange)
                    total_qty = sum(qty for _, qty in chunks)

                    for idx, (ref_str, _) in enumerate(chunks):
                        if idx == 0:
                            qty_str = str(total_qty)
                            name_str = name
                        else:
                            qty_str = ''
                            name_str = ''
                        fillRow([ref_str, name_str, qty_str, compComment])
            prevGroup = group

    # --------------------------------------------------------------------
    # Обработка последних/предпоследних строк + удаление полностью пустых страниц
    # --------------------------------------------------------------------
    rows_first_page = 27
    rows_other_pages = 29

    data_rows = len(table)
    if data_rows <= rows_first_page:
        target_rows = rows_first_page
    else:
        remainder = (data_rows - rows_first_page) % rows_other_pages
        if remainder == 0:
            target_rows = data_rows
        else:
            target_rows = data_rows + (rows_other_pages - remainder)

    while len(table) < target_rows:
        table.append([''] * COLUMN_COUNT)

    # Собираем заголовки, попавшие на последнюю или предпоследнюю позицию
    insert_indices = set()
    page = 0
    while True:
        if page == 0:
            rows_this_page = rows_first_page
        else:
            rows_this_page = rows_other_pages
        start_idx = sum(rows_first_page if p == 0 else rows_other_pages for p in range(page))
        end_idx = start_idx + rows_this_page - 1
        if start_idx >= len(table):
            break
        end_idx = min(end_idx, len(table) - 1)

        if table[end_idx][COL_STYLE] == 'title':
            insert_indices.add(end_idx)
        if end_idx - 1 >= start_idx and table[end_idx - 1][COL_STYLE] == 'title':
            insert_indices.add(end_idx - 1)

        page += 1

    for idx in sorted(insert_indices, reverse=True):
        table.insert(idx, [''] * COLUMN_COUNT)

    # Удаляем страницы, полностью состоящие из пустых строк (кроме первой)
    def is_row_empty(row):
        return all(cell == '' for cell in row)

    cleaned_table = []
    page = 0
    idx = 0
    while idx < len(table):
        if page == 0:
            page_rows = rows_first_page
        else:
            page_rows = rows_other_pages
        chunk = table[idx:idx+page_rows]
        # Удаляем страницу только если она не первая и вся состоит из пустых строк
        if page > 0 and all(is_row_empty(r) for r in chunk):
            pass  # пропускаем эту страницу
        else:
            cleaned_table.extend(chunk)
        idx += page_rows
        page += 1

    table = cleaned_table

    # Окончательное дополнение до целого числа страниц
    total_rows = len(table)
    if total_rows < rows_first_page:
        need = rows_first_page - total_rows
    else:
        remainder = (total_rows - rows_first_page) % rows_other_pages
        need = 0 if remainder == 0 else rows_other_pages - remainder

    for _ in range(need):
        table.append([''] * COLUMN_COUNT)

    return table, sch.fixed_references_log