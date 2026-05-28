"""Объектное представление схемы."""

import re
import sys

from . import altiumbom, config

REF_REGEXP = re.compile(r"([^0-9?]+)([0-9]+)")

class Component():
    """Данные о компоненте схемы."""

    multipliersDict = {
        'G': 'Г',
        'M': 'М',
        'k': 'к',
        'm': 'м',
        'μ': 'мк',
        'u': 'мк',
        'U': 'мк',
        'n': 'н',
        'p': 'п'
    }
    multipliers = set(list(multipliersDict.keys()) + list(multipliersDict.values()))
    # 2u7, 2н7, 4m7, 5k1 ...
    regexpr1 = re.compile(
        r"^(\d+)({})(\d+)$".format('|'.join(multipliers))
    )
    # 2.7 u, 2700p, 4.7 m, 470u, 5.1 k, 510 ...
    regexpr2 = re.compile(
        r"^(\d+(?:[\.,]\d+)?)\s*({})?$".format('|'.join(multipliers))
    )

    def __init__(self, schematic):
        self.schematic = schematic
        self.reference = ""
        self.value = ""
        self.fitted = True
        self.footprint = ""
        self.datasheet = ""
        self.fields = {}

    def getFieldValue(self, name):
        """Вернуть значение поля с указанным именем."""
        value = None
        if name == "Обозначение":
            value = self.reference
        elif name == "_Value":
            if config.getboolean("table", "add units"):
                value = self.getValueWithUnits()
            else:
                value = self.value
        elif name == "_Footprint":
            value = self.footprint
        elif name == "_Datasheet":
            value = self.datasheet
        elif name in self.fields:
            value = self.fields[name]
        if value:
            value = self.formatPattern(value)
        return value

    def getRefType(self, ref=None):
        """Вернуть буквенную часть обозначения."""
        if ref is None:
            ref = self.reference
        if not re.match(REF_REGEXP, ref):
            raise ValueError(f"Обозначение '{ref}' не соответствует формату (должно содержать буквенную часть и число), включите автонумерацию или изменить обозначение вручную")
        refType = re.search(REF_REGEXP, ref).group(1)
        return refType

    def getRefNumber(self, ref=None):
        """Вернуть цифровую часть обозначения."""
        if ref is None:
            ref = self.reference
        if not re.match(REF_REGEXP, ref):
            return None
        refNumber = re.search(REF_REGEXP, ref).group(2)
        return int(refNumber)

    def _convertSingularPlural(self, value, singular, plural):
        """Привести переданное значение к единственному либо множественному числу.

        Если параметр plural==True, то значение поля будет указано в
        множественном числе.
        Если параметр singular==True, то значение поля будет указано в
        единственном числе.
        Если значение поля имеет формат:
        значение 1 {значение 2}
        то "значение 1" воспринимается как значение поля в единственном числе,
        а "значение 2" - как значение в множественном числе.
        Если значение поля не соответствует указанному формату, то это значение
        будет использоваться полностью как в единственном, так и в
        множественном числе.

        Аргументы:
        value (str) -- значение поля, которое необходимо обработать;
        singular (boolean) -- привести к единственному числу;
        plural (boolean) -- привести к множественному числу.

        Возвращаемое значение (str) -- преобразованное значение.

        """

        if value and (singular or plural):
            valueSingularAndPlural = re.match(r"^(.+)\s\{(.+)\}$", value)
            if valueSingularAndPlural:
                if singular:
                    value = valueSingularAndPlural.group(1)
                elif plural:
                    value = valueSingularAndPlural.group(2)
            elif self.schematic.typeNamesDict:
                for item in iter(self.schematic.typeNamesDict.items()):
                    if value in item:
                        if singular:
                            value = item[0]
                        elif plural:
                            value = item[1]
        return value

    def getValueWithUnits(self):
        """Преобразовать значение к стандартному виду.

        Возвращаемое значение -- значение элемента, приведённое к
            стандартному виду, например:
            2u7 -> 2,7 мкФ

        """
        numValue = ""
        separator = ""
        if config.getboolean("table", "space before units"):
            separator = ' '
        multiplier = ""
        units = ""
        if self.getRefType().startswith('C') \
            and not self.value.endswith('Ф'):
                units = 'Ф'
                if re.match(r"^\d+$", self.value):
                    numValue = self.value
                    multiplier = 'п'
                elif re.match(r"^\d+[\.,]\d+$", self.value):
                    numValue = self.value
                    multiplier = "п"
                else:
                    numValue = self.value.rstrip('F')
                    numValue = numValue.strip()
                    if re.match(Component.regexpr1, numValue):
                        searchRes = re.search(Component.regexpr1, numValue).groups()
                        numValue = "{},{}".format(searchRes[0], searchRes[2])
                        multiplier = searchRes[1]
                    elif re.match(Component.regexpr2, numValue):
                        searchRes = re.search(Component.regexpr2, numValue).groups()
                        numValue = searchRes[0]
                        multiplier = searchRes[1]
                    else:
                        numValue = ""
        elif self.getRefType().startswith('L') \
            and not self.value.endswith("Гн"):
                units = "Гн"
                numValue = self.value.rstrip('H')
                numValue = numValue.strip()
                if re.match(Component.regexpr1, numValue):
                    searchRes = re.search(Component.regexpr1, numValue).groups()
                    numValue = "{},{}".format(searchRes[0], searchRes[2])
                    multiplier = searchRes[1]
                elif re.match(Component.regexpr2, numValue):
                    searchRes = re.search(Component.regexpr2, numValue).groups()
                    numValue = searchRes[0]
                    if searchRes[1] is None:
                        multiplier = "мк"
                    else:
                        multiplier = searchRes[1]
                else:
                    numValue = ""
        elif self.getRefType().startswith('R') \
            and not self.value.endswith("Ом"):
                units = "Ом"
                numValue = self.value.rstrip('Ω')
                if numValue.endswith("Ohm") or numValue.endswith("ohm"):
                    numValue = numValue[:-3]
                numValue = numValue.strip()
                if re.match(r"R\d+", numValue):
                    numValue = numValue.replace('R', "0,")
                elif re.match(r"\d+R\d+", numValue):
                    numValue = numValue.replace('R', ',')
                elif re.match(Component.regexpr1, numValue):
                    searchRes = re.search(Component.regexpr1, numValue).groups()
                    numValue = "{},{}".format(searchRes[0], searchRes[2])
                    multiplier = searchRes[1]
                elif re.match(Component.regexpr2, numValue):
                    searchRes = re.search(Component.regexpr2, numValue).groups()
                    numValue = searchRes[0]
                    if searchRes[1] is not None:
                        multiplier = searchRes[1]
                else:
                    numValue = ""
        if numValue:
            # Перевести множитель на русский
            if multiplier in Component.multipliersDict:
                multiplier = Component.multipliersDict[multiplier]
            elif multiplier is None:
                multiplier = ''
            numValue = numValue.replace('.', ',')
            return numValue + separator + multiplier + units
        return self.value

    def formatPattern(self, pattern, check=False, singular=False, plural=False):
        """Преобразовать шаблон.

        Шаблон представляет собой строку текста, в которой конструкции типа:

        ${НаименованиеПоля}
        ${Префикс|НаименованиеПоля|Суффикс}

        будут преобразованы в текст вида:

        ЗначениеПоля
        ПрефиксЗначениеПоляСуффикс

        Например:
        "МЛТ-0,5-${_Value}${-|Класс точности|}-В" -> "МЛТ-0,5-4,7кОм-±5%-В"
        Если значение поля пусто или указанного поля нет в компоненте, то
        соответствующий элемент шаблона удаляется. Если, допустим, для
        приведённого выше примера, в компоненте нет поля "Класс точности", то
        результат будет следующим:
        "МЛТ-0,5-4,7кОм-В" (префикс '-' тоже отсутствует)

        Символы '{', '|', '}' имеют специальное назначение. Если в шаблоне
        требуется указать эти символы, то их нужно экранировать символом
        обратной косой черты ' \ ', например:
        "Обозначение компонента ${\{|Обозначение|\}} в фигурных скобках."
        Но спец. символы вне конструкции ${} экранировать не нужно:
        "Обозначение компонента {${Обозначение}} в фигурных скобках."

        Если параметр check==True, то вместо преобразования строки будет
        выполнена проверка - является ли переданная строка шаблоном. При первом
        обнаружении конструкции ${} будет возвращено значение True, при
        отсутствии такой конструкции - False.

        Аргументы:
        pattern (str) -- строка текста, которую следует обработать как шаблон;
        check (boolean) -- проверить шаблон без преобразования;
        singular (boolean) -- привести к единственному числу;
        plural (boolean) -- привести к множественному числу.

        Возвращаемое значение (str) -- преобразованное значение.

        """
        out = ""
        prefix = ""
        fieldName = ""
        suffix = ""
        temp = ""

        # Флаг, указывающий на то, что спец.символ нужно обработать как обычный
        ignore = False
        # Флаг, указывающий на обрабатываемую часть подстановки.
        substitution = ""

        def resetSubstitution():
            nonlocal out, temp, substitution, prefix, fieldName, suffix
            out += temp
            substitution = temp = ""
            prefix = fieldName = suffix = ""

        for char in pattern:
            if char == '\\' and substitution and not ignore:
                    ignore = True
                    temp += char
                    continue
            elif substitution:
                temp += char
                if substitution == "beginning":
                    if char == '{' and not ignore:
                        substitution = "prefix"
                    else:
                        out += temp
                        substitution = temp = ""
                elif char == '{' and not ignore:
                    # Конструкция ${} имеет неверный формат:
                    # ${...{
                    #      ^
                    # открывающаяся фигурная скобка внутри подстановки.
                    resetSubstitution()
                elif char == '|' and substitution == "prefix" and not ignore:
                    substitution = "fieldName"
                elif char == '|' and substitution == "fieldName" and not ignore:
                    substitution = "suffix"
                elif char == '|' and substitution == "suffix" and not ignore:
                    # Конструкция ${} имеет неверный формат:
                    # ${prefix|fieldName|suffix|
                    #                          ^
                    # третья вертикальная черта внутри подстановки.
                    resetSubstitution()
                elif char == "}" and not ignore:
                    if substitution == "fieldName":
                        # Конструкция ${} имеет неверный формат:
                        # ${prefix|fieldName}
                        #                   ^
                        # одна вертикальная черта в подстановке. Должно быть
                        # либо две (для пефикса/суффикса), либо не быть вовсе.
                        resetSubstitution()
                    else:
                        if substitution == "prefix":
                            # Если по завершении конструкции ${} имеется только
                            # префикс, значит найдена сокращённая конструкция
                            # (без префикса/суффикса).
                            fieldName = prefix
                            prefix = ""
                        if check:
                            return True
                        fieldValue = self.getFieldValue(fieldName)
                        if fieldValue:
                            fieldValue = self._convertSingularPlural(fieldValue, singular, plural)
                            out += prefix + fieldValue + suffix
                    substitution = temp = prefix = fieldName = suffix = ""
                elif substitution == "prefix":
                    prefix += char
                elif substitution == "fieldName":
                    fieldName += char
                elif substitution == "suffix":
                    suffix += char
            elif char == '$':
                substitution = "beginning"
                temp += char
            else:
                out += char
            ignore = False
        if substitution:
            # Конструкция ${} неожиданно закончилась.
            resetSubstitution()
        if check:
            return False
        return out

    def getIndexValue(self, name, singular=False, plural=False):
        """Вернуть преобразованное значение для перечня.

        Вернуть приведённое к конечному виду значение одного из полей,
        используемых при построении перечня.

        Аргументы:
        name (str) -- название требуемого значения; может быть одним из:
            "class", "type", "name", "doc", "comment";
        singular (boolean) -- привести к единственному числу;
        plural (boolean) -- привести к множественному числу.

        Возвращаемое значение (str) -- итоговое значение.

        """
        if name not in ("class", "type", "name", "doc", "comment"):
            return ""
        fieldName = config.get("fields_index", name)
        value = ""
        if self.formatPattern(fieldName, check=True):
            value = self.formatPattern(fieldName, singular=singular, plural=plural).rstrip().rstrip(',')
        else:
            value = self.getFieldValue(fieldName)
            value = self._convertSingularPlural(value, singular, plural)
        if name == "name" and not value:
            if config.getboolean("table", "add units"):
                value = self.getValueWithUnits()
            else:
                value = self.value

        if name == "name":
            # Попробуем получить PartNumber
            partnumber = self.getFieldValue("PartNumber")
            if partnumber:
                value = partnumber
            else:
                # Если PartNumber пуст, берём Comment
                comment = self.getFieldValue("Comment")
                value = comment if comment else ""

        if value is None:
            value = ""
        return value
    
    def getSpecValue(self, name, singular=False, plural=False):
        """Вернуть преобразованное значение для спецификации.

        Вернуть приведённое к конечному виду значение одного из полей,
        используемых при построении спецификации.

        Аргументы:
        name (str) -- название требуемого значения; может быть одним из:
            "class", "type", "number", "name", "doc", "comment";
        singular (boolean) -- привести к единственному числу;
        plural (boolean) -- привести к множественному числу.

        Возвращаемое значение (str) -- итоговое значение.

        """
        if name not in ("class", "type", "number", "name", "doc", "comment"):
            return ""
        fieldName = config.get("fields_spec", name)
        value = ""
        if self.formatPattern(fieldName, check=True):
            value = self.formatPattern(fieldName, singular=singular, plural=plural).rstrip().rstrip(',')
        else:
            value = self.getFieldValue(fieldName)
            value = self._convertSingularPlural(value, singular, plural)
        if name == "name" and not value:
            if config.getboolean("table", "add units"):
                value = self.getValueWithUnits()
            else:
                value = self.value
        if value is None:
            value = ""
        return value

    def getBomValue(self, name, singular=False, plural=False):
        """Вернуть преобразованное значение для ведомости покупных изделий.

        Вернуть приведённое к конечному виду значение одного из полей,
        используемых при построении ведомости.

        Аргументы:
        name (str) -- название требуемого значения; может быть одним из:
            "class", "type", "name", "code", "doc", "dealer", "for what", "comment";
        singular (boolean) -- привести к единственному числу;
        plural (boolean) -- привести к множественному числу.

        Возвращаемое значение (str) -- итоговое значение.

        """
        if name not in ("class", "type", "name", "code", "doc", "dealer", "for what", "comment"):
            return ""
        fieldName = config.get("fields_bom", name)
        value = ""
        if self.formatPattern(fieldName, check=True):
            value = self.formatPattern(fieldName, singular=singular, plural=plural).rstrip().rstrip(',')
        else:
            value = self.getFieldValue(fieldName)
            value = self._convertSingularPlural(value, singular, plural)
        if name == "name" and not value:
            if config.getboolean("table", "add units"):
                value = self.getValueWithUnits()
            else:
                value = self.value
        if value is None:
            value = ""
        return value
    
    def getSdsValue(self, name, singular=False, plural=False):
        """Вернуть преобразованное значение для SDS Компэл.

        Вернуть приведённое к конечному виду значение одного из полей,
        используемых при построении спецификации.

        Аргументы:
        name (str) -- название требуемого значения; может быть одним из:
            "number", "vendor", "comment";
        singular (boolean) -- привести к единственному числу;
        plural (boolean) -- привести к множественному числу.

        Возвращаемое значение (str) -- итоговое значение.

        """
        if name not in ("number", "vendor", "comment"):
            return ""
        fieldName = config.get("fields_sds", name)
        value = ""
        if self.formatPattern(fieldName, check=True):
            value = self.formatPattern(fieldName, singular=singular, plural=plural).rstrip().rstrip(',')
        else:
            value = self.getFieldValue(fieldName)
            value = self._convertSingularPlural(value, singular, plural)        
        if value is None:
            value = ""
        return value
    
    def getExpandedValue(self):
        """Вернуть значение без множителя.

        Если компонент имеет значение физического характера (сопротивление,
        ёмкость, индуктивность), то будет возвращено абсолютное значение с
        учётом указанного множителя, например:
        1к5 => 1500
        0u33 => 0.00000033
        120 => 120
        и т.п.

        Возвращаемое значение (float) -- абсолютное значение.

        """
        extValue = float("inf")
        multiplierValues = {
            'G': 1e9,
            'Г': 1e9,
            'M': 1e6,
            'М': 1e6,
            'k': 1e3,
            'к': 1e3,
            'm': 1e-3,
            'м': 1e-3,
            'μ': 1e-6,
            'u': 1e-6,
            'U': 1e-6,
            'мк': 1e-6,
            'n': 1e-9,
            'н': 1e-9,
            'p': 1e-12,
            'п': 1e-12,
            None: 1
        }
        if self.getRefType().startswith('C'):
            value = self.value
            value = value.rstrip('F')
            value = value.rstrip('Ф')
            value = value.strip()
            if re.match(r"^\d+$", value):
                extValue = float(value) * 1e-12
            elif re.match(r"^\d+[\.,]\d+$", value):
                extValue = float(value.replace(',', '.')) * 1e-6
            elif re.match(Component.regexpr1, value):
                searchRes = re.search(Component.regexpr1, value).groups()
                numValue = "{}.{}".format(searchRes[0], searchRes[2])
                multiplier = multiplierValues[searchRes[1]]
                extValue = float(numValue) * multiplier
            elif re.match(Component.regexpr2, value):
                searchRes = re.search(Component.regexpr2, value).groups()
                numValue = searchRes[0]
                multiplier = multiplierValues[searchRes[1]]
                extValue = float(numValue.replace(',', '.')) * multiplier
        elif self.getRefType().startswith('L'):
            value = self.value
            value = value.rstrip('H')
            value = value.replace("Гн", "")
            value = value.strip()
            if re.match(r"^\d+(?:[\.,]\d+)?$", value):
                extValue = float(value.replace(',', '.')) * 1e-6
            elif re.match(Component.regexpr1, value):
                searchRes = re.search(Component.regexpr1, value).groups()
                numValue = "{}.{}".format(searchRes[0], searchRes[2])
                multiplier = multiplierValues[searchRes[1]]
                extValue = float(numValue) * multiplier
            elif re.match(Component.regexpr2, value):
                searchRes = re.search(Component.regexpr2, value).groups()
                numValue = searchRes[0]
                multiplier = multiplierValues[searchRes[1]]
                extValue = float(numValue.replace(',', '.')) * multiplier
        elif self.getRefType().startswith('R'):
            value = self.value
            value = value.rstrip('Ω')
            value = value.replace("Ом", "")
            value = value.replace("ohm", "")
            value = value.replace("Ohm", "")
            value = value.strip()
            if re.match(r"R\d+", value):
                numValue = value.replace('R', "0.")
                extValue = float(numValue)
            elif re.match(r"\d+R\d+", value):
                numValue = value.replace('R', ".")
                extValue = float(numValue)
            elif re.match(Component.regexpr1, value):
                searchRes = re.search(Component.regexpr1, value).groups()
                numValue = "{}.{}".format(searchRes[0], searchRes[2])
                multiplier = multiplierValues[searchRes[1]]
                extValue = float(numValue) * multiplier
            elif re.match(Component.regexpr2, value):
                searchRes = re.search(Component.regexpr2, value).groups()
                numValue = searchRes[0]
                if searchRes[1] is not None:
                    multiplier = multiplierValues[searchRes[1]]
                else:
                    multiplier = 1
                extValue = float(numValue.replace(',', '.')) * multiplier

        return extValue

class CompRangeIndex(Component):
    """Множество компонентов с одинаковыми параметрами.

    Этот класс описывает множество компонентов перечня
    элементов, которые имеют одинаковые тип, наименование, документ,
    примечание, буквенную часть обозначения и следуют последовательно.

    """

    def __init__(self, schematic, comp=None):
        Component.__init__(self, schematic)
        self._refRange = []
        self._refRangeFitted = []
        if comp is not None:
            self._refRange.append(comp.reference)
            if comp.fitted:
                self._refRangeFitted.append(comp.reference)
            self.reference = comp.reference
            self.value = comp.value
            self.footprint = comp.footprint
            self.datasheet = comp.datasheet
            self.fields = comp.fields

    def __iter__(self):
        for ref in self._refRange:
            yield ref

    def __len__(self):
        return len(self._refRange)
    
    def lenFitted(self):
        return len(self._refRangeFitted)
    
    def isFitted(self):
        return True if self.lenFitted() > 0 else False

    def append(self, comp):
        """Добавить новый компонент.

        Добавить компонент в множество одинаковых компонентов.
        Если компонент отличается от имеющихся, то он не будет добавлен.

        Аргументы:
        comp (Component) -- компонент, который необходимо добавить.

        Возвращаемые значения (boolean) -- True - если компонент был добавлен,
            False - в противном случае.

        """
        if not self._refRange:
            self.__init__(self.schematic, comp)
            return True
        if self.getRefType() == comp.getRefType() \
            and self.getIndexValue("type") == comp.getIndexValue("type") \
            and self.getIndexValue("name") == comp.getIndexValue("name") \
            and self.getIndexValue("doc") == comp.getIndexValue("doc") \
            and self.getIndexValue("comment") == comp.getIndexValue("comment"):
                self._refRange.append(comp.reference)
                if comp.fitted:
                    self._refRangeFitted.append(comp.reference)
                return True
        return False

    def getRefRangeString(self):
        """Вернуть перечень обозначений множества одинаковых компонентов."""
        refStr = ""
        adjustable = False
        adjustableField = config.get("fields", "adjustable")
        if self.getFieldValue(adjustableField) is not None:
            adjustable = True
        if len(self._refRange) > 1:
            # "VD1, VD2", "C8-C11", "R7, R9-R14", "C8*-C11*" ...
            prevType = self.getRefType(self._refRange[0])
            prevNumber = self.getRefNumber(self._refRange[0])
            counter = 0
            separator = ", "
            refStr = prevType + str(prevNumber)
            if adjustable:
                refStr += '*'
            for nextRef in self._refRange[1:]:
                currentType = self.getRefType(nextRef)
                currentNumber = self.getRefNumber(nextRef)
                if currentType == prevType \
                    and currentNumber == (prevNumber + 1):
                        prevNumber = currentNumber
                        counter += 1
                        if counter > 1:
                            separator = config.get("table", "ref separator")
                        continue
                else:
                    if counter > 0:
                        refStr += separator + prevType + str(prevNumber)
                        if adjustable:
                            refStr += '*'
                    separator = ', '
                    refStr += separator + currentType + str(currentNumber)
                    if adjustable:
                        refStr += '*'
                    prevType = currentType
                    prevNumber = currentNumber
                    counter = 0
            if counter > 0:
                refStr += separator + prevType + str(prevNumber)
                if adjustable:
                    refStr += '*'
        else:
            # "R5"; "VT13" ...
            refStr = self.reference
            if adjustable:
                refStr += '*'
        return refStr
    
    def getRefRangeFittedString(self):
        """Вернуть перечень обозначений множества одинаковых компонентов."""
        refStr = ""
        adjustable = False
        adjustableField = config.get("fields", "adjustable")
        if self.getFieldValue(adjustableField) is not None:
            adjustable = True
        if len(self._refRangeFitted) > 1:
            # "VD1, VD2", "C8-C11", "R7, R9-R14", "C8*-C11*" ...
            prevType = self.getRefType(self._refRangeFitted[0])
            prevNumber = self.getRefNumber(self._refRangeFitted[0])
            counter = 0
            separator = ", "
            refStr = prevType + str(prevNumber)
            if adjustable:
                refStr += '*'
            for nextRef in self._refRangeFitted[1:]:
                currentType = self.getRefType(nextRef)
                currentNumber = self.getRefNumber(nextRef)
                if currentType == prevType \
                    and currentNumber == (prevNumber + 1):
                        prevNumber = currentNumber
                        counter += 1
                        if counter > 1:
                            separator = config.get("table", "ref separator")
                        continue
                else:
                    if counter > 0:
                        refStr += separator + prevType + str(prevNumber)
                        if adjustable:
                            refStr += '*'
                    separator = ', '
                    refStr += separator + currentType + str(currentNumber)
                    if adjustable:
                        refStr += '*'
                    prevType = currentType
                    prevNumber = currentNumber
                    counter = 0
            if counter > 0:
                refStr += separator + prevType + str(prevNumber)
                if adjustable:
                    refStr += '*'
        else:
            # "R5"; "VT13" ...
            refStr = self.reference
            if adjustable:
                refStr += '*'
        return refStr

class CompRangeSpec(Component):
    """Множество компонентов с одинаковыми параметрами.

    Этот класс описывает множество компонентов спецификации, которые
    имеют одинаковые тип, наименование, документ и примечание
    (отличаются только обозначением).

    """

    def __init__(self, schematic, comp=None):
        Component.__init__(self, schematic)
        self._refRange = []
        self._refRangeFitted = []
        if comp is not None:
            self._refRange.append(comp.reference)
            if comp.fitted:
                self._refRangeFitted.append(comp.reference)
            self.reference = comp.reference
            self.value = comp.value
            self.footprint = comp.footprint
            self.datasheet = comp.datasheet
            self.fields = comp.fields

    def __iter__(self):
        for ref in self._refRange:
            yield ref

    def __len__(self):
        return len(self._refRange)
    
    def lenFitted(self):
        return len(self._refRangeFitted)
    
    def isFitted(self):
        return True if self.lenFitted() > 0 else False

    def append(self, comp):
        """Добавить новый компонент.

        Добавить компонент в множество одинаковых компонентов.
        Если компонент отличается от имеющихся, то он не будет добавлен.

        Аргументы:
        comp (Component) -- компонент, который необходимо добавить.

        Возвращаемые значения (boolean) -- True - если компонент был добавлен,
            False - в противном случае.

        """
        if not self._refRange:
            self.__init__(self.schematic, comp)
            return True
        if self.getSpecValue("type") == comp.getSpecValue("type") \
            and self.getSpecValue("name") == comp.getSpecValue("name") \
            and self.getSpecValue("doc") == comp.getSpecValue("doc") \
            and self.getSpecValue("comment") == comp.getSpecValue("comment"):
                self._refRange.append(comp.reference)
                if comp.fitted:
                    self._refRangeFitted.append(comp.reference)
                return True
        return False

    def getRefRangeString(self):
        """Вернуть перечень обозначений множества одинаковых компонентов."""
        refStr = ""
        if len(self._refRange) > 1:
            # "VD1, VD2", "C8-C11", "R7, R9-R14" ...
            sortedRanges = sorted(
                self._refRange,
                key=lambda ref: self.getRefNumber(ref)
            )
            sortedRanges = sorted(
                sortedRanges,
                key=lambda ref: self.getRefType(ref)
            )
            prevType = self.getRefType(sortedRanges[0])
            prevNumber = self.getRefNumber(sortedRanges[0])
            counter = 0
            separator = ", "
            refStr = prevType + str(prevNumber)
            for nextRef in sortedRanges[1:]:
                currentType = self.getRefType(nextRef)
                currentNumber = self.getRefNumber(nextRef)
                if currentType == prevType \
                    and currentNumber == (prevNumber + 1):
                        prevNumber = currentNumber
                        counter += 1
                        if counter > 1:
                            separator = config.get("table", "ref separator")
                        continue
                else:
                    if counter > 0:
                        refStr += separator + prevType + str(prevNumber)
                    separator = ', '
                    refStr += separator + currentType + str(currentNumber)
                    prevType = currentType
                    prevNumber = currentNumber
                    counter = 0
            if counter > 0:
                refStr += separator + prevType + str(prevNumber)
        else:
            # "R5"; "VT13" ...
            refStr = self.reference
        return refStr
    
    def getRefRangeFittedString(self):
        """Вернуть перечень обозначений множества одинаковых компонентов."""
        refStr = ""
        if len(self._refRangeFitted) > 1:
            # "VD1, VD2", "C8-C11", "R7, R9-R14" ...
            sortedRanges = sorted(
                self._refRangeFitted,
                key=lambda ref: self.getRefNumber(ref)
            )
            sortedRanges = sorted(
                sortedRanges,
                key=lambda ref: self.getRefType(ref)
            )
            prevType = self.getRefType(sortedRanges[0])
            prevNumber = self.getRefNumber(sortedRanges[0])
            counter = 0
            separator = ", "
            refStr = prevType + str(prevNumber)
            for nextRef in sortedRanges[1:]:
                currentType = self.getRefType(nextRef)
                currentNumber = self.getRefNumber(nextRef)
                if currentType == prevType \
                    and currentNumber == (prevNumber + 1):
                        prevNumber = currentNumber
                        counter += 1
                        if counter > 1:
                            separator = config.get("table", "ref separator")
                        continue
                else:
                    if counter > 0:
                        refStr += separator + prevType + str(prevNumber)
                    separator = ', '
                    refStr += separator + currentType + str(currentNumber)
                    prevType = currentType
                    prevNumber = currentNumber
                    counter = 0
            if counter > 0:
                refStr += separator + prevType + str(prevNumber)
        else:
            if len(self._refRangeFitted) > 0:
                # "R5"; "VT13" ...
                refStr = self.reference
        return refStr

class CompRangeBom(Component):
    """Множество компонентов с одинаковыми параметрами.

    Этот класс описывает множество компонентов ведомости, которые
    имеют одинаковые тип, наименование, документ и примечание
    (отличаются только обозначением).

    """

    def __init__(self, schematic, comp=None):
        Component.__init__(self, schematic)
        self._refRange = []
        self._refRangeFitted = []
        if comp is not None:
            self._refRange.append(comp.reference)
            if comp.fitted:
                self._refRangeFitted.append(comp.reference)
            self.reference = comp.reference
            self.value = comp.value
            self.footprint = comp.footprint
            self.datasheet = comp.datasheet
            self.fields = comp.fields

    def __iter__(self):
        for ref in self._refRange:
            yield ref

    def __len__(self):
        return len(self._refRange)
    
    def lenFitted(self):
        return len(self._refRangeFitted)
    
    def isFitted(self):
        return True if self.lenFitted() > 0 else False

    def append(self, comp):
        """Добавить новый компонент.

        Добавить компонент в множество одинаковых компонентов.
        Если компонент отличается от имеющихся, то он не будет добавлен.

        Аргументы:
        comp (Component) -- компонент, который необходимо добавить.

        Возвращаемые значения (boolean) -- True - если компонент был добавлен,
            False - в противном случае.

        """
        if not self._refRange:
            self.__init__(self.schematic, comp)
            return True
        if self.getBomValue("type") == comp.getBomValue("type") \
            and self.getBomValue("name") == comp.getBomValue("name") \
            and self.getBomValue("doc") == comp.getBomValue("doc") \
            and self.getBomValue("comment") == comp.getBomValue("comment"):
                self._refRange.append(comp.reference)
                if comp.fitted:
                    self._refRangeFitted.append(comp.reference)
                return True
        return False

    def getRefRangeString(self):
        """Вернуть перечень обозначений множества одинаковых компонентов."""
        refStr = ""
        if len(self._refRange) > 1:
            # "VD1, VD2", "C8-C11", "R7, R9-R14" ...
            sortedRanges = sorted(
                self._refRange,
                key=lambda ref: self.getRefNumber(ref)
            )
            sortedRanges = sorted(
                sortedRanges,
                key=lambda ref: self.getRefType(ref)
            )
            prevType = self.getRefType(sortedRanges[0])
            prevNumber = self.getRefNumber(sortedRanges[0])
            counter = 0
            separator = ", "
            refStr = prevType + str(prevNumber)
            for nextRef in sortedRanges[1:]:
                currentType = self.getRefType(nextRef)
                currentNumber = self.getRefNumber(nextRef)
                if currentType == prevType \
                    and currentNumber == (prevNumber + 1):
                        prevNumber = currentNumber
                        counter += 1
                        if counter > 1:
                            separator = config.get("table", "ref separator")
                        continue
                else:
                    if counter > 0:
                        refStr += separator + prevType + str(prevNumber)
                    separator = ', '
                    refStr += separator + currentType + str(currentNumber)
                    prevType = currentType
                    prevNumber = currentNumber
                    counter = 0
            if counter > 0:
                refStr += separator + prevType + str(prevNumber)
        else:
            # "R5"; "VT13" ...
            refStr = self.reference
        return refStr
    
    def getRefRangeFittedString(self):
        """Вернуть перечень обозначений множества одинаковых компонентов."""
        refStr = ""
        if len(self._refRangeFitted) > 1:
            # "VD1, VD2", "C8-C11", "R7, R9-R14" ...
            sortedRanges = sorted(
                self._refRangeFitted,
                key=lambda ref: self.getRefNumber(ref)
            )
            sortedRanges = sorted(
                sortedRanges,
                key=lambda ref: self.getRefType(ref)
            )
            prevType = self.getRefType(sortedRanges[0])
            prevNumber = self.getRefNumber(sortedRanges[0])
            counter = 0
            separator = ", "
            refStr = prevType + str(prevNumber)
            for nextRef in sortedRanges[1:]:
                currentType = self.getRefType(nextRef)
                currentNumber = self.getRefNumber(nextRef)
                if currentType == prevType \
                    and currentNumber == (prevNumber + 1):
                        prevNumber = currentNumber
                        counter += 1
                        if counter > 1:
                            separator = config.get("table", "ref separator")
                        continue
                else:
                    if counter > 0:
                        refStr += separator + prevType + str(prevNumber)
                    separator = ', '
                    refStr += separator + currentType + str(currentNumber)
                    prevType = currentType
                    prevNumber = currentNumber
                    counter = 0
            if counter > 0:
                refStr += separator + prevType + str(prevNumber)
        else:
            # "R5"; "VT13" ...
            refStr = self.reference
        return refStr

class CompGroupIndex():
    """Группа компонентов.

    Группой считается множество CompRange, которые имеют однотипные
    обозначения (например: R, C, DA и т.д.) и имеют одинаковый "Тип".

    Если установлен параметр "concatenate same name groups", то
    группы, идущие подряд и имеющие одинаковое наименование типа, но
    отличающиеся обозначением - будут объединены. Например, компоненты типа
    "Разъём (Разъёмы)", но с обозначениями "XP..." и "XS...", по умолчанию
    формируют две отдельные группы с одинаковым заголовком. Но, с помощью выше
    указанного параметра, эти группы могут быть объединены в одну.

    """

    def __init__(self, schematic, compRange=None):
        self.schematic = schematic
        self._compRanges = []
        self._compRangesFitted = []
        if compRange is not None:
            self._compRanges.append(compRange)
            if compRange.isFitted():
                self._compRangesFitted.append(compRange)

    def __iter__(self):
        for compRange in self._compRanges:
            yield compRange

    def __getitem__(self, key):
        return self._compRanges[key]

    def __len__(self):
        return len(self._compRanges)
    
    def lenFitted(self):
        return len(self._compRangesFitted)

    def isFitted(self):
        return True if len(self._compRangesFitted) > 0 else False

    def append(self, compRange):
        """Добавить множество компонентов в группу.

        Аргументы:
        compRange (CompRange) -- множество компонентов, которое необходимо
            добавить в группу.

        Возвращаемые значения (boolean) -- True - если множество было
            добавлено, False - в противном случае.

        """
        if not self._compRanges:
            self._compRanges.append(compRange)
            if compRange.isFitted():
                self._compRangesFitted.append(compRange)
            return True
        skipRefType = config.getboolean("table", "concatenate same name groups")
        lastCompRange = self._compRanges[-1]
        if (lastCompRange.getRefType() == compRange.getRefType() or skipRefType) \
            and lastCompRange.getIndexValue("type") == compRange.getIndexValue("type"):
                self._compRanges.append(compRange)
                if compRange.isFitted():
                    self._compRangesFitted.append(compRange)
                return True
        return False

    @staticmethod
    def _strCommon(str1, str2):
        """Определить общее начало двух строк.

        Вернуть подстроку, с которой начинаются обе указанные строки.

        Аргументы:
        str1 (str) -- первая строка;
        str2 (str) -- вторая строка.

        Возвращаемое значение (str) -- общее начало двух строк.

        """
        for i in range(len(str1)):
            if i == len(str2) or str1[i] != str2[i]:
                return str1[:i]
        return str1

    def getTitle(self):
        """Вернуть заголовок группы компонентов.

        По умолчанию, заголовком является "Тип" компонента.
        Если установлен параметр "title with doc", то после "Типа", через
        пробел, будет указан "Документ".
        Если "Документы" компонентов группы отличаются, то заголовок будет
        состоять из нескольких строк, каждая из которых служит для отдельного
        документа. При этом перед каждым документом будет указана часть
        наименования для идентификации компонентов.

        Возвращаемое значение (list) -- список строк заголовка.

        """
        if len(self) == 0:
            return []

        currentType = self._compRanges[0].getIndexValue("type", plural=True)

        if not config.getboolean("table", "title with doc"):
            return [currentType]

        currentName = self._compRanges[0].getIndexValue("name")
        currentDoc = self._compRanges[0].getIndexValue("doc")

        # Список уникальных пар Наименование-Документ
        nameDocList = []
        for compRange in self:
            currentName = compRange.getIndexValue("name")
            currentDoc = compRange.getIndexValue("doc")
            if not currentDoc:
                # Если имеются компоненты, в которых документ не указан,
                # то в заголовке для них будет указан только тип.
                currentName = ""
            for i in range(len(nameDocList)):
                savedName = nameDocList[i][0]
                savedDoc = nameDocList[i][1]
                if savedDoc == currentDoc:
                    commonName = self._strCommon(savedName, currentName)
                    commonName = commonName.rstrip(" -")
                    if commonName:
                        # Оставить только общую часть наименования
                        nameDocList[i][0] = commonName
                        break
            else:
                nameDocList.append([currentName, currentDoc])

        # Максимально сократить наименования, оставив только часть
        # достаточную для идентификации.
        for i in range(len(nameDocList)):
            name = nameDocList[i][0]
            doc = nameDocList[i][1]
            nameParts = re.findall(r"([-\s]?[^-\s]+)", name)
            if len(nameParts) > 1:
                for j in range(1, len(nameParts)):
                    shortName = "".join(nameParts[:j])
                    if [shortName, doc] not in nameDocList:
                        nameDocList[i][0] = shortName
                        break

        # Сформировать наименование
        if not nameDocList:
            return [currentType]
        firstDoc = nameDocList[0][-1]
        for name, doc in nameDocList:
            if doc != firstDoc:
                break
        else:
            # У всех компонентов один документ
            title = currentType
            if title:
                title += ' '
            title += firstDoc
            return [title]
        groupNames = []
        nameDocList.sort(key=lambda nameDoc: nameDoc[0])
        for nameDoc in nameDocList:
            name = currentType
            if nameDoc[0]:
                if name:
                    name += ' '
                name += nameDoc[0]
            if nameDoc[1]:
                if name:
                    name += ' '
                name += nameDoc[1]
            groupNames.append(name)

        return groupNames

class CompGroupSpec():
    """Группа компонентов.

    Группой считается множество CompRange, которые имеют одинаковый тип.
    Если установлен параметр "separate group for each doc", то компоненты
    будут разбиваться на группы не только по типу, но и по документу.

    """

    def __init__(self, schematic, compRange=None):
        self.schematic = schematic
        self._compRanges = []
        self._compRangesFitted = []
        if compRange is not None:
            self._compRanges.append(compRange)
            if compRange.isFitted():
                self._compRangesFitted.append(compRange)

    def __iter__(self):
        for compRange in self._compRanges:
            yield compRange

    def __getitem__(self, key):
        return self._compRanges[key]

    def __len__(self):
        return len(self._compRanges)

    def lenFitted(self):
        return len(self._compRangesFitted)

    def isFitted(self):
        return True if len(self._compRangesFitted) > 0 else False

    def sort(self, key=None):
        self._compRanges.sort(key=key)

    def append(self, compRange):
        """Добавить множество компонентов в группу.

        Аргументы:
        compRange (CompRange) -- множество компонентов, которое необходимо
            добавить в группу.

        Возвращаемые значения (boolean) -- True - если множество было
            добавлено, False - в противном случае.

        """
        if not self._compRanges:
            self._compRanges.append(compRange)
            if compRange.isFitted():
                self._compRangesFitted.append(compRange)
            return True
        lastCompRange = self._compRanges[-1]
        if lastCompRange.getSpecValue("type") == compRange.getSpecValue("type"):
            if config.getboolean("table", "separate group for each doc"):
                if lastCompRange.getSpecValue("doc") == compRange.getSpecValue("doc"):
                    # Если тип и документ не указаны, формировать группы
                    # на основе буквенной части обозначения.
                    if compRange.getSpecValue("type") \
                        or compRange.getSpecValue("doc") \
                        or lastCompRange.getRefType() == compRange.getRefType():
                            self._compRanges.append(compRange)
                            if compRange.isFitted():
                                self._compRangesFitted.append(compRange)
                            return True
            else:
                # Если тип не указан, формировать группы на основе
                # буквенной части обозначения.
                if compRange.getSpecValue("type") \
                    or lastCompRange.getRefType() == compRange.getRefType():
                        self._compRanges.append(compRange)
                        if compRange.isFitted():
                            self._compRangesFitted.append(compRange)
                        return True
        return False

    @staticmethod
    def _strCommon(str1, str2):
        """Определить общее начало двух строк.

        Вернуть подстроку, с которой начинаются обе указанные строки.

        Аргументы:
        str1 (str) -- первая строка;
        str2 (str) -- вторая строка.

        Возвращаемое значение (str) -- общее начало двух строк.

        """
        for i in range(len(str1)):
            if i == len(str2) or str1[i] != str2[i]:
                return str1[:i]
        return str1

    def getTitle(self):
        """Вернуть заголовок группы компонентов.

        По умолчанию, заголовком является "Тип" компонента.
        Если установлен параметр "title with doc", то после "Типа", через
        пробел, будет указан "Документ".
        Если "Документы" компонентов группы отличаются, то заголовок будет
        состоять из нескольких строк, каждая из которых служит для отдельного
        документа. При этом перед каждым документом будет указана часть
        наименования для идентификации компонентов.

        Возвращаемое значение (list) -- список строк заголовка.

        """
        if len(self) == 0:
            return []

        currentType = self._compRanges[0].getSpecValue("type", plural=True)

        if not config.getboolean("table", "title with doc"):
            return [currentType]

        currentName = self._compRanges[0].getSpecValue("name")
        currentDoc = self._compRanges[0].getSpecValue("doc")

        # Список уникальных пар Наименование-Документ
        nameDocList = []
        for compRange in self:
            currentName = compRange.getSpecValue("name")
            currentDoc = compRange.getSpecValue("doc")
            if not currentDoc:
                # Если имеются компоненты, в которых документ не указан,
                # то в заголовке для них будет указан только тип.
                currentName = ""
            for i in range(len(nameDocList)):
                savedName = nameDocList[i][0]
                savedDoc = nameDocList[i][1]
                if savedDoc == currentDoc:
                    commonName = self._strCommon(savedName, currentName)
                    commonName = commonName.rstrip(" -")
                    if commonName:
                        # Оставить только общую часть наименования
                        nameDocList[i][0] = commonName
                        break
            else:
                nameDocList.append([currentName, currentDoc])

        # Максимально сократить наименования, оставив только часть
        # достаточную для идентификации.
        for i in range(len(nameDocList)):
            name = nameDocList[i][0]
            doc = nameDocList[i][1]
            nameParts = re.findall(r"([-\s]?[^-\s]+)", name)
            if len(nameParts) > 1:
                for j in range(1, len(nameParts)):
                    shortName = "".join(nameParts[:j])
                    if [shortName, doc] not in nameDocList:
                        nameDocList[i][0] = shortName
                        break

        # Сформировать наименование
        if not nameDocList:
            return [currentType]
        firstDoc = nameDocList[0][-1]
        for name, doc in nameDocList:
            if doc != firstDoc:
                break
        else:
            # У всех компонентов один документ
            title = currentType
            if title:
                title += ' '
            title += firstDoc
            return [title]
        groupNames = []
        nameDocList.sort(key=lambda nameDoc: nameDoc[0])
        for nameDoc in nameDocList:
            name = currentType
            if nameDoc[0]:
                if name:
                    name += ' '
                name += nameDoc[0]
            if nameDoc[1]:
                if name:
                    name += ' '
                name += nameDoc[1]
            groupNames.append(name)

        return groupNames

class CompGroupBom():
    """Группа компонентов.

    Группой считается множество CompRange, которые имеют одинаковый тип.
    Если установлен параметр "separate group for each doc", то компоненты
    будут разбиваться на группы не только по типу, но и по документу.

    """

    def __init__(self, schematic, compRange=None):
        self.schematic = schematic
        self._compRanges = []
        self._compRangesFitted = []
        if compRange is not None:
            self._compRanges.append(compRange)
            if compRange.isFitted():
                self._compRangesFitted.append(compRange)

    def __iter__(self):
        for compRange in self._compRanges:
            yield compRange

    def __getitem__(self, key):
        return self._compRanges[key]

    def __len__(self):
        return len(self._compRanges)

    def __len__(self):
        return len(self._compRanges)

    def lenFitted(self):
        return len(self._compRangesFitted)
    
    def sort(self, key=None):
        self._compRanges.sort(key=key)

    def append(self, compRange):
        """Добавить множество компонентов в группу.

        Аргументы:
        compRange (CompRange) -- множество компонентов, которое необходимо
            добавить в группу.

        Возвращаемые значения (boolean) -- True - если множество было
            добавлено, False - в противном случае.

        """
        if not self._compRanges:
            self._compRanges.append(compRange)
            if compRange.isFitted():
                self._compRangesFitted.append(compRange)
            return True
        lastCompRange = self._compRanges[-1]
        if lastCompRange.getBomValue("type") == compRange.getBomValue("type"):
            if config.getboolean("table", "separate group for each doc"):
                if lastCompRange.getBomValue("doc") == compRange.getBomValue("doc"):
                    # Если тип и документ не указаны, формировать группы
                    # на основе буквенной части обозначения.
                    if compRange.getBomValue("type") \
                        or compRange.getBomValue("doc") \
                        or lastCompRange.getRefType() == compRange.getRefType():
                            self._compRanges.append(compRange)
                            if compRange.isFitted():
                                self._compRangesFitted.append(compRange)
                            return True
            else:
                # Если тип не указан, формировать группы на основе
                # буквенной части обозначения.
                if compRange.getBomValue("type") \
                    or lastCompRange.getRefType() == compRange.getRefType():
                        self._compRanges.append(compRange)
                        if compRange.isFitted():
                            self._compRangesFitted.append(compRange)
                        return True
        return False

    @staticmethod
    def _strCommon(str1, str2):
        """Определить общее начало двух строк.

        Вернуть подстроку, с которой начинаются обе указанные строки.

        Аргументы:
        str1 (str) -- первая строка;
        str2 (str) -- вторая строка.

        Возвращаемое значение (str) -- общее начало двух строк.

        """
        for i in range(len(str1)):
            if i == len(str2) or str1[i] != str2[i]:
                return str1[:i]
        return str1

class Schematic():
    """Данные о схеме и компонентах."""

    def __init__(self, altium_bom_name, auto_num=True):
        self.variant = ""
        self.title = ""
        self.number = ""
        self.company = ""
        self.developer = ""
        self.verifier = ""
        self.inspector = ""
        self.approver = ""

        self.fixed_references_log = []
        self.components = []
        self.typeNamesDict = {}

        netlist = altiumbom.read(altium_bom_name)

        # ---------- 0. Проверка обязательных колонок ----------
        required_str = config.get('bom_required', 'fields')
        REQUIRED_FIELDS = [f.strip() for f in required_str.split(',') if f.strip()]
        if netlist:
            first_row = netlist[0]
            missing = [field for field in REQUIRED_FIELDS if field not in first_row]
            if missing:
                raise ValueError(
                    f"В файле '{altium_bom_name}' отсутствуют обязательные колонки: {', '.join(missing)}"
                )
        else:
            raise ValueError(f"Файл '{altium_bom_name}' не содержит данных (пустой список строк).")

        # ---------- 1. Загружаем маппинг из конфига ----------

        mapping = {}
        for attr in ['reference', 'value', 'footprint', 'datasheet', 'fitted',
                     'title', 'number', 'company', 'developer', 'verifier', 'inspector', 'approver', 'variant']:
            col = config.get('bom_mapping', attr)
            if col is not None:
                mapping[attr] = col

        col_to_attr = {}
        for attr, col in mapping.items():
            if attr in ('title', 'number', 'company', 'developer', 'verifier', 'inspector', 'approver', 'variant'):
                target = 'schematic'
            else:
                target = 'component'
            col_to_attr[col] = (target, attr)

        # ---------- 2. Создаём компоненты и заполняем атрибуты ----------
        for comp in netlist:
            component = Component(self)
            for item, value in comp.items():
                # Если колонка есть в маппинге – обрабатываем
                if item in col_to_attr:
                    target_type, attr_name = col_to_attr[item]
                    if target_type == 'schematic':
                        if attr_name == 'number':
                            self.number = '.'.join(value.split('.')[:-1]) + ' Э3'
                        elif attr_name == 'variant':
                            self.variant = value if value != '-00' else ''
                        else:
                            setattr(self, attr_name, value)
                    else:  # component
                        if attr_name == 'value':
                            component.value = value if value != '~' else ''
                        elif attr_name == 'fitted':
                            component.fitted = True if value == 'Fitted' else False
                        else:
                            setattr(component, attr_name, value if value != '~' else '')
                # Все колонки всегда сохраняются в fields (для шаблонов)
                component.fields[item] = value
            self.components.append(component)

        if not self.number:
            self.number = "Project name не указан"

        # ---------- 2. Исправляем обозначения ----------
        if auto_num:
            self._fix_references()

        # ---------- 3. Заполняем поля, зависящие от типа обозначения ----------
        for component in self.components:
            component.fields['Tolerance'] = altiumbom.format_tolerance("")
            component.fields['_FType'] = altiumbom.format_ftype(component.getRefType(), "")
            component.fields['_Subclass'] = altiumbom.format_type(component.getRefType(), "")
            component.fields['_Class'] = altiumbom.format_class(component.getRefType())

    def getGroupedComponentsIndex(self):
        """Вернуть компоненты, сгруппированные по обозначению и типу.

        Одинаковые компоненты с любыми номерами объединяются в одну группу.
        Сортировка групп по минимальному номеру.
        """
        # Шаг 1. Группируем все компоненты по одинаковым параметрам
        groups_dict = {}
        for comp in self.components:
            # Ключ: тип, наименование, документ, примечание
            key = (
                comp.getIndexValue("type"),
                comp.getIndexValue("name"),
                comp.getIndexValue("doc"),
                comp.getIndexValue("comment")
            )
            groups_dict.setdefault(key, []).append(comp)

        comp_ranges = []
        for key, comps in groups_dict.items():
            # Сортируем по буквенной части, затем по номеру
            sorted_comps = sorted(comps, key=lambda c: (c.getRefType(), c.getRefNumber()))
            cr = CompRangeIndex(self)
            for comp in sorted_comps:
                cr.append(comp)
            if len(cr) > 0:
                comp_ranges.append(cr)

        # Шаг 2. Сортируем полученные диапазоны по первому номеру
        # (по типу обозначения, затем по минимальному номеру)
        comp_ranges.sort(key=lambda cr: (
            cr.getRefType(),
            min(cr.getRefNumber(ref) for ref in cr)
        ))

        # Шаг 3. Формируем группы (CompGroup) как раньше, но теперь без разрывов
        groups = []
        compGroup = CompGroupIndex(self)
        for cr in comp_ranges:
            if not compGroup.append(cr):
                groups.append(compGroup)
                compGroup = CompGroupIndex(self, cr)
        if len(compGroup) > 0:
            groups.append(compGroup)

        return groups

    def _fix_references(self):
        """Исправляет обозначения без числовой части или с '?', присваивая им номера."""
        max_numbers = {}
        for comp in self.components:
            ref = comp.reference
            if re.match(REF_REGEXP, ref):
                ref_type = comp.getRefType()
                ref_num = comp.getRefNumber()
                if ref_type not in max_numbers or ref_num > max_numbers[ref_type]:
                    max_numbers[ref_type] = ref_num

        counters = {}
        for comp in self.components:
            ref = comp.reference
            if not re.match(REF_REGEXP, ref):
                ref_type = ref.replace('?', '').strip()
                if not ref_type:
                    ref_type = 'U'

                if ref_type in max_numbers:
                    next_num = max_numbers[ref_type] + 1
                else:
                    next_num = 1

                if ref_type in counters:
                    next_num = max(max_numbers.get(ref_type, 0), counters[ref_type]) + 1

                old_ref = ref
                new_ref = f"{ref_type}{next_num}"
                comp.reference = new_ref
                counters[ref_type] = next_num
                max_numbers[ref_type] = next_num

                # Сохраняем сообщение о замене
                self.fixed_references_log.append(
                    f"Автонумерация: '{old_ref}' заменено на '{new_ref}'"
                )
    
    def getSuperGroupedComponentsIndex(self):
        """Вернуть компоненты, сгруппированные по обозначению, классу и типу."""
        supergroups = []
        groups = self.getGroupedComponentsIndex()
        currentClass = ''
        for group in groups:
            compClass = group[0].getIndexValue("class", plural=True)
            if compClass != currentClass:
                supergroups.append([])
                currentClass = compClass
            if len(supergroups) != 0:
                supergroups[-1].append(group)
        return supergroups
    
    def getGroupedComponentsSpec(self):
        """Вернуть компоненты, сгруппированные по типу."""
        sortedComponents = sorted(
            self.components,
            key=lambda comp: comp.getSpecValue("name")
        )
        sortedComponents = sorted(
            sortedComponents,
            key=lambda comp: comp.getSpecValue("type")
        )
        sortedComponents = sorted(
            sortedComponents,
            key=lambda comp: "" if comp.getSpecValue("type") else comp.getRefType()
        ) # Компоненты без типа сортировать по буквенной части обозначения
        groups = []
        compGroup = CompGroupSpec(self)
        compRange = CompRangeSpec(self)
        for comp in sortedComponents:
            if not compRange.append(comp):
                if not compGroup.append(compRange):
                    groups.append(compGroup)
                    compGroup = CompGroupSpec(self, compRange)
                compRange = CompRangeSpec(self, comp)
        if len(compRange) > 0:
            if not compGroup.append(compRange):
                groups.append(compGroup)
                compGroup = CompGroupSpec(self, compRange)
        if len(compGroup) > 0:
            groups.append(compGroup)

        # Группы компонентов должны быть отсортированы по буквенной части
        # обозначений.
        # Если группы имеют одинаковые буквенные обозначения - сортировать
        # по наименованию группы (тип или тип+документ).
        # Внутри группы, элементы перечисляются в порядке возрастания цифровой части обозначения.
        for index in range(len(groups)):
            groups[index].sort(
                key=lambda compRange: compRange.getRefNumber()
            )
        groups.sort(
            key=lambda group: group.getTitle()[:1]
        )
        groups.sort(
            key=lambda group: group[0].getRefType()
        )           
        
        return groups
        
    def getSuperGroupedComponentsSpec(self):
        """Вернуть компоненты, сгруппированные по обозначению, классу и типу."""
        supergroups = []
        groups = self.getGroupedComponentsSpec()
        currentClass = ''
        for group in groups:
            compClass = group[0].getSpecValue("class", plural=True)
            if compClass != currentClass:
                supergroups.append([])
                currentClass = compClass
            if len(supergroups) != 0:
                supergroups[-1].append(group)
        return supergroups
    
    def getGroupedComponentsBom(self):
        """Вернуть компоненты, сгруппированные по типу."""
        sortedComponents = sorted(
            self.components,
            key=lambda comp: comp.getBomValue("name")
        )
        sortedComponents = sorted(
            sortedComponents,
            key=lambda comp: comp.getBomValue("type")
        )
        sortedComponents = sorted(
            sortedComponents,
            key=lambda comp: "" if comp.getBomValue("type") else comp.getRefType()
        ) # Компоненты без типа сортировать оп буквенной части обозначения
        groups = []
        compGroup = CompGroupBom(self)
        compRange = CompRangeBom(self)
        for comp in sortedComponents:
            if not comp.fitted:
                continue
            if not compRange.append(comp):
                if not compGroup.append(compRange):
                    groups.append(compGroup)
                    compGroup = CompGroupBom(self, compRange)
                compRange = CompRangeBom(self, comp)
        if len(compRange) > 0:
            if not compGroup.append(compRange):
                groups.append(compGroup)
                compGroup = CompGroupBom(self, compRange)
        if len(compGroup) > 0:
            groups.append(compGroup)

        # Группы компонентов должны быть отсортированы по буквенной части
        # обозначений.
        # Если группы имеют одинаковые буквенные обозначения - сортировать
        # по наименованию группы (тип или тип+документ).
        # Внутри группы, элементы перечисляются в порядке возрастания цифровой части обозначения.
        for index in range(len(groups)):
            groups[index].sort(
                key=lambda compRange: compRange.getRefNumber()
            )
        groups.sort(
            key=lambda group: group[0].getBomValue("type")
        )
        groups.sort(
            key=lambda group: group[0].getRefType()
        )
        return groups
    
    def getSuperGroupedComponentsBom(self):
        """Вернуть компоненты, сгруппированные по обозначению, классу и типу."""
        supergroups = []
        groups = self.getGroupedComponentsBom()
        currentClass = ''
        for group in groups:
            compClass = group[0].getSpecValue("class", plural=True)
            if compClass != currentClass:
                supergroups.append([])
                currentClass = compClass
            if len(supergroups) != 0:
                supergroups[-1].append(group)
        return supergroups
