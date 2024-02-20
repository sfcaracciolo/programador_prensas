DROP DATABASE IF EXISTS caipe_server;
CREATE DATABASE IF NOT EXISTS caipe_server DEFAULT CHARACTER SET 'cp850';
CREATE USER IF NOT EXISTS 'prod_soft'@localhost IDENTIFIED BY '111111';
GRANT ALL PRIVILEGES ON caipe_server.* TO 'prod_soft'@localhost;
GRANT FILE ON *.* TO 'prod_soft'@localhost;
FLUSH PRIVILEGES;
USE caipe_server;
