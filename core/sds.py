import re
import sys
import traceback

from . import stamp, schematic, config

def build(netlist):
    """Построить SDS.

    Построить спецификацию на основе данных из файла списка цепей.

    """
    currentPosition = 1
    COLUMN_COUNT = 5+1
    COL_POS      = 0
    COL_NAME     = 1
    COL_QTY      = 2
    COL_VENDOR   = 3
    COL_COMMENT  = 4
    COL_STYLE    = -1
    table = []

    # --------------------------------------------------------------------
    # Методы для построения таблицы
    # --------------------------------------------------------------------
    def pad_or_truncate(lst, target_len):
        return lst[:target_len] + ['']*(target_len - len(lst))

    def gotoNextRow(count=1, fitted = True):
        nonlocal table
        if fitted:
            table += count * [['']*COLUMN_COUNT]

    def isRowEmpty(row):
        lastCol = len(table.Rows[row].TableColumnSeparators)
        rowCells = table.getCellRangeByPosition(
            0, # left
            row, # top
            lastCol, # right
            row # bottom
        )
        dataIsPresent = any(rowCells.DataArray[0])
        return not dataIsPresent

    def fillSectionTitle(section, fitted = True):
        if fitted:
            table[-1][COL_NAME] = section
            table[-1][COL_STYLE] = 'section_title'
            gotoNextRow()

    def fillRow(values, isTitle=False, posIncrement=0, fitted = True):
        nonlocal currentPosition
        if posIncrement:
            values[COL_POS] = str(currentPosition)
            currentPosition += posIncrement
        if fitted:
            table[-1] = pad_or_truncate(values, COLUMN_COUNT)
            if isTitle:
                table[-1][COL_STYLE] = 'title'
            gotoNextRow()

    # --------------------------------------------------------------------
    # Начало построения таблицы
    # --------------------------------------------------------------------
    try:
        sch = schematic.Schematic(netlist)
        if sch is None:
            return
        compGroups = sch.getSuperGroupedComponentsSpec()
        prevGroup = None
        emptyRowsType = config.getint("table", "empty rows between diff type")
        classtitle = ''
        variant = sch.variant
        
        gotoNextRow()
        
        if config.getboolean("sections", "pcb"):
            currentPosition += 1

        for classgroup in compGroups:
            for group in classgroup:
                increment = 1
                if prevGroup is not None:
                    if config.getboolean("table", "reserve position numbers"):
                        increment += emptyRowsType
                if config.getboolean("table", "empty row after group title"):
                    if config.getboolean("table", "reserve position numbers"):
                        increment += 1
                for compRange in group:
                    compNumber = compRange.getSdsValue("number")
                    compVendor = compRange.getSdsValue("vendor")
                    compRef = compRange.getRefRangeFittedString()
                    compComment = compRange.getSdsValue("comment")
                    comment = compRef
                    if comment:
                        if compComment:
                            comment = comment + '\n' + compComment
                    else:
                        comment = compComment
                    fillRow(
                        ["", compNumber, str(compRange.lenFitted()), compVendor, comment],
                        posIncrement=increment,
                        fitted = compRange.isFitted()
                    )
                    increment = 1
                prevGroup = group
            
        for rowIndex in range(len(table)):
            table[rowIndex][COL_COMMENT] = table[rowIndex][COL_COMMENT].replace('\n', ', ')
            table[rowIndex][COL_COMMENT] = table[rowIndex][COL_COMMENT].replace('Формованная', 'Формовать')
        
        return table[:-1]

    except:
        # Ошибка!
        print(
            "При построении возникла ошибка:\n\n" \
            + traceback.format_exc(),
            "Спецификация")
