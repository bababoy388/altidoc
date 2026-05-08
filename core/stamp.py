import re
from . import schematic, config

def build(netlist, doc_type = 'index', add_variant = True):
    '''Заполнить основную надпись.

    Считать данные из файла списка цепей и заполнить графы основной надписи.
    
    Аргументы:
    
    sch - файл списка цепей.
    
    doc_type - тип документа:
        'index'      - перечень элементов;
        'assembly'   - сборочный чертёж;
        'spec'       - спецификация;
        'bom'        - ведомость покупных изделий;
        'gspec'      - групповая спецификация;
        'gbom'       - групповая ведомость покупных изделий;
        'mexanic'    - ведомость покупных ЭРЭ;
        'docsheet'   - ведомость документов на носителях данных;
        'certsheet'  - информационно-удостоверяющий лист;
        'opmodemaps' - карты рабочих режимов;
        'manual'     - пояснительная записка;
        'sds'        - файл для закупки через SDS Компэл.
        
    Возвращаемое значение: словарь со следующими ключами:
        'number'      - обозначение документа (графы 2 и 26);
        'title'       - наименование документа (графа 1);
        'type'        - тип документа (графа 1);
        'developer'   - фамилия разработчика (графа 11);
        'verifier'    - фамилия проверяющего (графа 11);
        'inspector'   - фамилия нормаконтролера (графа 11);
        'approver'    - фамилия утверждающего (графа 11);
        'first_usage' - первое применение (графа 25);
        'company'     - наименование организации (графа 9);
        'amount'      - кол. на исполнение (для групповых документов).
    '''
    sch = schematic.Schematic(netlist)
    if sch is None:
        return
    
    variant = sch.variant if add_variant else ''
    stamp = {}
    
    # Наименование документа
    stamp['title'] = sch.title.replace('\\n', '\n')
    if config.getboolean('stamp', 'convert doc title'):
        tailPos = stamp['title'].find('Схема электрическая')
        if tailPos > 0:
            stamp['title'] = stamp['title'][:tailPos]
        stamp['title'] = stamp['title'].strip()
    # Тип документа
    if doc_type == 'index':
        stamp['type'] = 'Перечень элементов'
    elif doc_type == 'assembly':
        stamp['type'] = 'Сборочный чертёж'
    elif doc_type == 'spec' or doc_type == 'gspec':
        stamp['type'] = ''
    elif doc_type == 'bom' or  doc_type == 'gbom':
        stamp['type'] = 'Ведомость покупных изделий'
    elif doc_type == 'mexanic':
        stamp['type'] = 'Ведомость покупных ЭРЭ'
    elif doc_type == 'docsheet':
        stamp['type'] = 'Ведомость документов на носителях данных'
    elif doc_type == 'certsheet':
        stamp['type'] = 'Информационно-удостоверяющий лист'
    elif doc_type == 'opmodemaps':
        stamp['type'] = 'Карты рабочих режимов'
    elif doc_type == 'sds':
        stamp['type'] = 'SDS Компэл'
    elif doc_type == 'sds2':
        stamp['type'] = 'SDS (без произв.)'
    # Обозначение документа
    stamp['number'] = sch.number
    idParts = re.match(r'([А-ЯA-Z0-9]+(?:[\.\-]\d+)+\s?)(Э\d)', stamp['number'])
    if idParts is None:
        idParts = re.match(r'(\S+\s?)(Э\d)', stamp['number'])
    if config.getboolean('stamp', 'convert doc id') and idParts is not None:
        number = idParts.group(1).strip() + variant
        if doc_type == 'index':
            stamp['number']= number + ' ПЭ3'
        elif doc_type == 'assembly':
            stamp['number']= number +  ' СБ'
        elif doc_type == 'spec' or doc_type == 'gspec':
            stamp['number']= number
        elif doc_type == 'bom' or  doc_type == 'gbom' or doc_type == 'mexanic':
            stamp['number']= number + ' ВП'
        elif doc_type == 'docsheet':
            stamp['number']= number + ' ВН'
        elif doc_type == 'certsheet':
            stamp['number']= number + ' УЛ'
        elif doc_type == 'opmodemaps':
            stamp['number']= number + ' Д4'
        elif doc_type == 'sds':
            stamp['number']= number + '_sds'
        elif doc_type == 'sds2':
            stamp['number'] = number + '_sds2'
    # Кол. на исполнение (для групповых документов)
    if config.getboolean('stamp', 'place doc id to table title') and idParts is not None:
        stamp['amount'] = 'Кол. на исполнение {}-'.format(idParts.group(1).strip())
    # Разработал
    stamp['developer'] = sch.developer
    # Проверил
    stamp['verifier'] = sch.verifier
    # Нормативный контроль
    stamp['inspector'] = sch.inspector
    # Утвердил
    stamp['approver'] = sch.approver
    # Перв. применен.
    if config.getboolean('stamp', 'fill first usage') and idParts is not None:
        stamp['first_usage'] = idParts.group(1).strip()
    else:
        stamp['first_usage'] = ''
    # Наименование организации
    stamp['company'] = sch.company.replace('\\n', '\n')
    return stamp

