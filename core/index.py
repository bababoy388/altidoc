import traceback
from . import schematic, config

def build(netlist):
    '''Построить перечень элементов.

    Построить перечень элементов на основе данных из файла списка цепей.
    
    '''
    
    COLUMN_COUNT = 4+1
    COL_REF      = 0
    COL_NAME     = 1
    COL_QTY      = 2
    COL_COMMENT  = 3
    COL_STYLE    = -1
    table = []
    
    # --------------------------------------------------------------------
    # Методы для построения таблицы
    # --------------------------------------------------------------------
    def pad_or_truncate(lst, target_len):
        return lst[:target_len] + ['']*(target_len - len(lst))
        
    def gotoNextRow(count=1):
        nonlocal table
        table += count * [['']*COLUMN_COUNT]

    def fillRow(values, isTitle=False):
        table[-1] = pad_or_truncate(values, COLUMN_COUNT)
        if(isTitle):
            table[-1][COL_STYLE] = 'title'
        gotoNextRow()
    
    # --------------------------------------------------------------------
    # Начало построения таблицы
    # --------------------------------------------------------------------
    try:
        sch = schematic.Schematic(netlist)
        if sch is None:
            return
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
                fillRow(['', classtitle], isTitle = True)
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
                        compRef = group[0].getRefRangeString()
                        compType = group[0].getIndexValue('type', singular=True)
                        compName = group[0].getIndexValue('name')
                        compDoc = group[0].getIndexValue('doc')
                        name = ''
                        if compType:
                            name += compType + ' '
                        name += compName
                        if compDoc:
                            name += ' ' + compDoc
                        compComment = group[0].getIndexValue('comment')
                        fillRow(
                            [compRef, name, str(len(group[0])), compComment]
                        )
                else:
                    titleLines = group.getTitle()
                    for title in titleLines:
                        if title and classtitle != title:
                            fillRow(['', title], isTitle = True)
                    if config.getboolean('table', 'empty row after group title'):
                        gotoNextRow()
                    for compRange in group:
                        compRef = compRange.getRefRangeString()
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
                        fillRow(
                            [compRef, name, str(len(compRange)), compComment]
                        )
                prevGroup = group
        
        return table
        
    except:
        # Ошибка!
        print(
            'При построении возникла ошибка:\n\n' \
            + traceback.format_exc(),
            'Перечень элементов'
        )
