import re
import sys
import traceback

from . import stamp, schematic, config

def build(netlist):
    """Построить спецификацию.

    Построить спецификацию на основе данных из файла списка цепей.

    """
    currentPosition = 1
    COLUMN_COUNT = 7+1
    COL_FMT      = 0
    COL_ZONE     = 1
    COL_POS      = 2
    COL_NUMBER   = 3
    COL_NAME     = 4
    COL_QTY      = 5
    COL_COMMENT  = 6
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

        if config.getboolean("sections", "documentation"):
            fillSectionTitle("Документация")

            if config.getboolean("sections", "assembly drawing") \
                or config.getboolean("sections", "schematic") \
                or config.getboolean("sections", "index") \
                or config.getboolean("sections", "bom") \
                or config.getboolean("sections", "docsheet") \
                or config.getboolean("sections", "certsheet") \
                or config.getboolean("sections", "opmodemaps"):
                    gotoNextRow()

            if config.getboolean("sections", "assembly drawing"):
                stamp_dict = stamp.build(netlist, 'assembly', config.getboolean("sections", "assembly drawing_variant"))
                ref = stamp_dict['number']
                size = config.get("sections", "assembly drawing_default_format")
                name = stamp_dict['type']
                fillRow([size, "", "", ref, name])

            if config.getboolean("sections", "schematic"):
                var = variant if config.getboolean("sections", "schematic_variant") else ""
                ref = sch.number[:-3] + var + ' Э3'
                size = config.get("sections", "schematic_default_format")
                name = "Схема электрическая принципиальная"
                fillRow([size, "", "", ref, name])

            if config.getboolean("sections", "index"):
                stamp_dict = stamp.build(netlist, 'index', config.getboolean("sections", "index_variant"))
                ref = stamp_dict['number']
                size = "A4"
                name = stamp_dict['type']
                fillRow([size, "", "", ref, name])
            
            if config.getboolean("sections", "bom"):
                stamp_dict = stamp.build(netlist, 'bom', config.getboolean("sections", "bom_variant"))
                ref = stamp_dict['number']
                size = "A3"
                name = stamp_dict['type']
                fillRow([size, "", "", ref, name])
            
            if config.getboolean("sections", "docsheet"):
                stamp_dict = stamp.build(netlist, 'docsheet', onfig.getboolean("sections", "docsheet_variant"))
                ref = stamp_dict['number']
                size = "A4"
                name = stamp_dict['type']
                fillRow([size, "", "", ref, name])
            
            if config.getboolean("sections", "certsheet"):
                stamp_dict = stamp.build(netlist, 'certsheet', config.getboolean("sections", "certsheet_variant"))
                ref = stamp_dict['number']
                size = "A4"
                name = stamp_dict['type']
                fillRow([size, "", "", ref, name])

            if config.getboolean("sections", "opmodemaps"):
                stamp_dict = stamp.build(netlist, 'opmodemaps', config.getboolean("sections", "opmodemaps_variant"))
                ref = stamp_dict['number']
                size = "A4"
                name = stamp_dict['type']
                fillRow([size, "", "", ref, name])

        if config.getboolean("sections", "assembly units"):
            gotoNextRow()
            fillSectionTitle("Сборочные единицы")

        if config.getboolean("sections", "details"):
            gotoNextRow()
            fillSectionTitle("Детали")
        
            if config.getboolean("sections", "pcb"):
                gotoNextRow()
                size = ""
                ref = ""
                stamp_dict = stamp.build(netlist, 'spec')
                match = re.match(r'(\S+)(-R\d+.\d+[\S\s]*)', stamp_dict['number'])
                if match is not None:
                    if match.group(1)[-1] == '0':
                        ref = match.group(1)[:-1] + '1' + match.group(2)
                elif stamp_dict['number'][-1] == '0':
                    ref = stamp_dict['number'][:-1] + '1'
                if len(ref) != 0 and config.getboolean("sections", "pcb_variant"):
                    ref += variant
                name = "Плата печатная"
                fillRow([size, "", "", ref, name, "1"], posIncrement=1)

        if config.getboolean("sections", "standard parts"):
            gotoNextRow()
            fillSectionTitle("Стандартные изделия")

        if config.getboolean("sections", "other parts"):
            gotoNextRow()
            fillSectionTitle("Прочие изделия")

            gotoNextRow()
            for classgroup in compGroups:
                classFitted = False
                for group in classgroup:
                    if group.isFitted():
                        classFitted = True
                        break
                if config.getboolean('table', 'put class header') and classFitted:
                    increment = 1
                    if prevGroup is not None:
                        gotoNextRow(emptyRowsType)
                        if config.getboolean("table", "reserve position numbers"):
                            increment += emptyRowsType
                    classtitle = classgroup[0][0].getSpecValue('class', plural=True)
                    fillRow(["", "", "", "", classtitle], isTitle=True)
                    if config.getboolean('table', 'empty row after class title'):
                        gotoNextRow()
                    prevGroup = None
                for group in classgroup:
                    increment = 1
                    if prevGroup is not None:
                        gotoNextRow(emptyRowsType, fitted = group.isFitted())
                        if config.getboolean("table", "reserve position numbers"):
                            increment += emptyRowsType
                    if len(group) == 1 \
                        and not config.getboolean("table", "every group has title"):
                            compType = group[0].getSpecValue("type", singular=True)
                            compNumber = group[0].getSpecValue("number")
                            compName = group[0].getSpecValue("name")
                            compDoc = group[0].getSpecValue("doc")
                            name = ""
                            if compType:
                                name += compType + ' '
                            name += compName
                            if compDoc:
                                name += ' ' + compDoc
                            compRef = group[0].getRefRangeFittedString()
                            compComment = group[0].getSpecValue("comment")
                            comment = compRef
                            if comment:
                                if compComment:
                                    comment = comment + '\n' + compComment
                            else:
                                comment = compComment
                            fillRow(
                                ["", "", "", compNumber, name, str(group[0].lenFitted()), comment],
                                posIncrement=increment,
                                fitted = group[0].isFitted()
                            )
                    else:
                        titleLines = group.getTitle()
                        for title in titleLines:
                            if title and title != classtitle:
                                fillRow(["", "", "", "", title], isTitle=True, fitted = group.isFitted())
                        if config.getboolean("table", "empty row after group title"):
                            gotoNextRow(fitted = group.isFitted())
                            if config.getboolean("table", "reserve position numbers"):
                                increment += 1
                        for compRange in group:
                            compNumber = compRange.getSpecValue("number")
                            compName = compRange.getSpecValue("name")
                            compDoc = compRange.getSpecValue("doc")
                            name = compName
                            if compDoc:
                                for title in titleLines:
                                    if title.endswith(compDoc):
                                        break
                                else:
                                    name += ' ' + compDoc
                            compRef = compRange.getRefRangeFittedString()
                            compComment = compRange.getSpecValue("comment")
                            comment = compRef
                            if comment:
                                if compComment:
                                    comment = comment + '\n' + compComment
                            else:
                                comment = compComment
                            fillRow(
                                ["", "", "", compNumber, name, str(compRange.lenFitted()), comment],
                                posIncrement=increment,
                                fitted = compRange.isFitted()
                            )
                            increment = 1
                    prevGroup = group

        if config.getboolean("sections", "materials"):
            gotoNextRow()
            fillSectionTitle("Материалы")
            gotoNextRow()
            
        for rowIndex in range(len(table)):
            table[rowIndex][COL_COMMENT] = table[rowIndex][COL_COMMENT].replace('\n', ', ')
            table[rowIndex][COL_COMMENT] = table[rowIndex][COL_COMMENT].replace('Формованная', 'Формовать')
        
        return table

    except:
        # Ошибка!
        print(
            "При построении возникла ошибка:\n\n" \
            + traceback.format_exc(),
            "Спецификация")
