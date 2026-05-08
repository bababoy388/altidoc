"""Параметры работы.

Модуль предоставляет средства для загрузки и сохранения параметров.

"""

import os
import sys
from configparser import ConfigParser

SETTINGS = ConfigParser()
SETTINGS.optionxform=str

def load(path, encoding='utf-8'):
    """Загрузить настройки.

    Считать параметры работы из файла.

    """
    
    SETTINGS.read_dict({
        'gui' : {
            'tables' : 'index,spec,bom,sds'
        },
        'table': {
            'add units'                             : 'yes',
            'put class header'                      : 'yes',
            'empty row after class title'           : 'yes',
            'concatenate same name groups'          : 'yes',
            'empty row after group title'           : 'no',
            'empty rows between diff ref'           : '1',
            'empty rows between diff type'          : '1',
            'every group has title'                 : 'yes',
            'only components have position numbers' : 'no',
            'process repeated values'               : 'no',
            'ref separator'                         : '-',
            'reserve position numbers'              : 'no',
            'separate group for each doc'           : 'no',
            'space before units'                    : 'yes',
            'title with doc'                        : 'no'
        },
        'sections': {
            'assembly drawing'                : 'yes',
            'assembly drawing_variant'        : 'yes',
            'assembly drawing_default_format' : 'А3',
            'assembly units'                  : 'no',
            'bom'                             : 'yes',
            'bom_variant'                     : 'yes',
            'certsheet'                       : 'yes',
            'certsheet_variant'               : 'yes',
            'details'                         : 'yes',
            'docsheet'                        : 'yes',
            'docsheet_variant'                : 'yes',
            'documentation'                   : 'yes',
            'index'                           : 'yes',
            'index_variant'                   : 'yes',
            'materials'                       : 'no',
            'opmodemaps'                      : 'yes',
            'opmodemaps_variant'              : 'yes',
            'other parts'                     : 'yes',
            'pcb'                             : 'yes',
            'pcb_variant'                     : 'no',
            'schematic'                       : 'yes',
            'schematic_variant'               : 'yes',
            'schematic_default_format'        : 'А3',
            'standard parts'                  : 'no'
        },
        'fields': {
            'adjustable': 'Подбирают при регулировании'
        },
        'fields_index': {
            'class'     : '_Class',
            'type'      : '_Subclass',
            'name'      : '${|Comment|, }${|_FType|, }${|Size|, }${|Color|, }${|Number of capacitors| × }${|Number of resistors| × }${|_Value|}${ |Tolerance|}${ × |Rated voltage|}${ × |Rated current|}${, |TC|}',
            'doc'       : 'Стандарт',
            'comment'   : 'Примечание'
        },
        'fields_spec': {
            'class'     : '_Class',
            'type'      : '_Subclass',
            'number'    : 'Comment',
            'name'      : '${|_FType|, }${|Size|, }${|Color|, }${|Number of capacitors| × }${|Number of resistors| × }${|_Value|}${ |Tolerance|}${ × |Rated voltage|}${ × |Rated current|}${, |TC|}',
            'doc'       : 'Стандарт',
            'comment'   : 'Примечание'
        },
        'fields_bom': {
            'class'     : '_Class',
            'type'      : '_Subclass',
            'name'      : '${|Comment|, }${|_FType|, }${|Size|, }${|Color|, }${|Number of capacitors| × }${|Number of resistors| × }${|_Value|}${ |Tolerance|}${ × |Rated voltage|}${ × |Rated current|}${, |TC|}',
            'code'      : '',
            'doc'       : 'Стандарт',
            'dealer'    : '',
            'for what'  : '',
            'comment'   : 'Примечание'
        },
        'fields_sds': {
            'number'     : 'Comment',
            'vendor'     : 'Manufacturer',
            'comment'   : 'Примечание'
        },
        'stamp': {
            'convert doc id'                : 'yes',
            'convert doc title'             : 'yes',
            'fill first usage'              : 'yes',
            'place doc id to table title'   : 'yes'
        },
        'aliases': {
            'значение': 'Номинал'
        },
        'output': {
            'csv_delimiter' : ',',
            'default_type'  : 'pdf',
            'latex_path'    : 'latex/',
            'latex_template': 'latex/template.tex'
        },
        'export': {
            'index': 'pdf',
            'spec' : 'pdf',
            'bom'  : 'pdf',
            'sds'  : 'csv'
        },
        'custom_types' : {
            'Резистор постоянный'           : 'Резисторы постоянные',
            'Конденсатор пленочный'         : 'Конденсаторы пленочные',
            'Конденсатор керамический'      : 'Конденсаторы керамические',
            'Конденсатор танталовый'        : 'Конденсаторы танталовые',
            'Конденсатор электролитический' : 'Конденсаторы электролитические',
            'Суперконденсатор'              : 'Суперконденсаторы',
            'Ферритовая бусина'             : 'Ферритовые бусины',
            'Индуктивность высокочастотная' : 'Индуктивности высокочастотные',
            'Индуктивность силовая'         : 'Индуктивности силовые',
            'Светодиод'                     : 'Светодиоды'
        }
    })

    if os.path.isfile(path):
        SETTINGS.read(path, encoding)

def get(section, option):
    """Получить значение параметра "option" из раздела "section"."""
    return SETTINGS.get(section, option)

def getboolean(section, option):
    """Получить булево значение параметра "option" из раздела "section"."""
    return SETTINGS.getboolean(section, option)

def getint(section, option):
    """Получить целочисленное значение параметра "option" из раздела "section"."""
    return SETTINGS.getint(section, option)

def getsection(section):
    """Получить раздел "section" в виде словаря."""
    return dict(SETTINGS.items(section))

def set(section, option, value):
    """Записать значение параметра "option" из раздела "section"."""
    return SETTINGS.set(section, option, value)
