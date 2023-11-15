
from jinja2 import Environment, FileSystemLoader
import sys 

DEV = (len(sys.argv) == 2) and (sys.argv[1] == '--dev')

environment = Environment(loader=FileSystemLoader("sql/"))

# ALERGOM SERVER
template = environment.get_template("alergom_server_schema.jinja")
content = template.render(
    DBF_PATH='E:/Repositorios/programador_prensas/dbfs/' if DEV else 'D:/USUARIOS/CALIDAD/CAIPE/',
)
with open('sql/alergom_server_schema.sql', mode="w", encoding="utf-8") as f:
    f.write(content)

# CAIPE SERVER
template = environment.get_template("caipe_server_schema.jinja")
content = template.render(
    SERVER_IP='localhost' if DEV else '192.168.1.10',
    SERVER_PORT=3308 if DEV else 3306,
)
with open('sql/caipe_server_schema.sql', mode="w", encoding="utf-8") as f:
    f.write(content)

# SP HOJAS
template = environment.get_template("import_old_recipes.jinja")
content = template.render(
    CSV_PATH='E:/Repositorios/programador_prensas/SP-Hojas.csv' if DEV else 'C:/Users/Fabrica/OneDrive/Escritorio/CAIPE/SP-Hojas.csv',
)
with open('sql/import_old_recipes.sql', mode="w", encoding="utf-8") as f:
    f.write(content)