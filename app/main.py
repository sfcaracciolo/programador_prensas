# nuitka-project: --standalone
# nuitka-project: --msvc=14.3
# nuitka-project: --low-memory
# nuitka-project: --jobs=1
# nuitka-project: --lto=no
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-qt-plugins=sqldrivers
# nuitka-project: --windows-icon-from-ico=E:\Repositorios\programador_prensas\app\resources\app.ico
# nuitka-project: --windows-disable-console
# nuitka-project: --windows-uac-admin
# nuitka-project: --windows-company-name=CAIPE
# nuitka-project: --windows-product-name=PRODUCCION - ALERGOM
# nuitka-project: --windows-product-version=0.0.0.2

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from asyncio import exceptions
import logging
import sys
from datetime import datetime

logging.basicConfig(filename='app.log',
                    filemode='a',
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S',
                    level=logging.INFO)
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtSql import *
import Models, Views, Constants, Windows
from UaClient import UaClient
from asyncua import ua, sync
import resources
import locale

QCoreApplication.setOrganizationName("CAIPE")
QCoreApplication.setOrganizationDomain("caipe.com.ar")
QCoreApplication.setApplicationName("ALERGOM - Produccion")
QLocale.setDefault(QLocale('es_AR'))
locale.setlocale(locale.LC_ALL, "es_AR") #

class OpcClientWorker(QObject):

    server_status = Signal(dict)
    com_error = Signal(object)
    data_change_fired = Signal(object, object, str)

    def __init__(self):
        super(OpcClientWorker, self).__init__()

    def datachange_notification(self, node, val, data):
        if data.monitored_item.Value.SourceTimestamp:
            dato = data.monitored_item.Value.SourceTimestamp.isoformat()
        elif data.monitored_item.Value.ServerTimestamp:
            dato = data.monitored_item.Value.ServerTimestamp.isoformat()
        else:
            dato = datetime.now().isoformat()
        self.data_change_fired.emit(node, val, dato)

    def make_subscriptions(self):
        nodes = self.uaclient.client.nodes.root.get_child(
            [
                "0:Objects",
                "2:MODBUS RTU",
                "2:Tags",
                "2:Variables"
            ]
        ).get_children()
        for node in nodes:
            try:
                self.uaclient.subscribe_datachange(node, self)
            except Exception as exc:
                raise ValueError(exc)
        self._subscribed_nodes.append(nodes)
        return True

    @Slot(str)
    def set_machine_offline(self, machine):
        nodes = [
            self.uaclient.get_node(f'ns=2;s=MODBUS RTU.Tags.Estados.{machine}'), # set offline status
        ]
        values = [
            ua.DataValue(ua.Variant(0, ua.VariantType.UInt16))
        ]
        self.write_values(nodes, values)
        
    @Slot(str, list)
    def set_machine_online(self, machine, recipe_values):
        nodes = [
            self.uaclient.get_node(f'ns=2;s=MODBUS RTU.Tags.Recetas.{machine}'), # load recipe
            self.uaclient.get_node(f'ns=2;s=MODBUS RTU.Tags.Variables.{machine}'), # reset counters
            self.uaclient.get_node(f'ns=2;s=MODBUS RTU.Tags.Estados.{machine}'), # set online status
        ]
        values = [
            ua.DataValue(ua.Variant(recipe_values, ua.VariantType.UInt16)),
            ua.DataValue(ua.Variant(Constants.VARIABLES_SIZE*[0], ua.VariantType.UInt16)),
            ua.DataValue(ua.Variant(1, ua.VariantType.UInt16))
        ]
        self.write_values(nodes, values)

    def write_values(self, nodes, values):
        try:
            codes = self.uaclient.client.write_values(nodes, values)
        except Exception as exc:
            print(exc)
            return self.com_error.emit(exc)
        
    def check_status(self):
        if not self.uaclient._connected:
            self.server_data['is_connected'] = False
            self.server_data['msg'] = f'Connecting to server ({self.retries})'
            self.server_status.emit(self.server_data)
            try:
                self.uaclient.connect(self.uri)
            except exceptions.TimeoutError:
                self.retries += 1
            else:
                if not self.make_subscriptions():
                    self.uaclient.disconnect()
                    self.retries += 1
                else:
                    self.retries = 0
                    self.server_data['is_connected'] = True
                    self.server_data['msg'] = f'Connected to server'
                    self.server_status.emit(self.server_data)
        else:
            node = self.uaclient.get_node('i=2256') #server status var
            try:
                node.read_value()
            except ConnectionError as exc:
                self.uaclient.disconnect()
                self._subscribed_nodes = []

    def stop(self):
        self.timer.stop()
        self.uaclient.disconnect()

    @Slot()
    def start(self):
        # Store constructor arguments (re-used for processing)
        self.uaclient = UaClient()
        self._subscribed_nodes = []
        self.server_data = {}

        ip = Constants.settings.value('HMI/OPC/ip', defaultValue="localhost")
        port = Constants.settings.value('HMI/OPC/port', defaultValue='4840')
        self.uri = f'opc.tcp://{ip}:{port}/hmi/'
        self.retries = 0 

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.check_status)
        self.timer.start()

class OpcServerWorker(QObject):

    data_change_fired = Signal(object, object, str)

    def __init__(self):
        super(OpcServerWorker, self).__init__()

    def datachange_notification(self, node, val, data):
        if data.monitored_item.Value.SourceTimestamp:
            dato = data.monitored_item.Value.SourceTimestamp.isoformat()
        elif data.monitored_item.Value.ServerTimestamp:
            dato = data.monitored_item.Value.ServerTimestamp.isoformat()
        else:
            dato = datetime.now().isoformat()
        self.data_change_fired.emit(node, val, dato)
        

    def build_data_model(self):
        uri = "http://caipe.com.ar"
        idx = self.server.register_namespace(uri)

        recetas_group = self.server.nodes.objects.add_folder(idx, "Recetas")
        init_values =  Constants.RECETA_SIZE * [ 0 ]
        for name in Constants.MAQUINAS[:-3]:
            node = recetas_group.add_variable(idx, name, ua.Variant(init_values, ua.VariantType.UInt16))
            # Tuve que agregar write_value_rank y write_array_dimensions en sync.py https://github.com/FreeOpcUa/opcua-asyncio/discussions/500
            node.write_value_rank(1)
            node.write_array_dimensions([Constants.RECETA_SIZE])
            node.set_writable()

            # subscribo el server a los cambios de las recetas confirmados desde el HMI.
            sub = self.server.create_subscription(500, self)
            sub.subscribe_data_change(node)

    def start(self):

        self.server = sync.Server()
        port = Constants.settings.value('PC/OPC/port', defaultValue="4841")
        self.server.set_endpoint(f'opc.tcp://0.0.0.0:{port}')
        self.server.set_server_name('pc')
        # setup our own namespace, not really necessary but should as spec
        self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

        self.build_data_model()
        self.server.start()

    def stop(self):
        self.server.stop()

class MainWindow(QMainWindow):
    update_iop_status_color = Signal(object)
    set_machine_online = Signal(str, list)
    set_machine_offline = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.db = QSqlDatabase.addDatabase("QMARIADB")
        self.db.setHostName("localhost")
        self.db.setUserName("prod_soft")
        self.db.setPassword("111111")
        self.db.setPort(int(Constants.settings.value('PC/DB/port', defaultValue=3308)))
        self.db.setDatabaseName(Constants.settings.value('PC/DB/database', defaultValue="caipe_server"))

        if not self.db.open():
            raise self.sql_error(self.db.lastError())

        self.setup_models()
        self.setup_actions()
        self.setup_mappers()
        self.setup_windows()
        self.setup_ui()
        self.setup_callbacks()
        self.setup_queries()

        self.opc_client_worker = OpcClientWorker()

        self.opc_client_thread = QThread()
        self.opc_client_worker.moveToThread(self.opc_client_thread)
        self.opc_client_thread.started.connect(self.opc_client_worker.start)
        self.opc_client_thread.finished.connect(self.opc_client_worker.stop)

        self.opc_client_worker.data_change_fired.connect(self.subscription_remote_server_nodes_callback)
        self.opc_client_worker.server_status.connect(self.server_status_changed)
        self.opc_client_worker.com_error.connect(self.opc_error)
        self.set_machine_online.connect(self.opc_client_worker.set_machine_online)
        self.set_machine_offline.connect(self.opc_client_worker.set_machine_offline)

        self.opc_client_thread.start()


        self.opc_server_worker = OpcServerWorker()
        self.opc_server_worker.data_change_fired.connect(self.subscription_local_server_nodes_callback)

        self.opc_server_thread = QThread()
        self.opc_server_worker.moveToThread(self.opc_server_thread)
        self.opc_server_thread.started.connect(self.opc_server_worker.start)
        self.opc_server_thread.finished.connect(self.opc_server_worker.stop)

        self.opc_server_thread.start()

        # self.watcher = QFileSystemWatcher()
        # self.watcher.addPath('\\\\SAN-NB\Backup 25-03-2022\COS76000.dbf')
        # self.watcher.fileChanged.connect(self.iop_model.select)

        self.w_span_date.setValue(15)
        self.w_start_date.setDate(QDate.currentDate())
        self.opc_table_dock.hide()
        # self.top_splitter.restoreState(settings.value("splitterSizes"))

        self.update_iop_list_action.trigger()

    def setup_queries(self):
        delete_op_query = QSqlQuery()
        delete_op_query.prepare('CALL delete_op(:tp_id)')

        delete_tp_query = QSqlQuery()
        delete_tp_query.prepare('CALL delete_tp(:tp_id)')

        self.delete_queries = {
            'op': delete_op_query,
            'tp': delete_tp_query,
        }

        up_priority_query = QSqlQuery()
        up_priority_query.prepare('CALL up_priority(:tp_id)')

        down_priority_query = QSqlQuery()
        down_priority_query.prepare('CALL down_priority(:tp_id)')

        self.priority_queries = {
            'up': up_priority_query,
            'down': down_priority_query,
        }

        self.set_status_query = QSqlQuery()
        fields = str.join(',', [ f':{v}' for v in Constants.VARIABLES])
        self.set_status_query.prepare(f'CALL set_status(:tp_id, :status, {fields})')

        self.update_recipe_query = QSqlQuery()
        fields = str.join(',', [ f':{v}' for v in Constants.RECETA])
        self.update_recipe_query.prepare(f'CALL update_recipe(:machine, {fields})')

        # self.update_opc_data_query = QSqlQuery()
        # fields = str.join(',', [ f':{v}' for v in Constants.VARIABLES])
        # self.update_opc_data_query.prepare(f'CALL update_opc_data(:machine, {fields})')

    def setup_windows(self):

        self.tp_form_window = Windows.AddTpForm(
            self.tp_model,
            self.opc_model,
            self.hr_mapper,
            self.iop_mapper,
            self.rec_mapper,
        )

        self.extended_tp_form_window = Windows.ExtendTpForm(
            self.opc_model,
            self.tp_mapper,
        )

        self.edit_cycles_form_window = Windows.EditCyclesForm(
            self.tp_mapper,
        )

        self.move_tp_form_window = Windows.MoveTpForm(
            self.opc_model,
            self.tp_mapper,
        )

        self.add_comment_form_window = Windows.AddCommentForm(
            'update_comment',
            self.iop_mapper
        )

        self.add_group_comment_form_window = Windows.AddCommentForm(
            'bulk_update_comment',
            self.iop_mapper
        )

        self.forward_date_form_window = Windows.ShiftDateTpForm(
            'forward_shift',
            self.tp_model,
        )

        self.backward_date_form_window = Windows.ShiftDateTpForm(
            'backward_shift',
            self.tp_model,
        )

        self.ope_assignment_form_window = Windows.OpeAssigTpForm(
            'update_ope',
            self.ope_model,
            self.tp_mapper,
        )

        self.ope_group_assignment_form_window = Windows.OpeAssigTpForm(
            'bulk_update_ope',
            self.ope_model,
            self.tp_mapper,
        )

        self.recipe_viewer_window = Windows.RecipeEditor(
            self.rec_proxy_model,
        )

        self.settings_window = Windows.GeneralSettings()

        self.backup_window = Windows.BackUpWindow()
        self.restore_window = Windows.RestoreWindow()

    def setup_mappers(self):

        self.iop_mapper = QDataWidgetMapper()
        self.iop_mapper.setSubmitPolicy(QDataWidgetMapper.SubmitPolicy.ManualSubmit)
        self.iop_mapper.setOrientation(Qt.Orientation.Horizontal)
        self.iop_mapper.setModel(self.iop_proxy_model)

        # self.op_mapper = QDataWidgetMapper()
        # self.op_mapper.setOrientation(Qt.Orientation.Horizontal)
        # self.op_mapper.setModel(self.op_model)

        self.tp_mapper = QDataWidgetMapper()
        self.tp_mapper.setSubmitPolicy(QDataWidgetMapper.SubmitPolicy.ManualSubmit)
        self.tp_mapper.setOrientation(Qt.Orientation.Horizontal)
        self.tp_mapper.setModel(self.tp_model)

        self.hr_mapper = QDataWidgetMapper()
        self.hr_mapper.setSubmitPolicy(QDataWidgetMapper.SubmitPolicy.ManualSubmit)
        self.hr_mapper.setOrientation(Qt.Orientation.Horizontal)
        self.hr_mapper.setModel(self.hr_model)

        self.rec_mapper = QDataWidgetMapper()
        self.rec_mapper.setSubmitPolicy(QDataWidgetMapper.SubmitPolicy.ManualSubmit)
        self.rec_mapper.setOrientation(Qt.Orientation.Horizontal)
        self.rec_mapper.setModel(self.rec_model)

    def setup_models(self):

        self.op_model = Models.OpModel(db=self.db)
        self.iop_model = Models.OpItemModel(self.op_model, db=self.db)
        self.iop_proxy_model = Models.OpItemProxyModel()
        self.iop_proxy_model.setSourceModel(self.iop_model)

        self.tp_model = Models.TpModel(db=self.db)
        self.rec_model = Models.RecModel(db=self.db)
        self.rec_proxy_model = Models.RecProxyModel(self.rec_model)

        self.hr_model = Models.HrModel(db=self.db)
        self.opc_model = Models.OpcModel()
        self.ope_model = Models.SelectorModel('operario', db=self.db)

        self.calendar_model = Models.CalendarModel(db=self.db)
        self.calendar_proxy_model = Models.CalendarProxyModel(
            self.tp_model,
            self.opc_model
        )
        self.calendar_proxy_model.setSourceModel(self.calendar_model)

    def setup_callbacks(self):
        self.tp_form_window.sql_error.connect(self.sql_error)
        self.extended_tp_form_window.sql_error.connect(self.sql_error)
        self.move_tp_form_window.sql_error.connect(self.sql_error)
        self.forward_date_form_window.sql_error.connect(self.sql_error)
        self.backward_date_form_window.sql_error.connect(self.sql_error)
        self.ope_assignment_form_window.sql_error.connect(self.sql_error)
        self.ope_group_assignment_form_window.sql_error.connect(self.sql_error)
        
        self.tp_form_window.refresh_op_model.connect(self.refresh_op_model)

        self.tp_model.layoutChanged.connect(self.calendar_model.refresh)
        self.w_span_date.valueChanged.connect(self.calendar_model.refresh)
        self.w_start_date.dateChanged.connect(self.calendar_model.refresh)
        self.calendar_model.layoutChanged.connect(self.calendar_proxy_model.layoutChanged.emit)

        self.update_iop_status_color.connect(self.update_iop_status)
        self.add_group_comment_form_window.update_iop_list_data.connect(self.update_iop_list)

        # self.iop_panel.table.horizontalHeader().sortIndicatorChanged.connect(self.iop_proxy_model.setSortOrder)
        # self.show_progress_bar.connect(self.open_progress)
        # self.hide_progress_bar.connect(self.close_progress)
        # self.top_splitter.splitterMoved.connect(self.save_state)

    # @Slot(int, int)
    # def save_state(self, pos, ix):
    #     settings.setValue("splitterSizes", self.top_splitter.saveState())

    def setup_ui(self):

        self.iop_panel = Views.OpItemView(self.iop_mapper)
        self.iop_panel.table.setModel(self.iop_proxy_model)

        self.opc_table = QTableView()
        self.opc_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.opc_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.opc_table.setModel(self.opc_model)
        self.opc_table.resizeColumnsToContents()

        self.calendar_table = Views.CalendarWidget()
        self.calendar_table.setModel(self.calendar_proxy_model)

        self.w_span_date = QSpinBox()
        self.w_span_date.setMaximum(60)
        
        self.w_start_date = QDateEdit()
        self.w_start_date.setDisplayFormat('dd/MM/yy')
        self.w_start_date.setCalendarPopup(True)
        self.w_start_date.setMinimumWidth(100)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        
        # self.top_splitter = QSplitter()
        # self.top_splitter.setOrientation(Qt.Orientation.Horizontal)
        # self.top_splitter.addWidget(self.iop_table)
        # self.top_splitter.addWidget(self.calendar_table)

        self.iop_panel_dock = QDockWidget()
        self.iop_panel_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.iop_panel_dock.setWidget(self.iop_panel)
        self.iop_panel_dock.setMinimumWidth(600)
        self.iop_panel_dock.setTitleBarWidget(QLabel('Órdenes de producción'))
        self.toggle_view_iop_panel_action = self.iop_panel_dock.toggleViewAction()
        self.toggle_view_iop_panel_action.setIcon(QIcon(':/icons/clipboard-list.png'))
        self.toggle_view_iop_panel_action.setToolTip('Mostrar/ocultar órdenes de producción')

        self.opc_table_dock = QDockWidget()
        self.opc_table_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.opc_table_dock.setWidget(self.opc_table)
        self.opc_table_dock.setTitleBarWidget(QLabel('Máquinas en tiempo real'))
        self.toggle_view_opc_table_action = self.opc_table_dock.toggleViewAction()
        self.toggle_view_opc_table_action.setIcon(QIcon(':/icons/application-monitor.png'))
        self.toggle_view_opc_table_action.setToolTip('Mostrar/ocultar variables de las máquinas en tiempo real')

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.iop_panel_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.opc_table_dock)
        
        # separators = [ QAction() for _ in range(3) ]
        # list(map(lambda s: s.setSeparator(True), separators))

        tool_bar = QToolBar()
        tool_bar.addActions(
            [
                self.update_iop_list_action,
                self.recipe_editor_action,
                self.settings_action,
                self.toggle_view_iop_panel_action,
                self.toggle_view_opc_table_action,
            ]
        )
        tool_bar.addSeparator()
        tool_bar.addActions(
            [
                self.add_tp_action,
                self.extend_tp_action,
                self.move_tp_action,
                self.edit_cycles_action,
                self.forward_date_action,
                self.backward_date_action,
                self.up_priority_action,
                self.down_priority_action,
            ]
        )
        tool_bar.addSeparator()
        tool_bar.addActions(
            [
                self.add_comment_action,
                self.add_group_comment_action,
                self.ope_assignment_action,
                self.ope_group_assignment_action,
                self.delete_tp_action,
                self.delete_op_action,
            ]
        )
        tool_bar.addSeparator()
        tool_bar.addActions(
            [
                self.play_tp_action,
                self.finish_tp_action,
                self.restore_tp_action,
                # self.info_tp_action,
                # self.update_lotes_action,
            ]
        )

        tool_bar.addSeparator()
        tool_bar.addActions(
            [
                self.backup_action,
                self.restore_action,
            ]
        )

        spacer_widget = QWidget()
        spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tool_bar.addWidget(spacer_widget)

        tool_bar.addWidget(self.w_start_date)
        tool_bar.addWidget(self.w_span_date)
        self.addToolBar(tool_bar)

        self.setCentralWidget(self.calendar_table)

    def setup_actions(self):
        self.add_tp_action = QAction()
        self.add_tp_action.setIcon(QIcon(':/icons/plus.png'))
        self.add_tp_action.setToolTip('Programar OP (nueva)')
        self.add_tp_action.triggered.connect(self.add_tp_form)

        self.update_iop_list_action = QAction()
        self.update_iop_list_action.setIcon(QIcon(':/icons/arrow-circle-double-135.png'))
        self.update_iop_list_action.setToolTip('Actualizar lista de OPs')
        self.update_iop_list_action.triggered.connect(self.update_iop_list)

        self.settings_action = QAction()
        self.settings_action.setIcon(QIcon(':/icons/gear.png'))
        self.settings_action.setToolTip('Parámetros del sistema')
        self.settings_action.triggered.connect(self.open_settings)

        self.extend_tp_action = QAction()
        self.extend_tp_action.setIcon(QIcon(':/icons/hammer--plus.png'))
        self.extend_tp_action.setToolTip('Reprogramar OP (extender)')
        self.extend_tp_action.triggered.connect(self.extend_tp_form)

        self.move_tp_action = QAction()
        self.move_tp_action.setIcon(QIcon(':/icons/hammer--arrow.png'))
        self.move_tp_action.setToolTip('Reprogramar OP (mover)')
        self.move_tp_action.triggered.connect(self.move_tp_form)

        self.edit_cycles_action = QAction()
        self.edit_cycles_action.setIcon(QIcon(':/icons/hammer--pencil.png'))
        self.edit_cycles_action.setToolTip('Cambiar cantidad de moldeadas')
        self.edit_cycles_action.triggered.connect(self.edit_cycles_form)

        self.forward_date_action = QAction()
        self.forward_date_action.setIcon(QIcon(':/icons/calendar-next.png'))
        self.forward_date_action.setToolTip('Retrasar programación')
        self.forward_date_action.triggered.connect(self.forward_date_form)

        self.backward_date_action = QAction()
        self.backward_date_action.setIcon(QIcon(':/icons/calendar-previous.png'))
        self.backward_date_action.setToolTip('Adelantar programación')
        self.backward_date_action.triggered.connect(self.backward_date_form)

        self.delete_tp_action = QAction()
        self.delete_tp_action.setIcon(QIcon(':/icons/eraser.png'))
        self.delete_tp_action.setToolTip('Eliminar OP (selección)')
        self.delete_tp_action.triggered.connect(lambda: self.delete('tp'))

        self.delete_op_action = QAction()
        self.delete_op_action.setIcon(QIcon(':/icons/eraser--plus.png'))
        self.delete_op_action.setToolTip('Eliminar OP (grupo)')
        self.delete_op_action.triggered.connect(lambda: self.delete('op'))

        self.up_priority_action = QAction()
        self.up_priority_action.setIcon(QIcon(':/icons/arrow-270.png'))
        self.up_priority_action.setToolTip('Bajar OP')
        self.up_priority_action.triggered.connect(lambda: self.change_priority('up'))

        self.down_priority_action = QAction()
        self.down_priority_action.setIcon(QIcon(':/icons/arrow-090.png'))
        self.down_priority_action.setToolTip('Subir OP')
        self.down_priority_action.triggered.connect(lambda: self.change_priority('down'))

        self.ope_assignment_action = QAction()
        self.ope_assignment_action.setIcon(QIcon(':/icons/hard-hat.png'))
        self.ope_assignment_action.setToolTip('Asignar operario (selección)')
        self.ope_assignment_action.triggered.connect(self.ope_assignment_form)

        self.ope_group_assignment_action = QAction()
        self.ope_group_assignment_action.setIcon(QIcon(':/icons/hard-hat--plus.png'))
        self.ope_group_assignment_action.setToolTip('Asignar operario (grupo)')
        self.ope_group_assignment_action.triggered.connect(self.ope_group_assignment_form)

        self.play_tp_action = QAction()
        self.play_tp_action.setIcon(QIcon(':/icons/control.png'))
        self.play_tp_action.setToolTip('Activar OP')
        self.play_tp_action.triggered.connect(lambda: self.change_status(1))

        self.finish_tp_action = QAction()
        self.finish_tp_action.setIcon(QIcon(':/icons/flag-checker.png'))
        self.finish_tp_action.setToolTip('Finalizar OP')
        self.finish_tp_action.triggered.connect(lambda: self.change_status(2))

        self.restore_tp_action = QAction()
        self.restore_tp_action.setIcon(QIcon(':/icons/arrow-curve-180-left.png'))
        self.restore_tp_action.setToolTip('Restaurar OP')
        self.restore_tp_action.triggered.connect(lambda: self.change_status(0))

        self.recipe_editor_action = QAction()
        self.recipe_editor_action.setIcon(QIcon(':/icons/table--plus.png'))
        self.recipe_editor_action.setToolTip('Editor de recetas')
        self.recipe_editor_action.triggered.connect(self.recipe_editor_form)

        self.backup_action = QAction()
        self.backup_action.setIcon(QIcon(':/icons/drive-download.png'))
        self.backup_action.setToolTip('BackUp de la base de datos')
        self.backup_action.triggered.connect(self.open_backup)

        self.restore_action = QAction()
        self.restore_action.setIcon(QIcon(':/icons/drive-upload.png'))
        self.restore_action.setToolTip('Restauración de la base de datos')
        self.restore_action.triggered.connect(self.open_restore)

        # self.info_tp_action = QAction()
        # self.info_tp_action.setIcon(QIcon(':/icons/information.png'))
        # self.info_tp_action.triggered.connect(self.info_tp_form)

        # self.update_lotes_action = QAction()
        # self.update_lotes_action.setIcon(QIcon(':/icons/drawer.png'))
        # self.update_lotes_action.triggered.connect(self.update_lotes)

        self.add_comment_action = QAction()
        self.add_comment_action.setIcon(QIcon(':/icons/balloon.png'))
        self.add_comment_action.setToolTip('Añadir observación')
        self.add_comment_action.triggered.connect(self.add_comment)

        self.add_group_comment_action = QAction()
        self.add_group_comment_action.setIcon(QIcon(':/icons/balloon--plus.png'))
        self.add_group_comment_action.setToolTip('Añadir observación (grupo)')
        self.add_group_comment_action.triggered.connect(self.add_group_comment)

    def open_settings(self):
        self.settings_window.show()

    def open_backup(self):
        self.backup_window.show()

    def open_restore(self):
        self.restore_window.show()

    def update_iop_list(self):
        try:
            iop_index = self.iop_panel.table.selectedIndexes()[0]
        except IndexError:
            if not self.iop_model.select():
                self.sql_error(self.iop_model.lastError())
                return
        else:
            iop_id = iop_index.siblingAtColumn(self.iop_model.fieldIndex('id')).data(Qt.ItemDataRole.DisplayRole)
            fname = iop_index.siblingAtColumn(self.iop_model.fieldIndex('fname')).data(Qt.ItemDataRole.DisplayRole)
            if not self.iop_model.select():
                self.sql_error(self.iop_model.lastError())
                return
            new_iop_index = self.iop_model.find_iop_index(iop_id, fname)
            self.iop_panel.table.setCurrentIndex(new_iop_index)
        finally:
            # self.setEnabled(False)
            self.iop_panel.table.resizeColumnsToContents()
            # self.setEnabled(True)
            self.iop_panel.table.sort()

    @Slot(dict)
    def server_status_changed(self, data):
        # uncomment in production
        # self.setEnabled(data['is_connected'])
        self.status_bar.showMessage(data['msg'])
        
    def add_tp_form(self):
        try:
            iop_index = self.iop_panel.table.selectedIndexes()[0]
        except IndexError:
            QMessageBox(
                QMessageBox.Warning,
                'Selección vacía',
                'Debe seleccionar una fila ejecutar el comando.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
        else:

            hr_cod = iop_index.siblingAtColumn(self.iop_model.fieldIndex('CM76_06')).data(Qt.ItemDataRole.DisplayRole)
            start = self.hr_model.index(0, self.hr_model.fieldIndex('CM75_01'))
            try:
                hr_index = self.hr_model.match(start, Qt.ItemDataRole.DisplayRole, hr_cod, hits=1, flags=Qt.MatchFlag.MatchExactly)[0]
            except IndexError:
                QMessageBox(
                    QMessageBox.Critical,
                    'Hoja de ruta inexistente',
                    'La hoja de ruta asociada a la orden de producción seleccionada no existe en la base de datos.',
                    QMessageBox.StandardButton.Ok,
                    parent=self
                ).exec()
                return

            start = self.rec_model.index(0,self.rec_model.fieldIndex('hr'))
            try:
                hr_cod_letterless = hr_cod[:8]# format without letters.
                rec_index = self.rec_model.match(start, Qt.ItemDataRole.DisplayRole, hr_cod_letterless, hits=1, flags=Qt.MatchFlag.MatchExactly)[0]
            except IndexError:
                QMessageBox(
                    QMessageBox.Critical,
                    'Fórmula inexistente',
                    'La fórmula asociada a la hoja de ruta seleccionada no existe en la base de datos.',
                    QMessageBox.StandardButton.Ok,
                    parent=self
                ).exec()
                return


            iop_id = iop_index.siblingAtColumn(self.iop_model.fieldIndex('id')).data(role=Qt.ItemDataRole.DisplayRole) 
            fname = iop_index.siblingAtColumn(self.iop_model.fieldIndex('fname')).data(role=Qt.ItemDataRole.DisplayRole) 
            idx_op = self.iop_model.find_op_index(iop_id, fname)
            if idx_op.isValid():
                QMessageBox(
                    QMessageBox.Critical,
                    'Tarea programada',
                    'La orden de producción seleccionada ya se encuentra programada.',
                    QMessageBox.StandardButton.Ok,
                    parent=self
                ).exec()
                return
            
            # self.iop_mapper.setCurrentIndex(iop_index.row())
            self.hr_mapper.setCurrentIndex(hr_index.row())
            self.rec_mapper.setCurrentIndex(rec_index.row())

            self.tp_form_window.show()

    def add_comment(self):
        try:
            iop_index = self.iop_panel.table.selectedIndexes()[0]
        except IndexError:
            QMessageBox(
                QMessageBox.Warning,
                'Selección vacía',
                'Debe seleccionar una fila ejecutar el comando.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
        else:
            self.add_comment_form_window.show()

    def add_group_comment(self):
        try:
            iop_index = self.iop_panel.table.selectedIndexes()[0]
        except IndexError:
            QMessageBox(
                QMessageBox.Warning,
                'Selección vacía',
                'Debe seleccionar una fila ejecutar el comando.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
        else:
            self.add_group_comment_form_window.show()
    
    def refresh_op_model(self):
        if not self.op_model.select():
            self.sql_error(self.op_model.lastError())
            return

    def extend_tp_form(self):
        source_index = self.calendar_tp_selection()
        if source_index is None:
            return
        self.extended_tp_form_window.show()

    def edit_cycles_form(self):
        source_index = self.calendar_tp_selection()
        if source_index is None:
            return
        self.edit_cycles_form_window.show()
            
    def move_tp_form(self):
        source_index = self.calendar_tp_selection()
        if source_index is None:
            return
        self.move_tp_form_window.show()

    def forward_date_form(self):
        calendar_index = self.calendar_selection()
        if calendar_index is None:
            return

        self.forward_date_form_window.machine = self.calendar_proxy_model.get_machine_of_row(calendar_index)
        self.forward_date_form_window.date = self.calendar_proxy_model.get_date(calendar_index)
        self.forward_date_form_window.show()

    def backward_date_form(self):
        calendar_index = self.calendar_selection()
        if calendar_index is None:
            return

        self.backward_date_form_window.machine = self.calendar_proxy_model.get_machine_of_row(calendar_index)
        self.backward_date_form_window.date = self.calendar_proxy_model.get_date(calendar_index)
        self.backward_date_form_window.show()

    # def open_op_info(self):
    #     try:
    #         index = self.iop_panel.table.selectedIndexes()[0]
    #     except IndexError:
    #         QMessageBox(
    #             QMessageBox.Warning,
    #             'Selección vacía',
    #             'Debe seleccionar una fila ejecutar el comando.',
    #             QMessageBox.StandardButton.Ok,
    #             parent=self
    #         ).exec()
    #     else:
    #         iop_id = index.siblingAtColumn(0).data()
    #         start = self.view_models.opinfo.index(0,0)
    #         model_row = self.view_models.opinfo.match(start, Qt.ItemDataRole.DisplayRole, iop_id, hits=1)[0].row()
    #         self.opinfo_mapper.setCurrentIndex(model_row)
    #         self.op_info_window.show()

    # def open_op_lotes(self):
    #     try:
    #         index = self.iop_panel.table.selectedIndexes()[0]
    #     except IndexError:
    #         QMessageBox(
    #             QMessageBox.Warning,
    #             'Selección vacía',
    #             'Debe seleccionar una fila ejecutar el comando.',
    #             QMessageBox.StandardButton.Ok,
    #             parent=self
    #         ).exec()
    #     else:
    #         iop_id = index.siblingAtColumn(0).data()
    #         start = self.iop_model.index(0,0)
    #         model_row = self.iop_model.match(start, Qt.ItemDataRole.DisplayRole, iop_id, hits=1)[0].row()
    #         self.oplotes_mapper.setCurrentIndex(model_row)
    #         self.op_lotes_window.show()

    def calendar_selection(self):
        try:
            calendar_index = self.calendar_table.selectionModel().selectedIndexes()[0]
        except IndexError:
            QMessageBox(
                QMessageBox.Warning,
                'Selección vacía',
                'Debe seleccionar una tarea programada para ejecutar el comando.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
            return None
        return calendar_index

    def calendar_tp_selection(self, skip_mapper = False):

        calendar_index = self.calendar_selection()
        if calendar_index is None:
            return None

        source_index = self.calendar_proxy_model.mapToSource(calendar_index)
        if self.calendar_proxy_model.is_root_index(source_index):
            QMessageBox(
                QMessageBox.Warning,
                'Selección vacía',
                'Debe seleccionar una tarea programada para ejecutar el comando.',
                QMessageBox.StandardButton.Ok,
                parent=self
            ).exec()
            return None

        if not skip_mapper:
            tp_index = self.calendar_proxy_model.sourceToTpModel(source_index)
            self.tp_mapper.setCurrentIndex(tp_index.row())
        
        return source_index

    def delete(self, xp):
        
        source_index = self.calendar_tp_selection(skip_mapper = True)
        if source_index is None:
            return
        
        msg = '¿Está seguro que desea eliminar la tarea programada seleccionada?' if xp == 'tp' else '¿Está seguro que desea eliminar la tarea programada y todo su grupo asociado?'
        dialog = QMessageBox(
            QMessageBox.Question,
            'Eliminar tarea programada',
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            parent=self
        )
        if dialog.exec() == QMessageBox.StandardButton.No:
            return

        tp_index = self.calendar_proxy_model.sourceToTpModel(source_index)

        tp_id = tp_index.siblingAtColumn(self.tp_model.fieldIndex('id')).data(Qt.ItemDataRole.DisplayRole)
        self.delete_queries[xp].bindValue(':tp_id', tp_id)

        if not self.delete_queries[xp].exec():
            self.sql_error(self.delete_queries[xp].lastError())
            return

        if not self.tp_model.submitAll():
            self.sql_error(self.tp_model.lastError())
            return

        self.tp_model.layoutChanged.emit()
        
        if not self.op_model.select():
            self.sql_error(self.op_model.lastError())
            return

    def sql_error(self, sql_obj: QSqlError):
        err = sql_obj.text()
        QMessageBox(
            QMessageBox.Critical,
            'ERROR SQL',
            f'El programa se cerrará automáticamente debido a la desconexión de la base de datos.\n Msg: {err}',
            QMessageBox.StandardButton.Ok,
            parent=self
        ).exec()
        raise ConnectionError(self.close())

    def change_status(self, new_status):

        source_index = self.calendar_tp_selection(skip_mapper = True)
        if source_index is None:
            return

        tp_index = self.calendar_proxy_model.sourceToTpModel(source_index)
        tp_id = tp_index.siblingAtColumn(self.tp_model.fieldIndex('id')).data(Qt.ItemDataRole.DisplayRole)
        status = tp_index.siblingAtColumn(self.tp_model.fieldIndex('status')).data(Qt.ItemDataRole.DisplayRole)
        print(f'{tp_id}: {status} -> {new_status}')
        machine = tp_index.siblingAtColumn(self.tp_model.fieldIndex('machine')).data(Qt.ItemDataRole.DisplayRole)
        self.opc_model.set_vars(machine, Constants.VARIABLES_SIZE*[None])

        cycles, ton, toff = self.opc_model.get_vars(machine)
        self.set_status_query.bindValue(':tp_id', tp_id)
        self.set_status_query.bindValue(':status', new_status)
        self.set_status_query.bindValue(':cycles', cycles)
        self.set_status_query.bindValue(':ton', ton)
        self.set_status_query.bindValue(':toff', toff)

        if not self.set_status_query.exec():
            self.sql_error(self.set_status_query.lastError())
            return

        if not self.tp_model.submitAll():
            self.sql_error(self.tp_model.lastError())
            return

        self.tp_model.layoutChanged.emit()
        self.update_iop_status_color.emit(tp_index)
        
        if machine[:3] == 'PRE':
            if new_status == 1:
                    recipe_values = self.get_recipe(tp_index)
                    self.set_machine_online.emit(machine, recipe_values)
            elif status == 1: # (new_status in (0, 2))
                self.set_machine_offline.emit(machine)


    
    @Slot(object)
    def update_iop_status(self, tp_index: QModelIndex):
        # self.op_model.select()

        parent = tp_index.siblingAtColumn(self.tp_model.fieldIndex('parent')).data(Qt.ItemDataRole.DisplayRole)
        op_ix = self.get_op_index(parent)
        self.op_model.selectRow(op_ix.row())

        iop_id = op_ix.siblingAtColumn(self.op_model.fieldIndex('iop_id')).data(Qt.ItemDataRole.DisplayRole)
        iop_ix_left = self.get_iop_index(iop_id)
        iop_ix_right = iop_ix_left.siblingAtColumn(-1)
        self.iop_proxy_model.dataChanged.emit(iop_ix_left, iop_ix_right, [Qt.ItemDataRole.BackgroundRole])
        # self.iop_proxy_model.layoutChanged.emit()

    def get_iop_index(self, id) -> QModelIndex:
        start = self.iop_model.index(0, self.iop_model.fieldIndex('id'))
        ix = self.iop_model.match(start, Qt.ItemDataRole.DisplayRole, id, hits=1, flags=Qt.MatchFlag.MatchExactly)[0]
        return ix

    def get_op_index(self, id) -> QModelIndex:
        start = self.op_model.index(0, self.op_model.fieldIndex('id'))
        ix = self.op_model.match(start, Qt.ItemDataRole.DisplayRole, id, hits=1, flags=Qt.MatchFlag.MatchExactly)[0]
        return ix

    @Slot(object)
    def opc_error(self, exc):
        if isinstance(exc, ua.uaerrors._auto.BadNoCommunication):
            msg = 'No hay comunicación entre el HMI y el PLC.'
        elif isinstance(exc, AttributeError):
            msg = 'No hay comunicacion entre la PC y el HMI.'
        else:
            msg = 'Falla de comunicación desconocida.'

        QMessageBox(
            QMessageBox.Critical,
            'ERROR COM',
            msg,
            QMessageBox.StandardButton.Ok,
            parent=self
        ).exec()

    def change_priority(self, dir):
        source_index = self.calendar_tp_selection(skip_mapper = True)
        if source_index is None:
            return
        tp_index = self.calendar_proxy_model.sourceToTpModel(source_index)
        tp_id = tp_index.siblingAtColumn(self.tp_model.fieldIndex('id')).data(Qt.ItemDataRole.DisplayRole)
        self.priority_queries[dir].bindValue(':tp_id', tp_id)

        if not self.priority_queries[dir].exec():
            self.sql_error(self.priority_queries[dir].lastError())
            return

        if not self.tp_model.select():
            self.sql_error(self.tp_model.lastError())
            return

        self.tp_model.layoutChanged.emit()

    def ope_assignment_form(self):
        source_index = self.calendar_tp_selection()
        if source_index is None:
            return
        self.ope_assignment_form_window.show()

    def ope_group_assignment_form(self):
        source_index = self.calendar_tp_selection()
        if source_index is None:
            return
        self.ope_group_assignment_form_window.show()

    def recipe_editor_form(self):
        if not self.rec_model.select():
            self.sql_error(self.rec_model.lastError())
            return

        self.recipe_viewer_window.show()

    def info_tp_form(self):
        pass 

    def update_lotes(self):
        pass

    def get_recipe(self, tp_index: QModelIndex):
        hr = tp_index.siblingAtColumn(self.tp_model.fieldIndex('hr')).data()
        start = self.rec_model.index(0,self.rec_model.fieldIndex('hr'))
        try:
            rec_index = self.rec_model.match(start, Qt.ItemDataRole.DisplayRole, hr, hits=1)[0]
        except IndexError:
            raise ValueError('FATAL ERROR')

        r = self.rec_model.record(rec_index.row())
        values = [10**r.field(i).precision() * r.field(i).value() for i in range(2, r.count())]
        return list(map(int, values))

    def subscription_local_server_nodes_callback(self, nodeid, values, timestamp):
        if values == Constants.RECETA_SIZE * [0]:
            return

        machine = self.opc_server_worker.server.get_node(nodeid.nodeid).read_display_name().Text
        # print('local server', machine, values)

        self.update_recipe_query.bindValue(':machine', machine)
        for k, v in zip(Constants.RECETA, values):
            self.update_recipe_query.bindValue(f':{k}', v)
        
        if not self.update_recipe_query.exec():
            self.sql_error(self.update_recipe_query.lastError())
            return

        if not self.rec_model.select():
            self.sql_error(self.rec_model.lastError())
            return
        
    def subscription_remote_server_nodes_callback(self, node:sync.SyncNode, values, timestamp):
        machine = node.read_display_name().Text

        if values is None:
            logging.warning(f'COM error between HMI and machine {machine}')
            return
        # print(machine, values)
        self.opc_model.set_vars(machine, list(map(int, values)))
        self.calendar_proxy_model.layoutChanged.emit()

    def closeEvent(self, event):

        self.opc_server_thread.quit()
        self.opc_server_thread.wait()

        self.opc_client_thread.quit()
        self.opc_client_thread.wait()

        event.accept()

if __name__ == "__main__":

    app = QApplication(sys.argv)
    pixmap = QPixmap(':/img/splash.png')
    splash = QSplashScreen(pixmap)
    splash.show()

    logging.info('INICIO app.')
    # app.setWindowIcon(QIcon(':/img/app.ico'))
    splash.showMessage("Cargando programa ...", alignment=Qt.AlignLeft | Qt.AlignBottom)

    window = MainWindow()

    window.showMaximized()
    splash.finish(window)

    sys.exit(app.exec())