import itertools
from typing import Dict, Optional, Union, Any
from datetime import datetime, timedelta
from PySide6.QtCore import *
import PySide6.QtCore
from PySide6.QtGui import *
from PySide6.QtSql import *
from PySide6.QtSql import *
from Constants import * 

class SelectorModel(QSqlTableModel):
    def __init__(self, table_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTable(table_name)
        self.select()

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

class OpItemProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setDynamicSortFilter(True)
        # self.setSortOrder(0, Qt.SortOrder.DescendingOrder)

    # def setSortOrder(self, column:int, order:Qt.SortOrder):
    #     self.order = order
    #     self.column = column
    #     self.layoutChanged.emit()
        
    def lessThan(self, source_left: Union[QModelIndex, QPersistentModelIndex], source_right: Union[QModelIndex, QPersistentModelIndex]) -> bool:
        model = self.sourceModel()
   
        if self.column == 11: # entrega
            left_date, right_date = source_left.data(), source_right.data()
            value = datetime.strptime(left_date, "%d/%m/%Y") < datetime.strptime(right_date, "%d/%m/%Y")
            return value 

        if self.column == 3: # emision
            if source_left.data() == source_right.data():
                left_date = source_left.siblingAtColumn(model.fieldIndex('CM76_10')).data()
                right_date = source_right.siblingAtColumn(model.fieldIndex('CM76_10')).data()
                value = datetime.strptime(left_date, "%d/%m/%Y") > datetime.strptime(right_date, "%d/%m/%Y")
                return value if self.order == Qt.SortOrder.DescendingOrder else not value
            left_date, right_date = source_left.data(), source_right.data()
            value = datetime.strptime(left_date, "%d/%m/%Y") < datetime.strptime(right_date, "%d/%m/%Y")
            return value 

        if source_left.data() == source_right.data():
            left_date = source_left.siblingAtColumn(model.fieldIndex('CM76_10')).data()
            right_date = source_right.siblingAtColumn(model.fieldIndex('CM76_10')).data()
            value = datetime.strptime(left_date, "%d/%m/%Y") > datetime.strptime(right_date, "%d/%m/%Y")
            return value if self.order == Qt.SortOrder.DescendingOrder else not value

        return super().lessThan(source_left, source_right)

class OpItemModel(QSqlTableModel):
    def __init__(self, op_model: QSqlTableModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.op_model = op_model
        self.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.setTable('orden_produccion_item')
        self.cols =  [0, 1, 3, 4, 5, 6, 7, 8, 11, 29]
        self.names = ['ID', 'OP', 'Emisión', 'Fórmula', 'Cliente', 'O/C', 'HR', 'Cantidad', 'Entrega', 'Máquinas']
        orients = len(self.cols) * [ Qt.Orientation.Horizontal ]
        list(map(self.setHeaderData, self.cols, orients, self.names))
        
    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        if index.column() in self.cols:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def data(self, idx: Union[QModelIndex, QPersistentModelIndex], role: int) -> Any:
        # https://stackoverflow.com/questions/70455959/inconsistent-behavior-of-qsqltablemodel-with-onrowsubmit
        # Me pasó lo del punto 2 de la URL.

        idx_id = idx.siblingAtColumn(self.fieldIndex('id'))
        iop_id = super().data(idx_id, role=Qt.ItemDataRole.DisplayRole) 

        idx_fname = idx.siblingAtColumn(self.fieldIndex('fname'))
        fname = super().data(idx_fname, role=Qt.ItemDataRole.DisplayRole)

        if role == Qt.ItemDataRole.DisplayRole:

            if idx.column() in (3, 11):
                date = super().data(idx, role)
                if date != '' and date is not None:
                    dt = datetime.strptime(date, '%Y%m%d')
                    return dt.strftime('%d/%m/%Y')

        if role == Qt.ItemDataRole.BackgroundRole or role == Qt.ItemDataRole.ForegroundRole:
            idx_op = self.find_op_index(iop_id, fname)
            if idx_op.isValid():
                childs = idx_op.siblingAtColumn(self.op_model.fieldIndex('childs')).data(Qt.ItemDataRole.DisplayRole)
                finished_childs = idx_op.siblingAtColumn(self.op_model.fieldIndex('finished_childs')).data(Qt.ItemDataRole.DisplayRole)
                if finished_childs >= childs:
                    return QBrush(Qt.darkGreen) if role == Qt.ItemDataRole.BackgroundRole else QBrush(Qt.GlobalColor.white)# all tps finished
                elif finished_childs > 0:
                    return QBrush(Qt.darkYellow) if role == Qt.ItemDataRole.BackgroundRole else QBrush(Qt.GlobalColor.white) # some tps finished
                return QBrush(Qt.gray) if role == Qt.ItemDataRole.BackgroundRole else QBrush(Qt.GlobalColor.white) # any tps finished (programming)
        return super().data(idx, role)

    def find_op_index(self, iop_id, fname) -> QModelIndex: 
        start = self.op_model.index(0, self.op_model.fieldIndex('iop_id'))
        op_indexes = self.op_model.match(start, Qt.ItemDataRole.DisplayRole, iop_id, hits=1, flags=Qt.MatchFlag.MatchExactly)
        if len(op_indexes) == 0:
            return QModelIndex()
        for ix in op_indexes:
            if ix.siblingAtColumn(self.op_model.fieldIndex('fname')).data(Qt.ItemDataRole.DisplayRole) == fname:
                return ix
        return QModelIndex()

    def find_iop_index(self, iop_id, fname) -> QModelIndex: 
        start = self.index(0, self.fieldIndex('id'))
        iop_indexes = self.match(start, Qt.ItemDataRole.DisplayRole, iop_id, hits=1, flags=Qt.MatchFlag.MatchExactly)
        if len(iop_indexes) == 0:
            return QModelIndex()
        for ix in iop_indexes:
            if ix.siblingAtColumn(self.fieldIndex('fname')).data(Qt.ItemDataRole.DisplayRole) == fname:
                return ix
        return QModelIndex()
    
class RecModel(QSqlTableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.setTable('receta')
        self.select()


class OpeModel(SelectorModel):
    def __init__(self, *args, **kwargs):
        super().__init__(table_name = 'operario', *args, **kwargs)

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        
        if role == Qt.ItemDataRole.DecorationRole:
            return QColor(COLORES[index.row() % len(COLORES)])
        
        return super().data(index, role)
class TpActiveModel(SelectorModel):
    def __init__(self, *args, **kwargs):
        super().__init__(table_name = 'active_tp', *args, **kwargs)
    
    def is_active(self, machine):
        start = self.index(0, self.fieldIndex('machine'))
        ix = self.match(start, Qt.ItemDataRole.DisplayRole, machine, hits=1, flags=Qt.MatchFlag.MatchExactly)[0]
        tp_id = ix.siblingAtColumn(self.fieldIndex('tp_id')).data(Qt.ItemDataRole.DisplayRole)
        # print(ix, machine, ix.siblingAtColumn(self.fieldIndex('tp_id')), tp_id)
        return tp_id > 0

class RecProxyModel(QAbstractProxyModel):
    def __init__(self, model, parent: QObject = None ) -> None:
        super().__init__(parent)
        self.setSourceModel(model)
        self.from_source_sorting = (0,1,7,12,9,10,11,4,5,6,8,3,2,13,14,15,16,17)
        self.to_source_sorting = (0,1,12,11,7,8,9,2,10,4,5,6,3,13,14,15,16,17)
        self.hheader = [
            'ID',
            'Hoja de ruta',
            'Temp. 1\nsuperior\n[ºC]',
            'Temp. 2\ninferior\n[ºC]',
            'Tiempo\nComienzo\nDesgasaje\n[seg]',
            'Tiempo\nde\nBajada\n[seg]',
            'Tiempo\nde\nEspera\n[seg]',
            'Cantidad\nDesgasaje',
            'Tiempo\nCurado\n[min.seg]',
            'Presion\ndesgasaje 1\n[bar]',
            'Presion\ndesgasaje 2\n[bar]',
            'Presion\ndesgasaje 3\n[bar]',
            'Presion\nCurado\n[bar]',
            'Arrimes',
            'Arrimes\nMax.',
            'Arrimes\nMin.',
            'Libre 1',
            'Libre 2'
        ]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return self.sourceModel().rowCount(parent)
    
    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return 13

    def is_root_index(self, index:QModelIndex):
        if index.row() == -1 and index.column() == -1:
            return True
        return False
    
    def fieldIndex(self, fieldName):
        return self.to_source_sorting[self.sourceModel().fieldIndex(fieldName)]
    
    def index(self, row: int, column: int, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> QModelIndex:
        # return self.sourceModel().index(row, self.to_source_sorting[column], parent)
        return self.createIndex(row, column)

    def parent(self, index: QModelIndex):
        return self.createIndex(-1, -1)

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.hheader[section]
        return super().headerData(section, orientation, role)
    
    def mapFromSource(self, sourceIndex: QModelIndex | QPersistentModelIndex) -> QModelIndex:
        if self.is_root_index(sourceIndex):
            return QModelIndex()
        return sourceIndex.siblingAtColumn(self.from_source_sorting[sourceIndex.column()])
    
    def mapToSource(self, proxyIndex: QModelIndex | QPersistentModelIndex) -> QModelIndex:
        if self.is_root_index(proxyIndex):
            return QModelIndex()
        return self.sourceModel().index(proxyIndex.row(), self.to_source_sorting[proxyIndex.column()])

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        source_index = self.mapToSource(index)
        if self.is_root_index(source_index):
            return None
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        
        return super().data(index, role)
    
class OpModel(QSqlRelationalTableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.setTable('orden_programada')
        self.select()

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable  | Qt.ItemFlag.ItemIsEditable
    
class TpModel(QSqlTableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.setTable('tarea_programada')
        self.select()

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
    
class OpcModel(QAbstractTableModel):
    def __init__(self, tp_active_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = [ VARIABLES_SIZE * [0] for _ in MAQUINAS]
        self._hheader = ('Moldeadas','T. marcha','T. parada')
        self.tp_active_model = tp_active_model
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._hheader[section]
            if orientation == Qt.Orientation.Vertical:
                return MAQUINAS[section]
            
        return super().headerData(section, orientation, role)

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return MAQUINAS_SIZE

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return VARIABLES_SIZE

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def get_vars(self, machine):
        section = MAQUINAS.index(machine)
        return self._data[section]

    def set_vars(self, machine, values):
        section = MAQUINAS.index(machine)
        self._data[section] = values
        left_ix = self.index(section, 0)
        right_ix = self.index(section, VARIABLES_SIZE-1)
        self.dataChanged.emit(left_ix, right_ix)

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        row, col = index.row(), index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[row][col]
        
        if role in (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole):
            if self.tp_active_model.is_active(MAQUINAS[row]):
                return QBrush(Qt.darkGreen) if role == Qt.ItemDataRole.BackgroundRole else QBrush(Qt.GlobalColor.white)
        return None
    
    def update(self):
        self.tp_active_model.select()
        self.layoutChanged.emit()

class CalendarModel(QSqlQueryModel):
    def __init__(self, db, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db
        self._span = None
        self.start_date = None
        self.fieldIndex = dict(
            id=0,
            _row=1,
            _col=2,
            _offset=3,
        )
        # count_tps = cantidad de TPs por fecha y maquina en el rango de fechas del calendario.
        # max_tps = cantidad maxima de TPs por maquina
        self._query = QSqlQuery(db)
        # self._query.prepare(
        #     'CALL create_calendar(:start_date, :span)'
        # )
        self._query.prepare(
            """
                WITH count_tps AS (
                    SELECT 
                        tp.machine,
                        tp.date,
                        COUNT(tp.id) AS _count
                    FROM tarea_programada as tp
                    WHERE tp.date BETWEEN :start_date AND ADDDATE(:start_date, :span)
                    GROUP BY tp.machine, tp.date
                ), max_tps AS (
                    SELECT 
                        machine,
                        MAX(_count) AS amount
                    FROM count_tps
                    GROUP BY machine
                ), acum_tps AS (
                    SELECT
                        machine,
                        CAST(SUM(amount) OVER (ORDER BY machine ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)  AS INT) AS acum
                    FROM max_tps
                ), offset_tps AS (
                    SELECT
                        machine,
                        COALESCE(LAG(acum_tps.acum, 1) OVER (ORDER BY acum_tps.machine), 0) AS _offset
                    FROM acum_tps
                )
                SELECT 
                    tp.id as tp_id,
                    tp.priority + offset_tps._offset as _row,
                    CAST(DATEDIFF(tp.date, :start_date) AS INT) AS _col,
                    offset_tps._offset AS _offset
                FROM tarea_programada as tp
                INNER JOIN offset_tps ON offset_tps.machine = tp.machine
                WHERE tp.date BETWEEN :start_date AND ADDDATE(:start_date, :span);
            """
        )

    def refresh(self, v : Union[int, QDate]):
        if isinstance(v, int):
            self._span = v
            self._query.bindValue(':span', v)
        elif isinstance(v, QDate):
            self.start_date = v.toString('yyyy-MM-dd')
            self._query.bindValue(':start_date', self.start_date)

        self._query.exec()
        self.setQuery(self._query)
        err = self.lastError()
        if err.isValid():
            raise ValueError(err)
        self.layoutChanged.emit()

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

class CalendarProxyModel(QAbstractProxyModel):
    span_signal = Signal(int, int, int)

    def __init__(self, tp_model:QSqlTableModel, opc_model:OpcModel, ope_model:OpeModel, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.tp_model = tp_model
        self.ope_model = ope_model
        self.opc_model = opc_model
        self.mac_colors = itertools.cycle(COLORES)
        self.actual_color = None

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        source_model = self.sourceModel()

        if orientation == Qt.Orientation.Horizontal:
            if source_model.start_date is None:
                return
            start_date = datetime.strptime(source_model.start_date, '%Y-%m-%d')
            actual_date = start_date + timedelta(days=section)
            if role == Qt.ItemDataRole.DisplayRole:
                return actual_date.strftime('%A\n%d/%m')
            if role == Qt.ItemDataRole.ForegroundRole and actual_date.weekday() > 4 :
                return QBrush(Qt.GlobalColor.red)
            

        if orientation == Qt.Orientation.Vertical:
            start = source_model.index(0, source_model.fieldIndex['_row'])
            try:
                source_index = source_model.match(start, Qt.ItemDataRole.DisplayRole, section, flags=Qt.MatchFlag.MatchExactly)[0]
            except IndexError:
                raise ValueError('FATAL ERROR')
            _offset = source_index.siblingAtColumn(source_model.fieldIndex['_offset']).data()
            priority = section - _offset
            if role == Qt.ItemDataRole.DisplayRole:
                if priority == 0:
                    tp_index = self.sourceToTpModel(source_index)
                    return tp_index.siblingAtColumn(self.tp_model.fieldIndex('machine')).data(Qt.ItemDataRole.DisplayRole)
                return ''
            # if role == Qt.ItemDataRole.BackgroundRole:
            #     if priority == 0:
            #         self.actual_color = next(self.mac_colors)
            #     print(self.actual_color)
            #     return QBrush(self.actual_color)


        return super().headerData(section, orientation, role)

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        source_model = self.sourceModel()
        start = source_model.index(0,source_model.fieldIndex['_row'])
        rows = [ source_model.data(start.siblingAtRow(r), Qt.ItemDataRole.DisplayRole) for r in range(source_model.rowCount()) ]
        return 0 if len(rows) == 0 else max(rows) + 1

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        source_model = self.sourceModel()
        return 0 if source_model._span is None else source_model._span

    def mapFromSource(self, sourceIndex: Union[QModelIndex, QPersistentModelIndex]) -> QModelIndex:
        if self.is_root_index(sourceIndex):
            return QModelIndex()
        source_model = self.sourceModel()
        row = source_model.data(sourceIndex.siblingAtColumn(source_model.fieldIndex['_row']))
        col = source_model.data(sourceIndex.siblingAtColumn(source_model.fieldIndex['_col']))
        proxyIndex = self.createIndex(row, col)
        return proxyIndex

    def mapToSource(self, proxyIndex: Union[QModelIndex, QPersistentModelIndex]) -> QModelIndex:
        if self.is_root_index(proxyIndex):
            return QModelIndex()

        source_model = self.sourceModel()
        proxy_row = proxyIndex.row()
        start = source_model.index(0,source_model.fieldIndex['_row'])
        source_indexes = source_model.match(start, Qt.ItemDataRole.DisplayRole, proxy_row, hits=-1, flags=Qt.MatchFlag.MatchExactly)
        if len(source_indexes) == 0:
            return QModelIndex()
        
        col = proxyIndex.column()
        for ix in source_indexes:
            source_index = ix.siblingAtColumn(source_model.fieldIndex['_col'])
            _col = source_model.data(source_index, role=Qt.ItemDataRole.DisplayRole)
            if _col == col:
                return source_index
        
        return QModelIndex()

    def index(self, row: int, column: int, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> QModelIndex:
        return self.createIndex(row, column)

    def parent(self, index: QModelIndex):
        return self.createIndex(-1, -1)

    def sourceToTpModel(self, sourceIndex:QModelIndex) -> QModelIndex:
        source_model = self.sourceModel()
        tp_id = sourceIndex.siblingAtColumn(source_model.fieldIndex['id']).data(Qt.ItemDataRole.DisplayRole)
        start = self.tp_model.index(0, 0)
        try:
            ix = self.tp_model.match(start, Qt.ItemDataRole.DisplayRole, tp_id, flags=Qt.MatchFlag.MatchExactly)[0]
        except IndexError:
            print(sourceIndex)
            raise ValueError('FATAL ERROR')
        return ix

    def data(self, proxyIndex: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        source_index = self.mapToSource(proxyIndex)
        if self.is_root_index(source_index):
            return None

        tp_index = self.sourceToTpModel(source_index)

        op = tp_index.siblingAtColumn(self.tp_model.fieldIndex('op_id')).data()
        hr = tp_index.siblingAtColumn(self.tp_model.fieldIndex('hr')).data()
        tp_id = tp_index.siblingAtColumn(self.tp_model.fieldIndex('id')).data()
        ope = tp_index.siblingAtColumn(self.tp_model.fieldIndex('operator')).data()
        status = tp_index.siblingAtColumn(self.tp_model.fieldIndex('status')).data()
        cycles = tp_index.siblingAtColumn(self.tp_model.fieldIndex('cycles')).data()
        saved_cycles = tp_index.siblingAtColumn(self.tp_model.fieldIndex('saved_cycles')).data()
        acum_cycles = tp_index.siblingAtColumn(self.tp_model.fieldIndex('acum_cycles')).data()
        total_cycles = tp_index.siblingAtColumn(self.tp_model.fieldIndex('total_cycles')).data()
        machine = tp_index.siblingAtColumn(self.tp_model.fieldIndex('machine')).data()

        if role == Qt.ItemDataRole.DisplayRole:
            if status == 1: # tarea programada activa
                rt_cycles, _, _ = self.opc_model.get_vars(machine)
                if rt_cycles is None:
                    rt_cycles = 0
                acum_cycles += rt_cycles
                total_cycles += rt_cycles
                # return '\n'.join([hr, f'RT: {rt_cycles}', f'A: {acum_cycles}', f'AT: {total_cycles}', f'T: {cycles}'])
                return '\n'.join([hr, f'{rt_cycles}/{acum_cycles}', f'{total_cycles}/{cycles}'])
            
            # return '\n'.join([hr, f'U: {saved_cycles}', f'A: {acum_cycles}', f'AT: {total_cycles}', f'T: {cycles}'])
            return '\n'.join([hr, f'{saved_cycles}/{acum_cycles}', f'{total_cycles}/{cycles}'])


        if role == Qt.ItemDataRole.DecorationRole:
            if status == 2: # tarea programada finalizada
                return QIcon(':/icons/flag-checker.png')
            if status == 1: # tarea programada activa
                return QIcon(':/icons/status.png')
            if saved_cycles > 0:
                return QIcon(':/icons/status-away.png')
            if status == 0: # tarea programada finalizada
                return QIcon(':/icons/status-offline.png')

        if role == Qt.ItemDataRole.BackgroundRole:
            if ope != '' and status != 2:

                start = self.ope_model.index(0, self.ope_model.fieldIndex('CM70_03'))
                ope_index = self.ope_model.match(start, Qt.ItemDataRole.DisplayRole, ope, hits=1, flags=Qt.MatchFlag.MatchExactly)
                return QBrush(COLORES[ope_index[0].row() % len(COLORES)]) if len(ope_index) > 0 else QBrush(Qt.GlobalColor.gray)
            return QBrush(Qt.GlobalColor.white)

        if role == Qt.ItemDataRole.ToolTipRole:
            if ope != '':
                return ope
            
        if role == Qt.ItemDataRole.ForegroundRole:
            if ope != '' and status != 2:
                return QBrush(Qt.GlobalColor.white)
            return QBrush(Qt.GlobalColor.black)

        return super().data(proxyIndex, role)
    
    def is_root_index(self, index:QModelIndex):
        if index.row() == -1 and index.column() == -1:
            return True
        return False
    
    def get_machine_of_row(self, proxy_index: QModelIndex):
        source_model = self.sourceModel()
        row = proxy_index.row()
        start =  source_model.index(0, source_model.fieldIndex['_row'])
        try:
            source_index = source_model.match(start, Qt.ItemDataRole.DisplayRole, row, flags=Qt.MatchFlag.MatchExactly)[0]
        except IndexError:
            print(proxy_index)
            raise ValueError('FATAL ERROR')
        tp_index = self.sourceToTpModel(source_index)
        return tp_index.siblingAtColumn(self.tp_model.fieldIndex('machine')).data(Qt.ItemDataRole.DisplayRole)

    def get_date(self, proxy_index:QModelIndex):
        source_model = self.sourceModel()
        col = proxy_index.column()
        # source_model.start_date
        start_date = datetime.strptime(source_model.start_date, '%Y-%m-%d')
        _date = start_date + timedelta(days=col)
        return _date.strftime('%Y-%m-%d')

class HrModel(QSqlTableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.setTable('hoja_de_ruta')
        self.select()

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
