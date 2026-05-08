#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, glob, sys, shutil, argparse, string, csv, time
from core import config, index, spec, bom, sds, sds2, stamp, output
from PyQt5 import QtCore, QtWidgets, QtGui, uic
from queue import Queue

class MainWin(QtWidgets.QMainWindow):
	
	prog_path = os.path.dirname(os.path.realpath(__file__))
	latex_path = ''
	netlist = ''
	tables = {}
	stamps = {}
	lookup = {
		'Перечень элементов'         : 'index',
		'Спецификация'               : 'spec',
		#'Ведомость покупных изделий' : 'bom',
		'SDS Компэл'                 : 'sds',
		'SDS (без произв.)': 'sds2'
	}
	extention = ''
	
	def __init__(self, form_arg):
		super(MainWin, self).__init__()
		
		uic.loadUi(os.path.join(self.prog_path, "altidoc.ui"), self)
		self.setWindowIcon(QtGui.QIcon(os.path.join(self.prog_path, "icons", "sticker")))
		self.actionOpen.setIcon(QtGui.QIcon.fromTheme("document-open", QtGui.QIcon(os.path.join(self.prog_path, "icons", "document-open"))))
		self.actionAbout.setIcon(QtGui.QIcon.fromTheme("help-about", QtGui.QIcon(os.path.join(self.prog_path, "icons", "help-about"))))
		self.actionExit.setIcon(QtGui.QIcon.fromTheme("application-exit", QtGui.QIcon(os.path.join(self.prog_path, "icons", "window-close"))))
		self.actionTitle.setIcon(QtGui.QIcon.fromTheme("format-text-underline", QtGui.QIcon(os.path.join(self.prog_path, "icons", "format-text-underline-symbolic"))))
		self.actionSectionTitle.setIcon(QtGui.QIcon.fromTheme("format-text-bold", QtGui.QIcon(os.path.join(self.prog_path, "icons", "format-text-bold-symbolic"))))
		self.actionDelete.setIcon(QtGui.QIcon.fromTheme("edit-delete", QtGui.QIcon(os.path.join(self.prog_path, "icons", "edit-delete"))))
		self.actionInsertAbove.setIcon(QtGui.QIcon.fromTheme("go-top", QtGui.QIcon(os.path.join(self.prog_path, "icons", "go-top"))))
		self.actionInsertBelow.setIcon(QtGui.QIcon.fromTheme("go-bottom", QtGui.QIcon(os.path.join(self.prog_path, "icons", "go-bottom"))))
		self.actionSave.setIcon(QtGui.QIcon.fromTheme("media-floppy", QtGui.QIcon(os.path.join(self.prog_path, "icons", "media-floppy"))))
		self.actionSaveAll.setIcon(QtGui.QIcon.fromTheme("document-save", QtGui.QIcon(os.path.join(self.prog_path, "icons", "document-save"))))
		self.actionPosRebuild.setIcon(QtGui.QIcon.fromTheme("view-sort-ascending", QtGui.QIcon(os.path.join(self.prog_path, "icons", "view-sort-ascending-symbolic"))))
		
		self.setEnabledActions(False)
		self.tabWidget.setEnabled(False)
		self.actionPosRebuild.setEnabled(False)
		
		self.actionOpen.triggered.connect(self.slotOpen)
		self.actionSave.triggered.connect(self.slotSave)
		self.actionSaveAll.triggered.connect(self.slotSaveAll)
		self.actionAbout.triggered.connect(self.about)
		self.actionAboutQt.triggered.connect(self.aboutQt)
		self.actionExit.triggered.connect(self.close)
		self.actionInsertAbove.triggered.connect(self.insertRowAbove)
		self.actionInsertBelow.triggered.connect(self.insertRowBelow)
		self.actionDelete.triggered.connect(self.deleteRow)
		self.actionTitle.triggered.connect(self.typeChangedTitle)
		self.actionSectionTitle.triggered.connect(self.typeChangedSectionTitle)
		self.actionPosRebuild.triggered.connect(self.rebuldPos)
		
		
		self.latex_path = config.get('output', 'latex_path')
		self.extention = config.get('output', 'default_type')
		self.netlist = form_arg['netlist']
		
		self.tables = {
			'index' : self.indexTable,
			'spec'  : self.specTable,
			#'bom'   : self.bomTable,
			'sds'   : self.sdsTable,
			'sds2': self.sds2Table
		}
		
		self.stamps = {
			'index' : (self.indexStamp, self.indexStamp2),
			'spec'  : (self.specStamp, self.specStamp2),
			#'bom'   : (self.bomStamp, self.bomStamp2),
			'sds'   : (self.sdsStamp, self.sdsStamp2),
			'sds2': (self.sds2Stamp, self.sds2Stamp2)
		}
		
		self.export_ext = config.getsection('export')

		if 'sds2' not in self.export_ext:
			self.export_ext['sds2'] = self.export_ext.get('sds', 'pdf')
		
		entables = config.get('gui', 'tables').split(',')
		
		for idx in reversed(range(self.tabWidget.count())):
			header = self.lookup[self.tabWidget.tabText(idx)]
			if header not in entables:
				self.tabWidget.removeTab(idx)
				self.tables.pop(header)
				self.stamps.pop(header)
		
		self.tabWidget.currentChanged.connect(self.tabCurrentChanged)
		
		self.setAcceptDrops(True)
		self.show()
		
		if len(self.netlist):
			self.readNetlist()

	def setEnabledActions(self, enabled):
		self.actionTitle.setEnabled(enabled)
		self.actionSectionTitle.setEnabled(enabled)
		self.actionInsertAbove.setEnabled(enabled)
		self.actionInsertBelow.setEnabled(enabled)
		self.actionDelete.setEnabled(enabled)
		self.actionSave.setEnabled(enabled)
		self.actionSaveAll.setEnabled(enabled)

	def readNetlist(self):
		progress = QtWidgets.QProgressDialog(None, None, 0, len(self.lookup), self)
		progress.setWindowTitle("Чтение")
		progress.setWindowModality(True)
		progress.setValue(0)
		progress.show()
		QtWidgets.QApplication.processEvents()
		for i, doc in enumerate(self.tables.keys()):
			if doc == 'index':
				table = index.build(self.netlist)
			elif doc == 'spec':
				table = spec.build(self.netlist)
			elif doc == 'bom':
				table = bom.build(self.netlist)
			elif doc == 'sds':
				table = sds.build(self.netlist)
			elif doc == 'sds2':
				table = sds2.build(self.netlist)  # отдельный построитель

			stamp_dict = stamp.build(self.netlist, doc)  # теперь doc='sds2' работает
			header = output.lookup[stamp_dict['type']]['header']
			self.fillTable(self.tables[doc], header, table)
			self.fillStamp(self.stamps[doc], stamp_dict)
			progress.setValue(i + 1)
			QtWidgets.QApplication.processEvents()
		progress.close()
		self.setEnabledActions(True)
		self.tabWidget.setEnabled(True)
		self.statusbar.showMessage('Прочитан BOM "%s"' % self.netlist)
		self.setWindowTitle('%s - altidoc' % self.netlist)
	
	def fillTable(self, table, header, content):
		table.horizontalHeader().setStretchLastSection(False)
		table.setColumnCount(len(header))
		table.setRowCount(len(content))
		table.setHorizontalHeaderLabels(header)
		for i, row in enumerate(content):
			for j, cell in enumerate(row[:-1]):
				table.setItem(i,j,QtWidgets.QTableWidgetItem(cell))
			if row[-1] != '':
				item = table.item(i, header.index('Наименование'))
				item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
				font = item.font()
				if row[-1] == 'title':
					font.setUnderline(True)
				elif row[-1] == 'section_title':
					font.setBold(True)
					font.setUnderline(True)
				item.setFont(font)
		table.resizeColumnsToContents()
		table.horizontalHeader().setStretchLastSection(True)
		table.currentCellChanged.connect(self.tableChanged)
	
	def fillStamp(self, table, content):
		table1, table2 = table
		for tab in table:
			for i in range(tab.rowCount()):
				key = tab.verticalHeaderItem(i).text()
				tab.setItem(i,0,QtWidgets.QTableWidgetItem(content[output.stamp_lookup[key]]))
	
	def readTableHeader(self, table):
		header = [''] * table.columnCount()
		for j in range(table.columnCount()):
			header[j] = table.horizontalHeaderItem(j).text()
		return header
	
	def readTable(self, table):
		header = self.readTableHeader(table)
		col_name = header.index('Наименование')
		content = table.rowCount() * [[]]
		for i in range(table.rowCount()):
			content[i] = [''] * (table.columnCount()+1)
			for j in range(table.columnCount()):
				content[i][j] = table.item(i,j).text()
			font = table.item(i,col_name).font()
			if font.underline():
				if font.bold():
					content[i][-1] = 'section_title'
				else:
					content[i][-1] = 'title'
		return content
	
	def readStamp(self, table):
		table1, table2 = table
		content = {}
		content['number']      = table1.item(0,0).text()
		content['title']       = table1.item(1,0).text()
		content['first_usage'] = table1.item(2,0).text()
		content['company']     = table1.item(3,0).text()
		
		content['developer']   = table2.item(0,0).text()
		content['verifier']    = table2.item(1,0).text()
		content['inspector']   = table2.item(2,0).text()
		content['approver']    = table2.item(3,0).text()
		
		parent = table1.parentWidget()
		tab = parent.parentWidget().parentWidget()
		content['type'] = tab.tabText(tab.indexOf(parent)).replace('Спецификация','')
		return content
	
	def insertRowAbove(self):
		table = self.tables[self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]]
		i = table.currentRow()
		table.insertRow(i)
		for j in range(table.columnCount()):
			table.setItem(i,j,QtWidgets.QTableWidgetItem(''))
		
	def insertRowBelow(self):
		table = self.tables[self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]]
		i = table.currentRow()+1
		table.insertRow(i)
		for j in range(table.columnCount()):
			table.setItem(i,j,QtWidgets.QTableWidgetItem(''))
		
	def deleteRow(self):
		table = self.tables[self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]]
		table.removeRow(table.currentRow())
	
	def tableChanged(self, i):
		table = self.tables[self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]]
		header = self.readTableHeader(table)
		item = table.item(i, header.index('Наименование'))
		if item:
			font = item.font()
			self.actionTitle.setChecked(font.underline() and not font.bold())
			self.actionSectionTitle.setChecked(font.underline() and font.bold())
	
	def tabCurrentChanged(self, i):
		self.actionPosRebuild.setEnabled(self.tabWidget.tabText(i) != 'Перечень элементов')
		table = self.tables[self.lookup[self.tabWidget.tabText(i)]]
		self.tableChanged(table.currentRow())
	
	def typeChangedSectionTitle(self, checked):
		table = self.tables[self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]]
		header = self.readTableHeader(table)
		i = table.currentRow()
		item = table.item(i, header.index('Наименование'))
		if checked:
			self.actionTitle.setChecked(False)
			item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
		else:
			item.setTextAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
		font = item.font()
		font.setUnderline(checked)
		font.setBold(checked)
		item.setFont(font)
	
	def typeChangedTitle(self, checked):
		table = self.tables[self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]]
		header = self.readTableHeader(table)
		i = table.currentRow()
		item = table.item(i, header.index('Наименование'))
		if checked:
			self.actionSectionTitle.setChecked(False)
			item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
		else:
			item.setTextAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
		font = item.font()
		font.setUnderline(checked)
		font.setBold(False)
		item.setFont(font)
	
	def rebuldPos(self):
		doc = self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]
		table = self.tables[doc]
		header = self.readTableHeader(table)
		if doc == 'spec':
			qty_index = header.index('Кол.')
			pos_index = header.index('Поз.')
			components_only = True
		elif doc == 'bom':
			qty_index = header.index('Всего')
			pos_index = header.index('№ строки')
			components_only = config.getboolean("table", "only components have position numbers")
		else:
			return
		
		pos_count = 1
		for i in range(table.rowCount()):
			if table.item(i,qty_index).text() == '' and components_only:
				table.item(i,pos_index).setText('')
			else:
				table.item(i,pos_index).setText(str(pos_count))
				pos_count += 1
	
	def dragEnterEvent(self, event):
		if event.mimeData().hasFormat("text/uri-list"):
			event.acceptProposedAction()
		
	def dropEvent(self, event):
		files = []
		for url in event.mimeData().urls():
			if url.isLocalFile() and len(url.path())>4 and url.path()[-4:] == '.net':
				if os.name == 'nt':
					files.append(url.path()[1:].replace('/','\\'))
				else:
					files.append(url.path())
		event.acceptProposedAction()
		if files:
			self.netlist = files[0]
			self.readNetlist()
	
	def slotOpen(self):
		(path, filt) = QtWidgets.QFileDialog.getOpenFileName(self, 'Открыть', os.getcwd(),'Altium BOM (*_bom.csv)')
		if len(path) != 0:
			self.netlist = path
			self.readNetlist()
			os.chdir(os.path.dirname(path))
	
	def slotSave(self):
		doc = self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]
		name = self.readStamp(self.stamps[doc])['number'] + '.' + self.extention
		ext = {'tex':'Файл LaTeX (*.tex)','pdf':'Файл PDF (*.pdf)','xls':'Файл Microsoft Excel 2003 (*.xls)','csv':'Файл CSV (*.csv)'}[self.extention]
		(path, filt) = QtWidgets.QFileDialog.getSaveFileName(self, 'Сохранить',
			os.path.join(os.getcwd(), name) ,'Файл LaTeX (*.tex);;Файл PDF (*.pdf);;Файл Microsoft Excel 2003 (*.xls);;Файл CSV (*.csv)', ext)
		if len(path) != 0:
			os.chdir(os.path.dirname(path))
			self.extention = {'Файл LaTeX (*.tex)':'tex','Файл PDF (*.pdf)':'pdf','Файл Microsoft Excel 2003 (*.xls)':'xls','Файл CSV (*.csv)':'csv'}[filt]
			doc = self.lookup[self.tabWidget.tabText(self.tabWidget.currentIndex())]
			table = self.readTable(self.tables[doc])
			stamp_dict = self.readStamp(self.stamps[doc])
			self.export(path, table, stamp_dict)
			self.statusbar.showMessage('Записан файл "%s"'%(path))

	def slotSaveAll(self):
		name = self.readStamp(self.stamps['spec'])['number'] + '*.' + self.extention
		path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Сохранить все', os.getcwd())
		sys.stdout.flush()
		if len(path) != 0:
			ext = self.extention
			os.chdir(path)
			numpdf = 0
			extentions = []
			for key in self.tables.keys():
				extentions.append(self.export_ext[key])
				if extentions[-1] == 'pdf':
					numpdf += 2
			if numpdf > 0:
				progress = QtWidgets.QProgressDialog(None, None, 0, numpdf, self)
				progress.setWindowTitle("Экспорт")
				progress.setWindowModality(True)
				progress.setValue(0)
				progress.show()
				QtWidgets.QApplication.processEvents()
			else:
				progress = None
			for tableWidget, stampWidget, extention in zip(self.tables.values(), self.stamps.values(), extentions):
				self.extention = extention
				table = self.readTable(tableWidget)
				stamp_dict = self.readStamp(stampWidget)
				number = stamp_dict['number'].split(' ')
				suffix = ' ' + number[-1] if len(number) > 1 else ''
				self.export(stamp_dict['number'] + '.' + extention, table, stamp_dict, progress)
			if numpdf > 0:
				progress.close()
			self.extention = ext
			self.statusbar.showMessage('Записаны файлы "%s"'%(path))

	def export(self, path, table, stamp_dict, progressDialog=None):
		if self.extention == 'tex':
			output.latex(table, stamp_dict, path)
		elif self.extention == 'pdf':
			if progressDialog is None:
				progress = QtWidgets.QProgressDialog(None, None, 0, 2, self)
				progress.setWindowTitle("Экспорт")
				progress.setWindowModality(True)
				progress.setValue(0)
				progress.show()
				QtWidgets.QApplication.processEvents()
			else:
				progress = progressDialog

			path_tex = path[:-3] + 'tex'
			output.latex(table, stamp_dict, path_tex)  # генерация .tex

			# Копируем НОВЫЕ стили, если они почему-то не в системе (вероятно, не нужно)
			# shutil.copy(...) убираем вовсе

			# Компиляция через lualatex (два прохода для окончательной расстановки ссылок)
			os.system('lualatex -interaction=nonstopmode "%s"' % path_tex)
			progress.setValue(progress.value() + 1)
			QtWidgets.QApplication.processEvents()
			os.system('lualatex -interaction=nonstopmode "%s"' % path_tex)
			progress.setValue(progress.value() + 1)
			QtWidgets.QApplication.processEvents()

			# Очистка временных файлов
			self.rm('*.aux')
			self.rm('*.log')
			self.rm('*.out')
			self.rm('*-converted-to.pdf')
			self.rm(path_tex)  # удаляем исходный .tex

			if progressDialog is None:
				progress.close()
		elif self.extention == 'xls':
			output.xls(table, stamp_dict, path)
		elif self.extention == 'csv':
			output.csv(table, stamp_dict, path)

	def rm(self, pattern):
		for f in glob.glob(pattern):
			os.remove(f)
		
	def about(self):
		QtWidgets.QMessageBox.about(self, 'О программе',
			'''<h2>altidoc</h2>
			<p><b>v 0.0
			<p>(бывший bom2latexmerge)
			<p>Программа для чтения файлов BOM Altium Designer,
			<br>обработки и преобразования в текстовые документы
			<br>по ГОСТ 2.106-96, ГОСТ 2.113-75, ГОСТ 2.701-2008
			<br>(форматы LaTeX, PDF, CSV)
			<p><b>Автор:
			<br><b>П. В. Шаршавин
			<p><b>© ООО "РТС", 2021''')
	
	def aboutQt(self):
		QtWidgets.QMessageBox.aboutQt(self, u'О Qt')

def main():
	
	if os.name == 'nt':
		sys.stdout.reconfigure(encoding='utf-8')
		
	conf_path = os.path.join(os.path.expanduser("~"), '.config', 'altidoc', 'altidoc.conf')
	
	if not os.path.isfile(conf_path):
		conf_path = 'altidoc.conf'
	
	config.load(conf_path)
	# convert paths to absolute
	config.set('output', 'latex_path', os.path.abspath(config.get('output', 'latex_path')))
	config.set('output', 'template_path', os.path.abspath(config.get('output', 'template_path')))
	
	parser = argparse.ArgumentParser(sys.argv)
	parser.add_argument('bom', nargs='?', default='', help='input filename')
	args = parser.parse_args()

	netlist = args.bom
	
	if len(netlist) > 8 and netlist[-8:] == '_bom.csv' and os.path.isfile(netlist):
		if len(os.path.dirname(netlist)):
			os.chdir(os.path.join(os.path.dirname(netlist),''))
		netlist = os.path.join(os.getcwd(), os.path.basename(netlist))
	
	form_arg = {'netlist'	: netlist}

	app = QtWidgets.QApplication(sys.argv)
	form = MainWin(form_arg)
	app.exec_()

if __name__ == "__main__":
	main()
