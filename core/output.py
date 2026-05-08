import os, sys, string
import csv as CSV
#import xlrd, xlwt, xlutils
#from xlutils.copy import copy
from . import config
from copy import deepcopy

lookup = {
    'Перечень элементов' : {
        'format'        : 'a4paper',
        'table'         : 'ESKDbill',
        'xls_template'  : 'index.xlt',
        'header'        : [
            'Поз. обознач.',
            'Наименование',
            'Кол.',
            'Примечание']
    },
    '' : { # Спецификация
        'format'        : 'a4paper',
        'table'         : 'ESKDspecification',
        'xls_template'  : 'spec.xlt',
        'header'        : [
            'Формат',
            'Зона',
            'Поз.',
            'Обозначение',
            'Наименование',
            'Кол.',
            'Примечание'
        ]
    },
    'Ведомость покупных изделий' : {
        'format'        : 'a3paper',
        'table'         : 'ESKDspecpurchase',
        'xls_template'  : 'bom.xlt',
        'header'        : [
            '№ строки',
            'Наименование',
            'Код продукции',
            'Обозначение документа на поставку',
            'Поставщик',
            'Куда входит (обозначение)',
            'На изделие',
            'В комплекты',
            'На регулир.',
            'Всего',
            'Примечание'
        ]
    },
    'SDS Компэл' : {
        'format'        : None,
        'table'         : None,
        'xls_template'  : None,
        'header'        : [
            'Поз. обознач.',
            'Наименование',
            'Кол.',
            'Производитель',
            'Примечание'
        ]
    },
    'SDS (без произв.)' : {
        'format'        : None,
        'table'         : None,
        'xls_template'  : None,
        'header'        : [
            'Поз. обознач.',
            'Наименование',
            'Кол.',
            'Примечание'
        ]
    }
}

stamp_lookup = {
    'Обозначение'   : 'number',
    'Наименование'  : 'title',
    'Тип'           : 'type',
    'Разраб.'       : 'developer',
    'Пров.'         : 'verifier',
    'Н. контр.'     : 'inspector',
    'Утв.'          : 'approver',
    'Перв. примен.' : 'first_usage',
    'Организация'   : 'company',
    'Листов'        : 'sheets'
}

def latex(table, stamp, output):
    
    if stamp['type'] == 'SDS Компэл':
        return
    
    def replace_latex_specchar(text):
        return text.replace('%', '\\%')\
                   .replace('_', '\\_')\
                   .replace('±', '$\\pm$')\
                   .replace('×', '$\\times$')\
                   .replace('"', '\\textquotedbl')\
                   .replace('«', '<<')\
                   .replace('»', '>>')

    template_dir = config.get('output', 'template_path')
    template_abs_dir = os.path.abspath(template_dir).replace('\\', '/') + '/'
    template_path = os.path.join(template_dir, 'template.tex')
    
    with open(template_path, 'rt', encoding='utf8') as fid:
        template = string.Template(fid.read())
    
    tab = deepcopy(table)
    
    header = lookup[stamp['type']]['header']
    
    header[0] = '% ' + header[0]
    max_len = []
    
    for i in range(len(header)):
        max_len.append(len(header[i]))
    
    for i in range(len(tab)):
        name = tab[i][header.index('Наименование')]
        if tab[i][-1] == 'title':
             tab[i][header.index('Наименование')] = \
                '\\centering\\uline{%s}'%name
        elif tab[i][-1] == 'section_title':
             tab[i][header.index('Наименование')] = \
                '\\centering\\textbf{\\uline{%s}}'%name
        for j in range(len(tab[i])-1):
            tab[i][j] = replace_latex_specchar(tab[i][j])
            max_len[j] = max(max_len[j], len(tab[i][j]))
    
    for i in range(len(max_len)):
        max_len[i] = '{:<%d}'%(min(max_len[i], 100))    
    fmt = '  &  '.join(max_len) + '  \\\\ \\hline\n'
    
    content = fmt.format(*header)
    for row in tab:
        content += fmt.format(*row[:-1])

    table_env = lookup[stamp['type']]['table']

    if table_env == 'ESKDbill':
        blockwidth_cmd = '\\billblockwidth'
    elif table_env == 'ESKDspecification':
        blockwidth_cmd = '\\specblockwidth'
    elif table_env == 'ESKDspecpurchase':
        blockwidth_cmd = '\\purchaseblockwidth'
    else:
        blockwidth_cmd = '0pt'

    substitutions = {
        'Format': lookup[stamp['type']]['format'],
        'DocumentNumber': replace_latex_specchar(stamp['number']),
        'Title': replace_latex_specchar(stamp['title']),
        'Type': stamp['type'] if stamp['type'] != 'Спецификация' else '',
        'Environment': table_env,
        'Author': replace_latex_specchar(stamp['developer']),
        'Checker': replace_latex_specchar(stamp['verifier']),
        'Normcontr': replace_latex_specchar(stamp['inspector']),
        'Approver': replace_latex_specchar(stamp['approver']),
        'Organization': replace_latex_specchar(stamp['company']),
        'FirstUsage': replace_latex_specchar(stamp['first_usage']),
        'Sheets': '\\pageref{LastPage}',
        'SquaresBlockWidth': blockwidth_cmd,
        'Content': content,
        'TemplatePath': template_abs_dir,
    }
    
    with open(output, 'wt', encoding='utf8') as fid:
        fid.write(template.safe_substitute(substitutions))

def csv(table, stamp, output):
    header = lookup[stamp['type']]['header']
    
    delimiter = config.get('output', 'csv_delimiter').replace('\\t', '\t')
    
    with open(output, 'wt', encoding='utf8',  newline='') as fid:
        writer = CSV.writer(fid, delimiter=delimiter)
        if stamp['type'] != 'SDS Компэл' and stamp['type'] != 'SDS (без произв.)':
            fid.write(', '.join(['"{}":"{}"'.format(key, stamp.get(value, ''))
                                 for (key,value) in stamp_lookup.items()]) + '\n')
        writer.writerow(header)
        for row in table:
            writer.writerow(row[:-1])

def xls(table, stamp, output):
    
    if stamp['type'] == 'SDS Компэл':
        return
    
    template_dir = config.get('output', 'template_path')
    template_file = lookup[stamp['type']]['xls_template']
    template_path = os.path.join(template_dir, template_file)
    header = lookup[stamp['type']]['header']
    
    tab = deepcopy(table)
    
    rb = xlrd.open_workbook(template_path,on_demand=True,formatting_info=True)
    wb = xlutils.copy.copy(rb)
    ws = wb._Workbook__worksheets[0]
    ws.name = stamp['number']
    
    numeric_cells = [
        'Поз.',
        'Кол.',
        '№ строки',
        'На изделие',
        'В комплекты',
        'На регулир.',
        'Всего'
    ]
    
    center_cells = ['Поз. обознач.', 'Формат', 'Зона', 'Масса']
    
    def _getOutCell(row, col):
        ''' HACK: Extract the internal xlwt cell representation. '''
        row = ws._Worksheet__rows.get(row)
        if not row: return None
        cell = row._Row__cells.get(col)
        return cell
    
    row_begin = 2 if template_file == 'bom.xlt' else 1
    
    # Cells with predefined styles
    specstyle = {
        'center' : _getOutCell(row_begin, 0),
        'bold'   : _getOutCell(row_begin, 1),
        'uline'  : _getOutCell(row_begin, 2),
        'italic' : _getOutCell(row_begin, 3)
    }
    
    def setOutCell(row, col, value, style):
        ''' Change cell value with predefined formatting. '''
        # HACK to retain cell style.
        previousCell = specstyle[style]
        # END HACK, PART I
        
        ws.write(row, col, value)
        
        # HACK, PART II
        if previousCell:
            newCell = _getOutCell(row, col)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx
        # END HACK
    
    def write_row(row, content):
        for col, cell in enumerate(content[:-1]):
            cell = cell.replace('×', 'x')
            if header[col] in numeric_cells:
                cell = int(cell) if cell != '' else cell
                setOutCell(row, col, cell, 'center')
            elif header[col] in center_cells:
                setOutCell(row, col, cell, 'center')
            elif header[col] == 'Наименование':
                if content[-1] == 'title':
                    setOutCell(row, col, cell, 'uline')
                elif content[-1] == 'section_title':
                    setOutCell(row, col, cell, 'bold')
                else:
                    setOutCell(row, col, cell, 'italic') 
            else:
                setOutCell(row, col, cell, 'italic') 
    
    ws_row = row_begin
    
    for row in tab:
        write_row(ws_row, row)
        ws_row += 1
    
    # Adding formulas   
    if template_file == 'bom.xlt':
        for row in range(row_begin, len(ws.rows)):
            formula_sum = 'SUM({}:{})'.format(
                xlwt.Utils.rowcol_to_cell(row, header.index('На изделие')),
                xlwt.Utils.rowcol_to_cell(row, header.index('На регулир.')))
            formula = 'IF({} > 0;{},"")'.format(formula_sum, formula_sum)
            setOutCell(row,header.index('Всего'),xlwt.Formula(formula),'center')

    # Adjust row heights
    for i in range(row_begin, len(ws.rows)):
        ws.rows[i].height = 455 # 8 mm
    
    wb.save(output)

def screen(table, stamp):
    header = lookup[stamp['type']]['header']
    
    max_len = []
    
    for i in range(len(header)):
        max_len.append(len(header[i]))
    
    for i in range(len(table)):
        for j in range(len(table[i])-1):
            max_len[j] = max(max_len[j], len(table[i][j]))
            
    lines = []
    
    for i in range(len(max_len)):
        lines.append('-' * max_len[i])
        max_len[i] = '{:<%d}'%(min(max_len[i], 100))
    fmt = '|  ' + '  |  '.join(max_len) + '  |'
    
    hline = '+--' + '--+--'.join(lines) + '--+'
    
    print('\x1b[36m' + hline + '\n' + fmt.format(*header) + '\n' + hline)
    for row in table:
        style = {
                    'title':'\x1b[32m',
                    'section_title':'\x1b[36m',
                    '':'\x1b[0m'
                }[row[-1]]
        print(style + fmt.format(*row[:-1]) + '\x1b[0m')
    print(hline)
