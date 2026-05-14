from . import schematic, config


def build(netlist, auto_num=True):
    """Построить ведомость покупных изделий.

    Построить ведомость на основе данных из файла списка цепей.

    """
    currentPosition = 1
    COLUMN_COUNT = 11 + 1
    COL_POS = 0
    COL_NAME = 1
    COL_CODE = 2
    COL_DOC = 3
    COL_DEALER = 4
    COL_FOR_WHAT = 5
    COL_QTY_DEVICE = 6
    COL_QTY_ZIP = 7
    COL_QTY_TUNE = 8
    COL_QTY_TOTAL = 9
    COL_COMMENT = 10
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

    def fillSectionTitle(section):
        table[-1][COL_NAME] = section
        table[-1][COL_STYLE] = 'section_title'
        gotoNextRow()

    def fillRow(values, isTitle=False, posIncrement=0):
        nonlocal currentPosition
        if posIncrement and config.getboolean("table", "only components have position numbers"):
            values[COL_POS] = str(currentPosition)
            currentPosition += posIncrement
        table[-1] = pad_or_truncate(values, COLUMN_COUNT)
        if isTitle:
            table[-1][COL_STYLE] = 'title'
        gotoNextRow()

    # --------------------------------------------------------------------
    # Начало построения таблицы
    # --------------------------------------------------------------------
    sch = schematic.Schematic(netlist, auto_num=auto_num)
    if sch is None:
        return
    compGroups = sch.getSuperGroupedComponentsBom()
    prevGroup = None
    emptyRowsType = config.getint("table", "empty rows between diff type")
    classtitle = ''

    gotoNextRow()

    for classgroup in compGroups:
        if config.getboolean('table', 'put class header'):
            increment = 1
            if prevGroup is not None:
                gotoNextRow(emptyRowsType)
                if config.getboolean("table", "reserve position numbers"):
                    increment += emptyRowsType
            classtitle = classgroup[0][0].getBomValue('class', plural=True)
            fillRow(['', classtitle], isTitle=True)
            if config.getboolean('table', 'empty row after class title'):
                gotoNextRow()
            prevGroup = None
        for group in classgroup:
            increment = 1
            if prevGroup is not None:
                gotoNextRow(emptyRowsType)
                if config.getboolean("table", "reserve position numbers"):
                    increment += emptyRowsType
            if len(group) == 1 \
                    and not config.getboolean("table", "every group has title"):
                compType = group[0].getBomValue("type", singular=True)
                compName = group[0].getBomValue("name")
                compCode = group[0].getBomValue("code")
                compDoc = group[0].getBomValue("doc")
                compDealer = group[0].getBomValue("dealer")
                compForWhat = group[0].getBomValue("for what")
                compComment = group[0].getBomValue("comment")
                name = ""
                if compType:
                    name += compType + ' '
                name += compName
                compCount = str(len(group[0]))
                fillRow(
                    ["", name, compCode, compDoc, compDealer, compForWhat, compCount, "", "", compCount, compComment],
                    posIncrement=increment
                )
            else:
                title = group[0].getBomValue("type", plural=True)
                if title and title != classtitle:
                    fillRow(
                        ["", title],
                        isTitle=True
                    )
                if config.getboolean("table", "empty row after group title"):
                    gotoNextRow()
                    if config.getboolean("table", "reserve position numbers"):
                        increment += 1
                for compRange in group:
                    compName = compRange.getBomValue("name")
                    compCode = compRange.getBomValue("code")
                    compDoc = compRange.getBomValue("doc")
                    compDealer = compRange.getBomValue("dealer")
                    if config.get("fields_bom", "for what") == "_Designator":
                        compForWhat = compRange.getRefRangeString()
                    else:
                        compForWhat = compRange.getBomValue("for what")
                    compComment = compRange.getBomValue("comment")
                    compCount = str(len(compRange))
                    fillRow(
                        ["", compName, compCode, compDoc, compDealer, compForWhat, compCount, "", "", compCount,
                         compComment],
                        posIncrement=increment
                    )
                    increment = 1
            prevGroup = group

    if not config.getboolean("table", "only components have position numbers"):
        for rowIndex in range(len(table)):
            table[rowIndex][0] = str(rowIndex + 1)

    if config.getboolean("table", "process repeated values"):
        prevValues = [""] * COLUMN_COUNT
        repeatCount = [0] * COLUMN_COUNT
        for rowIndex in range(1, len(table)):
            for colIndex in (2, 3, 4, 5, 10):
                if table[rowIndex][colIndex] == prevValues[colIndex] and table[rowIndex][colIndex] != "":
                    repeatCount[colIndex] += 1
                    if repeatCount[colIndex] == 1:
                        table[rowIndex][colIndex] = "То же"
                    elif repeatCount[colIndex] > 1:
                        table[rowIndex][colIndex] = '»'
                else:
                    prevValues[colIndex] = table[rowIndex][colIndex]
                    repeatCount[colIndex] = 0

    for rowIndex in range(len(table)):
        table[rowIndex][10] = table[rowIndex][10].replace('Формованная', 'Формовать')

    return table