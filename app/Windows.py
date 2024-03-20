from math import ceil
from PySide6.QtSql import *
from PySide6.QtCore import * 
from PySide6.QtWidgets import * 
from PySide6.QtGui import * 
import Models, Views
from Constants import *
import resources

class HandlerSql(QWidget):
    sql_error = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setFocus()

    def executor(self, query: QSqlQuery, tp_model: QSqlTableModel):
        self.close()
        if not query.exec():
            self.sql_error.emit(query.lastError())
            return False

        if not tp_model.submitAll():
            self.sql_error.emit(tp_model.lastError())
            return False

        tp_model.layoutChanged.emit()

        return True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

class AddCommentForm(QWidget):
    update_iop_list_data = Signal()

    def __init__(self, backend_fun:str, iop_mapper:QDataWidgetMapper) -> None:
        super().__init__()
        self.iop_mapper = iop_mapper
        self.iop_model = iop_mapper.model().sourceModel()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)
        self.setFocus()
        self.setup_widgets()
        self.setup_mappers()
        self.setup_ui()

        self._query = QSqlQuery()
        self._query.prepare(f'CALL {backend_fun}(:iop_id, :fname, :comment)')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def setup_ui(self):

        form_layout = QFormLayout()

        # form_layout.addRow('Id', self.w_iop_id)
        # form_layout.addRow('File', self.w_fname)
        form_layout.addRow('Comentario', self.w_comment)

        button_box = QDialogButtonBox(
            QDialogButtonBox.SaveAll | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.SaveAll).setText('Guardar')

        button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.save)
        button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        # button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def setup_mappers(self):

        self.iop_mapper.addMapping(self.w_iop_id, self.iop_model.fieldIndex('id'), QByteArray('value'))
        self.iop_mapper.addMapping(self.w_fname, self.iop_model.fieldIndex('fname'), QByteArray('text'))
        self.iop_mapper.addMapping(self.w_comment, self.iop_model.fieldIndex('CM76_26'))
        
    def setup_widgets(self):

        self.w_iop_id = QSpinBox()
        self.w_iop_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_iop_id.setReadOnly(True)
        self.w_iop_id.setMaximum(1000000000)

        self.w_comment = QTextEdit()
        self.w_comment.setPlaceholderText('...')
        self.w_comment.textChanged.connect(self.trim_len_text)

        self.w_fname = QLineEdit()
        self.w_fname.setReadOnly(True)

    def trim_len_text(self):
        comment = self.w_comment.toPlainText()
        if len(comment) > MAX_COMMENT_SIZE:
            self.w_comment.setPlainText(comment[:MAX_COMMENT_SIZE])

    def save(self):
        iop_id = self.w_iop_id.value()
        fname = self.w_fname.text()
        comment = self.w_comment.toPlainText()
        self._query.bindValue(':iop_id',iop_id)
        self._query.bindValue(':fname',fname)
        self._query.bindValue(':comment', comment)

        if not self._query.exec():
            self.iop_mapper.revert()
            raise ValueError(self._query.lastError()) 
        
        if not self.iop_mapper.submit():
            raise ValueError(self.iop_mapper.lastError())
        
        self.update_iop_list_data.emit()
        self.close()

class OpeAssigTpForm(HandlerSql):

    def __init__(self, backend_fun:str, ope_model: QSqlTableModel, tp_mapper:QDataWidgetMapper):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)
        self.setFocus()

        self.tp_mapper = tp_mapper
        self.tp_model = tp_mapper.model()
        self.ope_model = ope_model

        self.setup_widgets()
        self.setup_mappers()
        self.setup_ui()

        self._query = QSqlQuery()
        self._query.prepare(f'CALL {backend_fun}(:tp_id, :operator)')

    def setup_mappers(self):

        self.tp_mapper.addMapping(self.w_tp_id, self.tp_model.fieldIndex('id'))
        self.tp_mapper.addMapping(self.w_ope, self.tp_model.fieldIndex('operator'))
        
    def setup_widgets(self):

        self.w_tp_id = QSpinBox()
        self.w_tp_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_tp_id.setReadOnly(True)
        self.w_tp_id.setMaximum(1000000000)

        self.w_ope = QComboBox()
        self.w_ope.setModel(self.ope_model)
        self.w_ope.setModelColumn(self.ope_model.fieldIndex('CM70_03'))

    def setup_ui(self):

        form_layout = QFormLayout()
        form_layout.addRow('Operario', self.w_ope)
        group_box = QGroupBox('Seleccione Operario')
        group_box.setLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Save ,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Remover')
        button_box.button(QDialogButtonBox.Save).setText('Aplicar')
        # button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.apply)
        button_box.rejected.connect(self.discard)
        # button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(group_box)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def apply(self):
        operator = self.w_ope.currentText()
        self.call(operator)

    def discard(self):
        operator = None
        self.call(operator)

    def call(self, operator):
        tp_id = self.w_tp_id.value()

        self._query.bindValue(':tp_id',tp_id)
        self._query.bindValue(':operator', operator)
        
        self.executor(self._query, self.tp_model)

class ShiftDateTpForm(HandlerSql):

    def __init__(self, backend_fun, tp_model:QSqlTableModel):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.tp_model = tp_model

        self.setup_widgets()
        self.setup_ui()

        self._query = QSqlQuery()
        self._query.prepare(f'CALL {backend_fun}(:machine, :date, :amount)')

    def setup_widgets(self):
        
        self.w_amount = QSpinBox()
        self.w_amount.setMinimum(1)
        self.w_amount.setMaximum(100000)
        self.w_amount.setValue(1)

    def setup_ui(self):

        form_layout = QFormLayout()
        form_layout.addRow('Cantidad', self.w_amount)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.Save).setText('Guardar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.save)
        button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def save(self):
        amount = self.w_amount.value()
        self._query.bindValue(':machine', self.machine)
        self._query.bindValue(':date', self.date)
        self._query.bindValue(':amount', amount)

        self.executor(self._query, self.tp_model)

class EditCyclesForm(HandlerSql):

    def __init__(self, tp_mapper:QDataWidgetMapper):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.tp_mapper = tp_mapper
        self.tp_model = tp_mapper.model()

        self.setup_widgets()
        self.setup_mappers()
        self.setup_ui()

        self._query = QSqlQuery()
        self._query.prepare(f'CALL bulk_update_cycles(:tp_id, :cycles)')

    def setup_mappers(self):

        self.tp_mapper.addMapping(self.w_tp_id, self.tp_model.fieldIndex('id'))
        self.tp_mapper.addMapping(self.w_cycles, self.tp_model.fieldIndex('cycles'))
        
    def setup_widgets(self):

        self.w_tp_id = QSpinBox()
        self.w_tp_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_tp_id.setReadOnly(True)
        self.w_tp_id.setMaximum(1000000000)
        
        self.w_cycles = QSpinBox()
        self.w_cycles.setMinimum(1)
        self.w_cycles.setMaximum(100000)
        self.w_cycles.setValue(1)

    def setup_ui(self):

        form_layout = QFormLayout()
        form_layout.addRow('Cantidad', self.w_cycles)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.Save).setText('Guardar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.save)
        button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def save(self):
        tp_id = self.w_tp_id.value()
        cycles = self.w_cycles.value()

        self._query.bindValue(':tp_id', tp_id)
        self._query.bindValue(':cycles', cycles)

        self.executor(self._query, self.tp_model)

class MoveTpForm(HandlerSql):

    def __init__(self, opc_model:QSqlTableModel, tp_mapper:QDataWidgetMapper):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.opc_model = opc_model
        self.tp_mapper = tp_mapper
        self.tp_model = tp_mapper.model()

        self.setup_widgets()
        self.setup_mappers()
        self.setup_ui()

        self._query = QSqlQuery()
        self._query.prepare('CALL update_tp(:tp_id, :machine, :date)')

    def setup_widgets(self):
        
        self.w_tp_id = QSpinBox()
        self.w_tp_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_tp_id.setReadOnly(True)
        self.w_tp_id.setMaximum(1000000000)

        self.w_maq = QComboBox()
        self.w_maq.addItems(MAQUINAS)
        # self.w_maq.setModel(self.opc_model)
        # self.w_maq.setModelColumn(self.opc_model.fieldIndex('machine'))

        self.w_start_date = QDateEdit()
        self.w_start_date.setDisplayFormat('dd/MM/yyyy')
        self.w_start_date.setCalendarPopup(True)
        self.w_start_date.setDate(QDate.currentDate())

    def setup_mappers(self):

        self.tp_mapper.addMapping(self.w_tp_id, self.tp_model.fieldIndex('id'))
        self.tp_mapper.addMapping(self.w_maq, self.tp_model.fieldIndex('machine'))
        self.tp_mapper.addMapping(self.w_start_date, self.tp_model.fieldIndex('date'))

    def setup_ui(self):

        form_layout = QFormLayout()
        # form_layout.addRow('Id', self.w_tp_id)
        form_layout.addRow('Máquina', self.w_maq)
        form_layout.addRow('Fecha', self.w_start_date)
        group_box = QGroupBox('Reprogramación')
        group_box.setLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.Save).setText('Guardar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.save)
        button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(group_box)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def save(self):
        tp_id = self.w_tp_id.value()
        machine = self.w_maq.currentText()
        date = self.w_start_date.date()

        self._query.bindValue(':tp_id', tp_id)
        self._query.bindValue(':machine', machine)
        self._query.bindValue(':date', date)

        self.executor(self._query, self.tp_model)

class ExtendTpForm(HandlerSql):

    def __init__(self, opc_model:QSqlTableModel, tp_mapper:QDataWidgetMapper):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.opc_model = opc_model
        self.tp_mapper = tp_mapper
        self.tp_model = tp_mapper.model()

        self._query = QSqlQuery()
        self._query.prepare('CALL create_childs(:parent, :machine, :date, :amount)')
        
        self.setup_widgets()
        self.setup_mappers()
        self.setup_ui()

    def setup_widgets(self):
        
        self.w_parent = QSpinBox()
        self.w_parent.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_parent.setReadOnly(True)
        self.w_parent.setMaximum(1000000000)

        self.w_maq = QComboBox()
        self.w_maq.addItems(MAQUINAS)
        # self.w_maq.setModel(self.opc_model)
        # self.w_maq.setModelColumn(self.opc_model.fieldIndex('machine'))

        self.w_start_date = QDateEdit()
        self.w_start_date.setDisplayFormat('dd/MM/yyyy')
        self.w_start_date.setCalendarPopup(True)
        self.w_start_date.setDate(QDate.currentDate())

        self.w_amount = QSpinBox()
        self.w_amount.setReadOnly(False)
        self.w_amount.setMinimum(1)
        self.w_amount.setMaximum(100000)

    def show(self) -> None:
        self.w_amount.setValue(1)
        return super().show()

    def setup_mappers(self):

        self.tp_mapper.addMapping(self.w_parent, self.tp_model.fieldIndex('parent'))
        self.tp_mapper.addMapping(self.w_maq, self.tp_model.fieldIndex('machine'))
        self.tp_mapper.addMapping(self.w_start_date, self.tp_model.fieldIndex('date'))

    def setup_ui(self):

        form_layout = QFormLayout()
        # form_layout.addRow('Id', self.w_parent)
        form_layout.addRow('Máquina', self.w_maq)
        form_layout.addRow('Inicio', self.w_start_date)
        form_layout.addRow('Duración', self.w_amount)
        group_box = QGroupBox('Reprogramación')
        group_box.setLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.Save).setText('Guardar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.save)
        button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(group_box)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def save(self):
        parent = self.w_parent.value()
        machine = self.w_maq.currentText()
        date = self.w_start_date.date()
        amount = self.w_amount.value()

        self._query.bindValue(':parent', parent)
        self._query.bindValue(':machine', machine)
        self._query.bindValue(':date', date)
        self._query.bindValue(':amount', amount)

        self.executor(self._query, self.tp_model)

class AddTpForm(HandlerSql):
    refresh_op_model = Signal()

    def __init__(self, tp_model:QSqlTableModel, opc_model:QSqlTableModel, hr_mapper:QDataWidgetMapper, iop_mapper:QDataWidgetMapper, rec_mapper:QDataWidgetMapper):
        super().__init__()

        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.tp_model = tp_model
        self.opc_model = opc_model
        self.hr_mapper = hr_mapper
        self.iop_mapper = iop_mapper
        self.rec_mapper = rec_mapper

        self.setup_widgets()
        self.setup_mappers()
        self.setup_ui()

        self._query = QSqlQuery()
        self._query.prepare('CALL create_parent_and_childs(:iop_id, :fname, :machine, :date, :cycles, :amount)')

    def setup_widgets(self):
        self.w_iop_id = QSpinBox()
        self.w_iop_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_iop_id.setReadOnly(True)
        self.w_iop_id.setMaximum(1000000)

        self.w_hr_id = QSpinBox()
        self.w_hr_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_hr_id.setReadOnly(True)
        self.w_hr_id.setMaximum(1000000)

        self.w_rec_id = QSpinBox()
        self.w_rec_id.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_rec_id.setReadOnly(True)
        self.w_rec_id.setMaximum(1000000)

        # self.w_material = QLineEdit()
        # self.w_material.setReadOnly(True)

        self.w_maq = QComboBox()
        self.w_maq.addItems(MAQUINAS)
        # self.w_maq.setModel(self.opc_model)
        # self.w_maq.setModelColumn(self.opc_model.fieldIndex('machine'))

        self.w_start_date = QDateEdit()
        self.w_start_date.setDisplayFormat('dd/MM/yyyy')
        self.w_start_date.setCalendarPopup(True)
        self.w_start_date.setDate(QDate.currentDate())

        self.w_amount = QSpinBox()
        self.w_amount.setReadOnly(True)
        self.w_amount.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_amount.setMinimum(1)
        self.w_amount.setMaximum(100000)

        self.w_fname = QLineEdit()
        self.w_fname.setReadOnly(True)

        self.w_formula = QLineEdit()
        self.w_formula.setReadOnly(True)

        self.w_hr = QLineEdit()
        self.w_hr.setReadOnly(True)

        self.w_maq_rec = QLineEdit()
        self.w_maq_rec.setReadOnly(True)

        self.w_units = QSpinBox()
        self.w_units.setReadOnly(True)
        self.w_units.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_units.setMaximum(1000000)

        self.w_cycles = QSpinBox()
        self.w_cycles.setReadOnly(True)
        self.w_cycles.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_cycles.setMaximum(1000000)

        self.w_overflow = QDoubleSpinBox()
        self.w_overflow.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_overflow.setReadOnly(True)
        self.w_overflow.setMaximum(1000000)
        self.w_overflow.setDecimals(1)

        self.w_hours = QDoubleSpinBox()
        self.w_hours.setReadOnly(True)
        self.w_hours.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_hours.setMaximum(1000000)
        self.w_hours.setDecimals(1)

        self.w_units_per_cycle = QSpinBox()
        self.w_units_per_cycle.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_units_per_cycle.setReadOnly(True)
        self.w_units_per_cycle.setMaximum(1000000)

        self.w_factor_bocas = QSpinBox()
        self.w_factor_bocas.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_factor_bocas.setReadOnly(True)
        self.w_factor_bocas.setMaximum(1000000)

        self.w_cycles_per_hour = QDoubleSpinBox()
        self.w_cycles_per_hour.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_cycles_per_hour.setReadOnly(True)
        self.w_cycles_per_hour.setMaximum(1000000)
        self.w_cycles_per_hour.setDecimals(2)

        self.w_weight = QDoubleSpinBox()
        self.w_weight.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_weight.setReadOnly(True)
        self.w_weight.setMaximum(1000000)
        self.w_weight.setDecimals(2)

        self.w_weight_per_cycle = QDoubleSpinBox()
        self.w_weight_per_cycle.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.w_weight_per_cycle.setReadOnly(True)
        self.w_weight_per_cycle.setMaximum(1000000)
        self.w_weight_per_cycle.setDecimals(3)

    def setup_mappers(self):

        iop_model = self.iop_mapper.model().sourceModel()
        self.iop_mapper.addMapping(self.w_iop_id, iop_model.fieldIndex('id'))
        self.iop_mapper.addMapping(self.w_fname, iop_model.fieldIndex('fname'))
        self.iop_mapper.addMapping(self.w_units, iop_model.fieldIndex('CM76_07'))

        rec_model = self.rec_mapper.model()
        self.rec_mapper.addMapping(self.w_rec_id, rec_model.fieldIndex('id'))

        hr_model = self.hr_mapper.model()
        self.hr_mapper.addMapping(self.w_hr_id, hr_model.fieldIndex('id'))
        self.hr_mapper.addMapping(self.w_hr, hr_model.fieldIndex('CM75_01'))
        self.hr_mapper.addMapping(self.w_formula, hr_model.fieldIndex('CM75_03'))
        self.hr_mapper.addMapping(self.w_weight_per_cycle, hr_model.fieldIndex('CM75_04'))
        self.hr_mapper.addMapping(self.w_cycles_per_hour, hr_model.fieldIndex('CM75_05'))
        self.hr_mapper.addMapping(self.w_units_per_cycle, hr_model.fieldIndex('CM75_06'))
        self.hr_mapper.addMapping(self.w_factor_bocas, hr_model.fieldIndex('CM75_48'))
        self.hr_mapper.addMapping(self.w_maq_rec, hr_model.fieldIndex('CM75_49'))

    def setup_ui(self):

        informacion_layout = QFormLayout()
        informacion_layout.addRow('Hoja de ruta', self.w_hr)
        informacion_layout.addRow('Fórmula', self.w_formula)
        informacion_layout.addRow('Peso/moldeada', self.w_weight_per_cycle)
        informacion_layout.addRow('Piezas/moldeada', self.w_units_per_cycle)
        informacion_layout.addRow('Moldeadas/hora', self.w_cycles_per_hour)
        informacion_layout.addRow('Factor de bocas', self.w_factor_bocas)
        informacion_layout.addRow('Máq. recomendada', self.w_maq_rec)
        self.informacion_group_box = QGroupBox('Información')
        self.informacion_group_box.setLayout(informacion_layout)

        estimaciones_layout = QFormLayout()
        estimaciones_layout.addRow('Piezas', self.w_units)
        estimaciones_layout.addRow('Moldeadas', self.w_cycles)
        # estimaciones_layout.addRow('Excedente [%]', self.w_overflow)
        estimaciones_layout.addRow('Peso [kg]', self.w_weight)
        estimaciones_layout.addRow('Tiempo [hs]', self.w_hours)
        estimaciones_layout.addRow('Jornadas', self.w_amount)
        self.estimaciones_group_box = QGroupBox('Previsto')
        self.estimaciones_group_box.setLayout(estimaciones_layout)

        programacion_layout = QFormLayout()
        # programacion_layout.addRow('Moldeadas a realizar', self.w_cycles)
        programacion_layout.addRow('Máquina', self.w_maq)
        programacion_layout.addRow('Inicio', self.w_start_date)
        # programacion_layout.addRow('Duración', self.w_amount)
        self.programacion_group_box = QGroupBox('Programación')
        self.programacion_group_box.setLayout(programacion_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.Save).setText('Guardar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.save)
        button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.informacion_group_box)
        layout.addWidget(self.estimaciones_group_box)
        layout.addWidget(self.programacion_group_box)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def set_values(self):
        try:
            cycles = ceil(self.w_factor_bocas.value() * self.w_units.value() / self.w_units_per_cycle.value())
        except ZeroDivisionError:
            cycles = 0
            weight = 0
            hours = 0
            amount = 1
        else:
            weight = cycles * self.w_weight_per_cycle.value()
            hours = cycles / self.w_cycles_per_hour.value()
            amount = hours // int(settings.value('Jornada laboral', defaultValue=10)) + 1

        self.w_cycles.setValue(cycles)
        self.w_weight.setValue(weight)
        self.w_hours.setValue(hours)
        self.w_amount.setValue(amount)

    def show(self) -> None:
        self.set_values()
        return super().show()

    def save(self):
        iop_id = self.w_iop_id.value()
        machine = self.w_maq.currentText()
        date = self.w_start_date.date()
        cycles = self.w_cycles.value()
        amount = self.w_amount.value()
        fname = self.w_fname.text()


        self._query.bindValue(':iop_id', iop_id)
        self._query.bindValue(':fname', fname)
        self._query.bindValue(':machine', machine)
        self._query.bindValue(':date', date)
        self._query.bindValue(':cycles', cycles)
        self._query.bindValue(':amount', amount)

        if not self.executor(self._query, self.tp_model):
            return
        self.refresh_op_model.emit()

class RecipeForm(QWidget):
    refresh_rec_proxy_model = Signal()

    def __init__(self, rec_model:QSqlTableModel, query: QSqlQuery):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)
        self.setFocus()
        
        self.rec_model = rec_model
        self._query = query
        self.setup_widgets()
        self.setup_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def setup_widgets(self):

        self.w_id = QSpinBox()
        self.w_id.setMaximum(1000000)

        self.w_hr = QLineEdit()
        regexp = QRegularExpressionValidator(r'\d{5}\/\d{2}$')
        self.w_hr.setValidator(regexp)

        self.w_sdesga1 = QSpinBox()
        self.w_sdesga1.setMaximum(1000000)

        self.w_sprecur1 = QSpinBox()
        self.w_sprecur1.setMaximum(1000000)

        self.w_spredes1a = QSpinBox()
        self.w_spredes1a.setMaximum(1000000)

        self.w_spredes1b = QSpinBox()
        self.w_spredes1b.setMaximum(1000000)

        self.w_spredes1c = QSpinBox()
        self.w_spredes1c.setMaximum(1000000)

        self.w_tinides = QDoubleSpinBox()
        self.w_tinides.setMaximum(1000000)
        self.w_tinides.setDecimals(1)

        self.w_tbaja1 = QDoubleSpinBox()
        self.w_tbaja1.setMaximum(1000000)
        self.w_tbaja1.setDecimals(1)

        self.w_tespe1 = QDoubleSpinBox()
        self.w_tespe1.setMaximum(1000000)
        self.w_tespe1.setDecimals(1)

        self.w_tcurado1 = QDoubleSpinBox()
        self.w_tcurado1.setMaximum(1000000)
        self.w_tcurado1.setDecimals(2)

        self.w_sptemp1i = QSpinBox()
        self.w_sptemp1i.setMaximum(1000000)

        self.w_sptemp1s = QSpinBox()
        self.w_sptemp1s.setMaximum(1000000)

        # self.w_sarrimes = QSpinBox()
        # self.w_sarrimes.setMaximum(1000000)

        # self.w_sparrmax = QSpinBox()
        # self.w_sparrmax.setMaximum(1000000)

        # self.w_sparrmin = QSpinBox()
        # self.w_sparrmin.setMaximum(1000000)

    def setup_ui(self):

        form_layout = QFormLayout()
        form_layout.addRow('Hoja de ruta', self.w_hr)
        form_layout.addRow('Temp. 1 superior [ºC]', self.w_sptemp1s)
        form_layout.addRow('Temp. 2 inferior [ºC]', self.w_sptemp1i)
        form_layout.addRow('Tiempo Comienzo Desgasaje [seg]', self.w_tinides)
        form_layout.addRow('Tiempo de Bajada [seg]', self.w_tbaja1)
        form_layout.addRow('Tiempo de Espera [seg]', self.w_tespe1)
        form_layout.addRow('Cantidad Desgasaje', self.w_sdesga1)
        form_layout.addRow('Tiempo Curado [min.seg]', self.w_tcurado1)
        form_layout.addRow('Presion desgasaje 1 [bar]', self.w_spredes1a)
        form_layout.addRow('Presion desgasaje 2 [bar]', self.w_spredes1b)
        form_layout.addRow('Presion desgasaje 3 [bar]', self.w_spredes1c)
        form_layout.addRow('Presion Curado [bar]', self.w_sprecur1)
        # form_layout.addRow('Arrimes', self.w_sarrimes)
        # form_layout.addRow('Arrimes Max.', self.w_sparrmax)
        # form_layout.addRow('Arrimes Min.', self.w_sparrmin)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.Save).setText('Guardar')

        button_box.button(QDialogButtonBox.Save).clicked.connect(self.save)
        button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def save(self):

        self._query.bindValue(':id', self.w_id.text())
        self._query.bindValue(':hr', self.w_hr.text())
        self._query.bindValue(':SDESGA1', self.w_sdesga1.value())
        self._query.bindValue(':SPRECUR1', self.w_sprecur1.value())
        self._query.bindValue(':SPREDES1a', self.w_spredes1a.value())
        self._query.bindValue(':SPREDES1b', self.w_spredes1b.value())
        self._query.bindValue(':SPREDES1c', self.w_spredes1c.value())
        self._query.bindValue(':TINIDES', self.w_tinides.value())
        self._query.bindValue(':TBAJA1', self.w_tbaja1.value())
        self._query.bindValue(':TESPE1', self.w_tespe1.value())
        self._query.bindValue(':TCURADO1', self.w_tcurado1.value())
        self._query.bindValue(':SPTEMP1i', self.w_sptemp1i.value())
        self._query.bindValue(':SPTEMP1s', self.w_sptemp1s.value())
        # self._query.bindValue(':SARRIMES', self.w_sarrimes.value())
        # self._query.bindValue(':SPARRMAX', self.w_sparrmax.value())
        # self._query.bindValue(':SPARRMIN', self.w_sparrmin.value())

        if not self._query.exec():
            print(self._query.lastError())
            if self._query.lastError().nativeErrorCode() == '1062':
                QMessageBox(
                    QMessageBox.Warning,
                    'Hoja de ruta duplicada',
                    'No puede realizar la acción porque la hoja de ruta introducida ya existe en la base de datos.',
                    QMessageBox.StandardButton.Ok,
                    parent=self
                ).exec()
            return False

        if not self.rec_model.submitAll():
            print(self._query.lastError())
            return False

        self.rec_model.layoutChanged.emit()
        self.refresh_rec_proxy_model.emit()
        self.close()

class NewRecipeForm(RecipeForm):
    def __init__(self, rec_model:QSqlTableModel):

        query = QSqlQuery()
        query.prepare('INSERT INTO receta(hr, SDESGA1, SPRECUR1, SPREDES1a, SPREDES1b, SPREDES1c, TINIDES, TBAJA1, TESPE1, TCURADO1, SPTEMP1i, SPTEMP1s) VALUES (:hr, :SDESGA1, :SPRECUR1, :SPREDES1a, :SPREDES1b, :SPREDES1c, :TINIDES, :TBAJA1, :TESPE1, :TCURADO1, :SPTEMP1i, :SPTEMP1s)')
        
        super().__init__(rec_model, query)
        
class EditRecipeForm(RecipeForm):

    def __init__(self, rec_mapper:QDataWidgetMapper):
        self.rec_mapper = rec_mapper
        query = QSqlQuery()
        query.prepare('UPDATE receta SET hr = :hr, SDESGA1 = :SDESGA1, SPRECUR1 = :SPRECUR1, SPREDES1a = :SPREDES1a, SPREDES1b = :SPREDES1b, SPREDES1c = :SPREDES1c, TINIDES = :TINIDES, TBAJA1 = :TBAJA1, TESPE1 = :TESPE1, TCURADO1 = :TCURADO1, SPTEMP1i = :SPTEMP1i, SPTEMP1s = :SPTEMP1s WHERE id = :id')
        
        super().__init__(rec_mapper.model(), query)
        # self.w_hr.setReadOnly(True)
        self.setup_mappers()

    def setup_mappers(self):

        self.rec_mapper.addMapping(self.w_id, self.rec_model.fieldIndex('id'))
        self.rec_mapper.addMapping(self.w_hr, self.rec_model.fieldIndex('hr'))
        self.rec_mapper.addMapping(self.w_sdesga1, self.rec_model.fieldIndex('SDESGA1'))
        self.rec_mapper.addMapping(self.w_sprecur1, self.rec_model.fieldIndex('SPRECUR1'))
        self.rec_mapper.addMapping(self.w_spredes1a, self.rec_model.fieldIndex('SPREDES1a'))
        self.rec_mapper.addMapping(self.w_spredes1b, self.rec_model.fieldIndex('SPREDES1b'))
        self.rec_mapper.addMapping(self.w_spredes1c, self.rec_model.fieldIndex('SPREDES1c'))
        self.rec_mapper.addMapping(self.w_tinides, self.rec_model.fieldIndex('TINIDES'))
        self.rec_mapper.addMapping(self.w_tbaja1, self.rec_model.fieldIndex('TBAJA1'))
        self.rec_mapper.addMapping(self.w_tespe1, self.rec_model.fieldIndex('TESPE1'))
        self.rec_mapper.addMapping(self.w_tcurado1, self.rec_model.fieldIndex('TCURADO1'))
        self.rec_mapper.addMapping(self.w_sptemp1i, self.rec_model.fieldIndex('SPTEMP1i'))
        self.rec_mapper.addMapping(self.w_sptemp1s, self.rec_model.fieldIndex('SPTEMP1s'))
        # self.rec_mapper.addMapping(self.w_sarrimes, self.rec_model.fieldIndex('SARRIMES'))
        # self.rec_mapper.addMapping(self.w_sparrmax, self.rec_model.fieldIndex('SPARRMAX'))
        # self.rec_mapper.addMapping(self.w_sparrmin, self.rec_model.fieldIndex('SPARRMIN'))

class RecipeEditor(QWidget):
    def __init__(self, rec_proxy_model:Models.RecProxyModel):
        super().__init__()
        self.rec_proxy_model = rec_proxy_model
        self.rec_model = rec_proxy_model.sourceModel()

        self.setMinimumHeight(480)
        self.setMinimumWidth(820)
        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.rec_mapper = QDataWidgetMapper()
        self.rec_mapper.setSubmitPolicy(QDataWidgetMapper.SubmitPolicy.ManualSubmit)
        self.rec_mapper.setOrientation(Qt.Orientation.Horizontal)
        self.rec_mapper.setModel(self.rec_model)

        self.table = QTableView()
        # self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.setModel(self.rec_proxy_model)
        self.table.resizeColumnsToContents()
        self.table.clicked.connect(self.updateSelection)
        self.table.horizontalHeader().sectionClicked.connect(self.sortTable)
        self.selectRow(0)
        
        # self.table = Views.RecView(self.rec_mapper)
        # self.table.setModel(self.rec_model)
        # for i in range(self.rec_model.columnCount()):
        #     self.table.setColumnWidth(i, 80)
        # self.delegate = Views.LineEditDelegate(hr_model, self.table)
        # self.table.setItemDelegateForColumn(self.rec_model.fieldIndex('Hoja de ruta'), self.delegate)
        # self.table.setItemDelegate(QSqlRelationalDelegate(self.table))


        self.new_recipe_form_window = NewRecipeForm(
            self.rec_model
        )
        self.new_recipe_form_window.refresh_rec_proxy_model.connect(self.rec_proxy_model.layoutChanged.emit)
        
        self.edit_recipe_form_window = EditRecipeForm(
            self.rec_mapper
        )

        button_box = QDialogButtonBox()

        delete_button = button_box.addButton('Eliminar', QDialogButtonBox.ButtonRole.ActionRole)
        edit_button = button_box.addButton('Editar', QDialogButtonBox.ButtonRole.ActionRole)
        create_button = button_box.addButton('Nuevo', QDialogButtonBox.ButtonRole.ActionRole)

        delete_button.clicked.connect(self.delete)
        edit_button.clicked.connect(self.edit)
        create_button.clicked.connect(self.new_recipe_form_window.show)


        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def sortTable(self, section):
        new_section = self.rec_proxy_model.to_source_sorting[section]
        self.table.sortByColumn(new_section, Qt.SortOrder.AscendingOrder)
        self.rec_proxy_model.layoutChanged.emit()

    def updateSelection(self, selectedIndex: QModelIndex):
        self.selectRow(selectedIndex.row())
        self.rec_proxy_model.layoutChanged.emit()

    def selectRow(self, row):
        self.rec_mapper.setCurrentIndex(row)
        self.table.selectRow(row)

    def edit(self):
        try:
            index = self.table.currentIndex()
        except IndexError:
            QMessageBox(
                QMessageBox.Warning,
                'Seleccionar receta',
                'Debe seleccionar una receta antes de proceder a la edición.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
        else:
            self.edit_recipe_form_window.show()

    def delete(self):
        try:
            index = self.table.currentIndex()
        except IndexError:
            QMessageBox(
                QMessageBox.Warning,
                'Seleccionar receta',
                'Debe seleccionar una receta antes de proceder a la eliminación.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
        else:
            query = QSqlQuery()
            query.prepare('DELETE FROM receta WHERE id = :id')
            modelIndex = self.rec_model.index(self.rec_mapper.currentIndex(), self.rec_model.fieldIndex('id'))
            query.bindValue(':id', modelIndex.data(Qt.ItemDataRole.DisplayRole))

            if not query.exec():
                print(query.lastError())
                return False

            msg = '¿Está seguro que desea eliminar la receta seleccionada?'
            dialog = QMessageBox(
                QMessageBox.Question,
                'Eliminar receta',
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                parent=self
            )
            if dialog.exec() == QMessageBox.StandardButton.No:
                self.rec_model.revertAll()
                return False

            if not self.rec_model.submitAll():
                print(query.lastError())
                return False

            self.rec_model.layoutChanged.emit()
            self.rec_proxy_model.layoutChanged.emit()
        
class GeneralSettings(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)

        self.setup_widgets()
        self.setup_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def setup_widgets(self):

        self.w_jornada = QSpinBox()
        self.w_jornada.setMinimum(1)
        self.w_jornada.setMaximum(12)

        # self.w_uri = QLineEdit()
        # self.w_endpoint = QLineEdit()
        # self.w_name = QLineEdit()
        # self.w_hostname = QLineEdit()
        # self.w_username = QLineEdit()
        # self.w_pwd = QLineEdit()
        self.w_database = QLineEdit()
        self.w_opc_client_ip = QLineEdit()

        self.w_db_port = QSpinBox()
        self.w_db_port.setMinimum(1)
        self.w_db_port.setMaximum(20000)

        self.w_opc_client_port = QSpinBox()
        self.w_opc_client_port.setMinimum(1)
        self.w_opc_client_port.setMaximum(20000)

        self.w_opc_server_port = QSpinBox()
        self.w_opc_server_port.setMinimum(1)
        self.w_opc_server_port.setMaximum(20000)



    def setup_ui(self):

        form_layout = QFormLayout()

        form_layout.addRow('Jornada laboral [hs]', self.w_jornada)
        form_layout.addRow('IP OPC server (remoto)', self.w_opc_client_ip)
        form_layout.addRow('Puerto OPC server (remoto)', self.w_opc_client_port)
        form_layout.addRow('Puerto OPC server (local)', self.w_opc_server_port)
        form_layout.addRow('Puerto de la base de datos', self.w_db_port)
        form_layout.addRow('Nombre de la base de datos', self.w_database)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.SaveAll,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.SaveAll).setText('Guardar')

        button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.apply)
        button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        # button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def show(self) -> None:
        self.get_values()
        return super().show()

    def get_values(self):
        self.w_jornada.setValue(int(settings.value('Jornada laboral', defaultValue=10)))
        # self.w_uri.setText(settings.value('HMI/OPC SERVER/uri', defaultValue="opc.tcp://localhost:4840/CAIPE OPC SERVER (HMI)"))
        # self.w_endpoint.setText(settings.value('PC/OPC SERVER/endpoint', defaultValue="opc.tcp://0.0.0.0:4841/pc/"))
        # self.w_name.setText(settings.value('PC/OPC SERVER/name', defaultValue="CAIPE OPC SERVER (PC)"))
        # self.w_hostname.setText(settings.value('PC/DB/hostname', defaultValue="localhost"))
        # self.w_username.setText(settings.value('PC/DB/username', defaultValue="pc"))
        # self.w_pwd.setText(settings.value('PC/DB/pwd', defaultValue="222222"))
        self.w_db_port.setValue(int(settings.value('PC/DB/port', defaultValue=3308)))
        self.w_opc_server_port.setValue(int(settings.value('PC/OPC/port', defaultValue=4841)))
        self.w_opc_client_port.setValue(int(settings.value('HMI/OPC/port', defaultValue=4840)))
        self.w_opc_client_ip.setText(settings.value('HMI/OPC/ip', defaultValue='localhost'))
        self.w_database.setText(settings.value('PC/DB/database', defaultValue="alergom_server"))

    def apply(self):
        settings.setValue('Jornada laboral', self.w_jornada.value())
        settings.setValue('HMI/OPC/ip', self.w_opc_client_ip.text())
        settings.setValue('HMI/OPC/port', self.w_opc_client_port.value())
        settings.setValue('PC/OPC/port', self.w_opc_server_port.value())
        settings.setValue('PC/DB/port', self.w_db_port.value())
        settings.setValue('PC/DB/database', self.w_database.text())
        self.close()

class BackUpWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)
        self.p = None
        self.setup_widgets()
        self.setup_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def setup_widgets(self):

        self.w_target_dir = QLineEdit()
        self.w_target_dir.setReadOnly(True)
        self.w_target_dir.setMinimumWidth(500)
        self.w_open_button = QPushButton()
        self.w_open_button.setIcon(QIcon(':/icons/folder-horizontal-open.png'))
        self.w_open_button.clicked.connect(self.open_dialog)
        self.w_plain_text = QPlainTextEdit()
        self.w_plain_text.setReadOnly(True)
        self.w_plain_text.setMinimumHeight(500)

    def open_dialog(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec():
            self.selected_path = dialog.selectedFiles()[0]
            self.w_target_dir.setText(self.selected_path)

    def setup_ui(self):

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.w_target_dir)
        hlayout.addWidget(self.w_open_button)

        form_layout = QFormLayout()
        form_layout.addRow('Seleccionar destino', hlayout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.SaveAll,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.SaveAll).setText('Guardar')

        button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.start_process)
        button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        # button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.w_plain_text)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def show(self) -> None:
        self.get_values()
        return super().show()

    def get_values(self):
        self.w_target_dir.setText(settings.value('PC/DB/backup', defaultValue="C:/"))

    def message(self, s):
        self.w_plain_text.appendPlainText(s)

    def start_process(self):
        if self.p is None:  # No process running.
            self.message("Executing process")
            self.p = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
            self.p.setWorkingDirectory("./sql") # no cambiar.
            self.p.readyReadStandardOutput.connect(self.handle_stdout)
            self.p.readyReadStandardError.connect(self.handle_stderr)
            self.p.stateChanged.connect(self.handle_state)
            self.p.finished.connect(self.process_finished)  # Clean up once complete.

            target_dir = self.w_target_dir.text()
            config_file = './../config.ini'
            user = 'root' # settings.value('PC/DB/username', defaultValue="root")
            pwd = 'root' # settings.value('PC/DB/pwd', defaultValue="root")
            args = [
                './auto_backup.ps1',
                '-target_dir', target_dir,
                '-c', config_file,
                '-u', user,
                '-p', pwd,
            ]
            self.p.start('pwsh', args)

    def handle_stderr(self):
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.message(stderr)

    def handle_stdout(self):
        data = self.p.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.message(stdout)

    def handle_state(self, state):
        states = {
            QProcess.NotRunning: 'Not running',
            QProcess.Starting: 'Starting',
            QProcess.Running: 'Running',
        }
        state_name = states[state]
        self.message(f"State changed: {state_name}")

    def process_finished(self):
        self.message("Process finished.")
        self.p = None
        QMessageBox(
            QMessageBox.Information,
            'Información',
            'El backup ha finalizado con éxito.',
            buttons=QMessageBox.Ok
        ).exec()
        self.close()

class RestoreWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowModality(Qt.WindowModal.ApplicationModal)
        self.p = None
        self.setup_widgets()
        self.setup_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            
    def setup_widgets(self):

        self.w_src_path = QLineEdit()
        self.w_src_path.setReadOnly(True)
        self.w_src_path.setMinimumWidth(500)
        self.w_label = QLabel('ATENCION: El backup seleccionado debe estar copiado localmente en la PC (no usar rutas de red para la restauración)')
        self.w_open_button = QPushButton()
        self.w_open_button.setIcon(QIcon(':/icons/folder-horizontal-open.png'))
        self.w_open_button.clicked.connect(self.open_dialog)
        self.w_plain_text = QPlainTextEdit()
        self.w_plain_text.setReadOnly(True)
        self.w_plain_text.setMinimumHeight(500)

    def open_dialog(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setNameFilter('.backup')
        if dialog.exec():
            self.w_src_path.setText(dialog.selectedFiles()[0][:-8]) # delete .backup

    def setup_ui(self):

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.w_src_path)
        hlayout.addWidget(self.w_open_button)

        form_layout = QFormLayout()
        form_layout.addRow('Seleccionar backup', hlayout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.SaveAll,
        )

        button_box.button(QDialogButtonBox.Cancel).setText('Cancelar')
        button_box.button(QDialogButtonBox.SaveAll).setText('Restaurar')

        button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.start_process)
        button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        # button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.w_label)
        layout.addWidget(self.w_plain_text)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def message(self, s):
        self.w_plain_text.appendPlainText(s)

    def start_process(self):
        if self.p is None:  # No process running.
            self.message("Executing process")
            self.p = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
            self.p.setWorkingDirectory("./sql") # no cambiar.
            self.p.readyReadStandardOutput.connect(self.handle_stdout)
            self.p.readyReadStandardError.connect(self.handle_stderr)
            self.p.stateChanged.connect(self.handle_state)
            self.p.finished.connect(self.process_finished)  # Clean up once complete.

            src_path = self.w_src_path.text()
            dst_path = settings.value('PC/DB/data_dir', defaultValue="C:\Program Files\MariaDB 10.6\data")
            config_file = './../config.ini'
            user = 'root' # settings.value('PC/DB/username', defaultValue="root")
            pwd = 'root' # settings.value('PC/DB/pwd', defaultValue="root")
            args = [
                './auto_restore.ps1',
                '-src_path', src_path,
                '-dst_path', dst_path,
                '-c', config_file,
                '-u', user,
                '-p', pwd,
            ]
            self.p.start('pwsh', args)

    def handle_stderr(self):
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.message(stderr)

    def handle_stdout(self):
        data = self.p.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.message(stdout)

    def handle_state(self, state):
        states = {
            QProcess.NotRunning: 'Not running',
            QProcess.Starting: 'Starting',
            QProcess.Running: 'Running',
        }
        state_name = states[state]
        self.message(f"State changed: {state_name}")

    def process_finished(self):
        self.message("Process finished.")
        self.p = None
        QMessageBox(
            QMessageBox.Information,
            'Información',
            'La restauración ha finalizado con éxito.\nReinicie el programa para aplicar los cambios.',
            buttons=QMessageBox.Ok
        ).exec()
        self.close()