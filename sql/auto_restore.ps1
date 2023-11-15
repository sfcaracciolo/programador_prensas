Param (
[Parameter(Mandatory=$true)][string]$src_path, # network path
[string]$dst_path='C:\Program Files\MariaDB 10.6\data\',
[Alias("c")][string]$config_file='C:\Program Files (x86)\CAIPE\ALERGOM - PRODUCCION\main.dist\config.ini',
[Alias("u")][string]$user='root',
[Alias("p")][string]$password='root'
)
# Este script restaura un backup de las tablas orden_programada, tarea_programada y receta. 
# Para no alterar la db activa, autoincrementa el nombre de la db y restaura el backup con este nombre (esto permite poder volver de la restauración simplemente cambiando la db en config.ini)
# Automáticamente, cambia el nombre del config.ini para que al abrir el soft ya esté configurado el backup restaurado.

# set restore database name
Get-Content -Path $config_file | 
    ForEach-Object { 
        if ($_.Split('=')[0] -eq 'DB\database') {
            $actual_dabatase = $_.Split('=')[1]
            if ($actual_dabatase -match 'caipe_server_R'){ # increse
                $new_database = 'caipe_server_R' + '{0:d5}' -f ([int]$actual_dabatase.SubString(14)+1)
            } else {
                $new_database = 'caipe_server_R00001'
            }
            'DB\database='+$new_database
        } else {
            $_
        }
    } |
    Set-Content -Path 'config_temp.txt'
Copy-Item 'config_temp.txt' $config_file -Force

$dst_data_path = (Join-Path -Path $dst_path -ChildPath $new_database);
if (!(Test-Path $dst_data_path -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $dst_data_path
}

$init_cmd = @"
DROP DATABASE IF EXISTS $new_database;
CREATE DATABASE IF NOT EXISTS $new_database DEFAULT CHARACTER SET 'cp850';
CREATE USER IF NOT EXISTS 'prod_soft'@localhost IDENTIFIED BY '111111';
GRANT ALL PRIVILEGES ON $new_database.* TO 'prod_soft'@localhost;
GRANT FILE ON *.* TO 'prod_soft'@localhost;
FLUSH PRIVILEGES;
USE $new_database;
SOURCE caipe_server_schema.sql;
ALTER TABLE $new_database.orden_programada DISCARD TABLESPACE;
ALTER TABLE $new_database.tarea_programada DISCARD TABLESPACE;
ALTER TABLE $new_database.receta DISCARD TABLESPACE;
"@;

$end_cmd = @"
USE $new_database;
ALTER TABLE $new_database.orden_programada IMPORT TABLESPACE;
ALTER TABLE $new_database.tarea_programada IMPORT TABLESPACE;
ALTER TABLE $new_database.receta IMPORT TABLESPACE;
"@;

$parent_path=Split-Path $src_path -parent
(mariabackup --prepare --export --target-dir=$parent_path) &&
(mariadb --user=$user --password=$password --execute=$init_cmd ) && 
Copy-Item (Join-Path -Path $src_path -ChildPath 'orden_programada.ibd') $dst_data_path && 
Copy-Item (Join-Path -Path $src_path -ChildPath 'orden_programada.cfg') $dst_data_path && 
Copy-Item (Join-Path -Path $src_path -ChildPath 'tarea_programada.ibd') $dst_data_path && 
Copy-Item (Join-Path -Path $src_path -ChildPath 'tarea_programada.cfg') $dst_data_path && 
Copy-Item (Join-Path -Path $src_path -ChildPath 'receta.ibd') $dst_data_path &&
Copy-Item (Join-Path -Path $src_path -ChildPath 'receta.cfg') $dst_data_path &&
(mariadb --user=$user --password=$password --execute=$end_cmd ) 
