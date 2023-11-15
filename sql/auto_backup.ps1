Param (
[Parameter(Mandatory=$true)][string]$target_dir, # network path
[Alias("c")][string]$config_file='C:\Program Files (x86)\CAIPE\ALERGOM - PRODUCCION\main.dist\config.ini',
[Alias("u")][string]$user='root',
[Alias("p")][string]$password='root'
)

# Este script genera un backup de las tablas orden_programada, tarea_programada y receta de la db activa (la configurada en config.ini) en el soft de producción.
# Este script requiere tener permisos de escritura si se usa un target en red.

$today=(Get-Date).ToString("yyyyMMddHHmmss");
$today_path = Join-Path -Path $target_dir -ChildPath $today;

# get active database name
$file = Get-Content -Path $config_file
foreach ($line in $file) {
    $parse = $line.Split('=')
    if ($parse[0] -eq 'DB\database') {
        $database = $parse[1]
        break
    }
}
$tables=@"
$database.orden_programada
$database.tarea_programada
$database.receta
"@

$filename = "tables_file.txt"
$path = Join-Path -Path $pwd -ChildPath $filename;
(Write-Output $tables > $filename) &&
(mariabackup --backup --target-dir=$today_path --databases=$database --tables-file=$path --user=$user --password=$password);
$backup_file = Join-Path -Path $today_path -ChildPath ($database + '/.backup');
New-Item -ItemType file -Force -Path $backup_file;
Write-Host "Backup finished at $today_path" -BackgroundColor Green;