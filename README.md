# Requisitos

* Instalar pyside6, asyncua, nuitka
* Cargar Driver MYSQL en PySide6:
  1. Se descarga de https://github.com/thecodemonkey86/qt_mysql_driver. Chequear versión de Qt con pip list y descargar la versión para MSVC2019 64-bit.
  2. Extraer en Lib\site-packages\PySide6\ los *.dll que no están en /sqldrivers
  3. Extraer en Lib\site-packages\PySide6\plugins\sqldrivers la carpeta /sqldrivers.

# Ejecución

* Crear resources.py: `\Scripts\pyside6-rcc.exe app\resources.qrc -o app\resources.py`
* Abrir app: `python app\main.py`

# Deploy

1. En carpeta /deploy: `nuitka ..\app\main.py`
2. Abrir installforge 1.4.2.21, cargar `sql\installer_v14.ifp` y tocar el botón Build.

Ver en sección SQL que en modo --dev también se genera `installer_v14.ifp` con Jinja.

# SQL

Para crear los esquemas de la base de datos según sea producción o dev, se ejecuta `python templates.py` con el flag `--dev` si corresponde. Los archivos *.sql se generan en `\sql`. 

## Base de datos

Las tablas definidas son:
* `cliente`, `hoja_de_ruta`, `operario` y `orden_produccion_item` son vistas de los *.dbf del servidor.
* `orden_programada`: son las órdenes de producción programadas, c/u corresponde a un elemento de `orden_programada_item` y tiene hijos según la cantidad de jornales que dure la orden (padre de `tarea_programada`).
* `tarea_programada`: son las tareas que componen cada orden programada (hijo de `orden_programada`). c/u tiene guardado, acumulado y total por cada variable.
* `receta`: contiene 16 variables.
  
## Backup/Restore

Se implementó un pequeño sistema para hacer backups de tres tablas en la PC de fábrica: 'orden_programada', 'tarea_programada' y 'receta'.

Se desarrollaron dos scripts de Powershell que deben ser ejecutados en `\sql`: 
  1. `auto_backup.ps1`: Debe ejecutarse automaticamente cada 15 o 30 días para realizar backups con el siguiente comando -> `./auto_backup.ps1 -target_dir "E:\backup_test"`
  2. `auto_restore.ps1`: restaura el backup indicado con el siguiente comando -> `.\auto_restore.ps1 -src_path "E:\backup_test\20230304224737\caipe_server"`

<!-- https://mariadb.com/kb/en/partial-backup-and-restore-with-mariabackup/ -->

# Funcionamiento

Las tareas programadas se visualizan en el calendario, muestran la hoja de ruta, las moldeadas actuales de la tarea (tiempo real) / moldeades acumuladas de la tarea (acumula moldeadas si han detenido y arrancado la máquina), y las moldeadas actuales totales (suma de todos las moldeadas asociadas a la misma orden de producción) / moldeadas requeridas por la orden de producción.

Al poner una tarea en marcha se envía la receta correspondiente a la máquina, se resetean los contadores (moldeadas, t. marcha, t. parada) y se escribe un 1 en el estado de máquina. Cuando se detiene o finaliza una tarea que se encuentra online, se escribe un 0 en el estado de máquina.

## Transiciones de estado

| old/new | 0 (restored) | 1 (online) | 2(finished) |
| --- | --- | --- | --- |
| 0 (restored) | X | A | + |
| 1 (online) | B | X | B+ |
| 2 (finished) | - | A- | X |

**X**: sin acción. **A**: Si máquina online -> checkout de la TP activa. Luego, activar TP nueva. **B**: Checkout de la TP activa. Luego, desactivar TP. **+/-**: Incrementar/Decrementar hijos finalizados. Checkout es la operación que incrementa los acumulados de las tareas programadas.
