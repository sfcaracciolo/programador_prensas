from PySide6.QtSql import *
from PySide6.QtCore import * 
from PySide6.QtWidgets import * 
from PySide6.QtGui import * 
import resources

class OpItemTable(QTableView):
    def __init__(self, iop_mapper, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iop_mapper = iop_mapper
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().hide()

        # horizontal header
        self.setSortingEnabled(False) # si, false.
        self.hheader = self.horizontalHeader()
        self.hheader.setSectionsClickable(True)
        self.hheader.setSortIndicatorShown(True)
        self.hheader.sectionClicked.connect(self.sort)

    @Slot(int)
    def sort(self, column: int = None):
        if column is None:
            column = 11
            self.hheader.setSortIndicator(column, Qt.SortOrder.DescendingOrder)
            
        order = self.hheader.sortIndicatorOrder()
        self.iop_mapper.model().column = column
        self.iop_mapper.model().order = order
        self.sortByColumn(column, order)

    def setModel(self, model: QAbstractItemModel) -> None:
        ret = super().setModel(model)
        list(map(self.hideColumn, set(range(model.columnCount())) - set(model.sourceModel().cols)))
        self.resizeColumnsToContents()
        return ret

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        try:
            iop_index = self.selectedIndexes()[0]
        except IndexError:
            pass
        else:
            self.iop_mapper.setCurrentIndex(iop_index.row())

        return super().selectionChanged(selected, deselected)

class OpItemView(QWidget):
    def __init__(self, iop_mapper, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.table = OpItemTable(iop_mapper)

        self.w_comment = QTextEdit()
        self.w_comment.setPlaceholderText('...')
        self.w_comment.setReadOnly(True)

        iop_model = iop_mapper.model().sourceModel()
        iop_mapper.addMapping(self.w_comment, iop_model.fieldIndex('CM76_26')) # CM76_26

        layout = QVBoxLayout()
        layout.addWidget(self.table, stretch=4)
        layout.addWidget(self.w_comment, stretch=1)

        self.setLayout(layout)

class TpItemView(QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)

    def setModel(self, model: QAbstractItemModel) -> None:
        ret = super().setModel(model)
        self.resizeColumnsToContents()
        return ret

class CalendarWidget(QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSortingEnabled(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.h_header = self.horizontalHeader()
        self.h_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.h_header.setDefaultSectionSize(90)

        self.v_header = self.verticalHeader()
        self.v_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.v_header.setDefaultSectionSize(90)

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        self.clearFocus() # estas dos lineas son para solucionar el bug de la seleccion de la celdas.
        self.setFocus()
        return super().selectionChanged(selected, deselected)

class WidgetDate(QWidget):
    def __init__(self, view_format, parent=None) -> None:
        super().__init__(parent)

        self.w_popup_button = QPushButton()
        self.w_popup_button.setIcon(QIcon(':/icons/calendar.png'))
        self.w_popup_button.setAutoFillBackground(False)
        self.w_popup_button.setFlat(True)

        self.w_clear_button = QPushButton()
        self.w_clear_button.setIcon(QIcon(':/icons/broom.png'))
        self.w_clear_button.setAutoFillBackground(False)
        self.w_clear_button.setFlat(True)

        self.w_calendar = QCalendarWidget()
        self.w_calendar.setWindowFlag(Qt.Popup)
        self.w_calendar.setSelectionMode(QCalendarWidget.SingleSelection)

        self.w_line_edit = QLineEdit()
        self.w_line_edit.setReadOnly(True)

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        layout.addWidget(self.w_line_edit)
        layout.addWidget(self.w_clear_button)
        layout.addWidget(self.w_popup_button)

        
        self.w_popup_button.clicked.connect(self.show_calendar)
        self.w_clear_button.clicked.connect(self.w_line_edit.clear)
        self.w_calendar.clicked.connect(self.click_date)

        self.setLayout(layout)

        self.view_format = view_format
        self.db_format = 'yyyyMMdd'

    def click_date(self, date:QDate):
        val = date.toString(self.view_format)
        self.w_line_edit.setText(val)
        self.w_calendar.close()

    def show_calendar(self):
        rect = self.w_line_edit.geometry()
        pos = QPoint(rect.x(), rect.y() + rect.height())
        global_pos = self.w_line_edit.mapToGlobal(pos)
        self.w_calendar.move(global_pos)
        self.w_calendar.show()
        
class DbfIntDate(WidgetDate):
    def __init__(self, parent=None) -> None:
        super().__init__('yyMMdd', parent)

    @Property(int)
    def value(self):
        view_val = self.w_line_edit.text()
        if view_val != '':
            db_val = int(view_val)
        else:
            db_val = 0
        return db_val
        
    @value.setter
    def value(self, db_val):
        if db_val > 0:
            view_val = str(db_val)
        else:
            view_val = ''
        self.w_line_edit.setText(view_val)

class DbfCharDate(WidgetDate):
    def __init__(self, parent=None) -> None:
        super().__init__('yyyy/MM/dd', parent)

    @Property(str)
    def value(self):
        view_val = self.w_line_edit.text()
        if view_val != '':
            date = QDate.fromString(view_val, self.view_format)
            db_val = date.toString(self.db_format)
        else:
            db_val = ''
        return db_val
        
    @value.setter
    def value(self, db_val):
        if db_val != '':
            date = QDate.fromString(db_val, self.db_format)
            view_val = date.toString(self.view_format)
        else:
            view_val = ''
        self.w_line_edit.setText(view_val)

class LabelSiNo(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.value = ''

    @Property(int)
    def text_sino(self):
        return self.value
        
    @text_sino.setter
    def text_sino(self, val):
        self.value = 'Si' if val == 1 else 'No'
        self.setText(self.value)
