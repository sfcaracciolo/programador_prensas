DROP DATABASE IF EXISTS alergom_server;
DROP DATABASE IF EXISTS caipe_server;

SOURCE alergom_server_schema.sql;
SOURCE caipe_server_schema.sql;
SOURCE import_old_recipes.sql;