CREATE OR REPLACE TABLE cliente
engine=CONNECT 
table_type=MYSQL 
dbname=alergom_server
tabname=cliente
connection='mysql://caipe:111111@localhost:3308';

CREATE OR REPLACE TABLE hoja_de_ruta
engine=CONNECT 
table_type=MYSQL 
dbname=alergom_server
tabname=hoja_de_ruta
connection='mysql://caipe:111111@localhost:3308';

CREATE OR REPLACE TABLE orden_produccion_item
engine=CONNECT
table_type=MYSQL 
dbname=alergom_server
tabname=orden_produccion_item_abierta
connection='mysql://caipe:111111@localhost:3308';


CREATE OR REPLACE TABLE operario
engine=CONNECT 
table_type=MYSQL 
dbname=alergom_server
tabname=operario
connection='mysql://caipe:111111@localhost:3308';

ALTER TABLE orden_produccion_item
    ADD PRIMARY KEY (id, fname)
;

ALTER TABLE cliente
    ADD PRIMARY KEY (FM01_01)
;

ALTER TABLE hoja_de_ruta
    ADD PRIMARY KEY (CM75_01)
;

ALTER TABLE operario
    ADD PRIMARY KEY (CM70_01)
;

DROP TABLE IF EXISTS orden_programada;
CREATE TABLE orden_programada (
    id INT UNSIGNED  NOT NULL AUTO_INCREMENT, 
    iop_id INT UNSIGNED NOT NULL,
    cycles INT UNSIGNED NOT NULL,
    -- status INT UNSIGNED NOT NULL DEFAULT(0), --0: programada (gris). 1: en proceso (amarillo). 2: terminado (verde)
    fname CHAR(12) NOT NULL DEFAULT('COS76000'),
    childs INT UNSIGNED NOT NULL DEFAULT(0),
    finished_childs INT UNSIGNED NOT NULL DEFAULT(0),
    PRIMARY KEY(id)
);

DROP TABLE IF EXISTS tarea_programada;
CREATE TABLE tarea_programada (
    id INT UNSIGNED  NOT NULL AUTO_INCREMENT, 
    parent INT UNSIGNED NOT NULL, -- orden_programada id
    hr CHAR(15) NULL,
    op_id INT(8) NULL,
    machine CHAR(25) NOT NULL,
    date DATE NOT NULL,
    cycles INT UNSIGNED NOT NULL DEFAULT(0),
    priority INT UNSIGNED NULL,
    operator CHAR(25) NULL,
    status INT UNSIGNED DEFAULT(0),
    saved_cycles INT UNSIGNED DEFAULT(0),
    acum_cycles INT UNSIGNED DEFAULT(0),
    total_cycles INT UNSIGNED DEFAULT(0),
    saved_ton INT UNSIGNED DEFAULT(0),
    acum_ton INT UNSIGNED DEFAULT(0),
    total_ton INT UNSIGNED DEFAULT(0),
    saved_toff INT UNSIGNED DEFAULT(0),
    acum_toff INT UNSIGNED DEFAULT(0),
    total_toff INT UNSIGNED DEFAULT(0),
    PRIMARY KEY(id),
    INDEX (date) -- best performance? i think yes
);

DROP TABLE IF EXISTS active_tp;
CREATE TABLE active_tp (
    machine CHAR(25) NOT NULL UNIQUE,
    tp_id INT UNSIGNED NULL UNIQUE
    -- cycles INT UNSIGNED DEFAULT(0),
    -- ton INT UNSIGNED DEFAULT(0),
    -- toff INT UNSIGNED DEFAULT(0)
);

DROP TABLE IF EXISTS receta;
CREATE TABLE receta (
    id INT UNSIGNED  NOT NULL AUTO_INCREMENT, 
    hr CHAR(15) NOT NULL UNIQUE,
    SDESGA1 INT NOT NULL DEFAULT(0),
    SPRECUR1 INT NOT NULL DEFAULT(0),
    SPREDES1a INT NOT NULL DEFAULT(0),
    SPREDES1b INT NOT NULL DEFAULT(0),
    SPREDES1c INT NOT NULL DEFAULT(0),
    TINIDES DOUBLE(6,1) NOT NULL DEFAULT(0),
    TBAJA1 DOUBLE(6,1) NOT NULL DEFAULT(0),
    TESPE1 DOUBLE(6,1) NOT NULL DEFAULT(0),
    TCURADO1 DOUBLE(6,2) NOT NULL DEFAULT(0),
    SPTEMP1i INT NOT NULL DEFAULT(0),
    SPTEMP1s INT NOT NULL DEFAULT(0),
    SARRIMES INT NOT NULL DEFAULT(0),
    SPARRMAX INT NOT NULL DEFAULT(0),
    SPARRMIN INT NOT NULL DEFAULT(0),
    LIBRE1 INT NOT NULL DEFAULT(0),
    LIBRE2 INT NOT NULL DEFAULT(0),
    PRIMARY KEY(id)
);

INSERT INTO active_tp(machine) VALUES
	('PRE 001'),
	('PRE 002'),
	('PRE 003'),
	('PRE 004'),
	('PRE 005'),
	('PRE 006'),
	('PRE 007'),
	('PRE 008'),
	('PRE 009'),
	('PRE 010'),
	('INY 001'),
	('INY 002'),
	('INY 003')
;

-- INSERT INTO receta(id, hr) VALUES 
--     (1, '00003/01'),
--     (2, '00011/01')
-- ;

-- INSERT INTO tarea_programada(iop_id, maq_id, date, cycles) VALUES 
--     (11428, 1, '2022-05-04', 1000),
--     (11518, 2, '2022-05-05', 1500),
--     (11525, 3, '2022-05-05', 1000),
--     (11579, 3, '2022-05-07', 500),
--     (11579, 3, '2022-05-07', 500),
--     (11579, 3, '2022-05-08', 500),
--     (11579, 3, '2022-05-08', 500),
--     (11579, 3, '2022-05-09', 500),
--     (11579, 3, '2022-05-10', 500)
-- ;
-- CALL create_tp(1, 1, '2022-03-03', 111, 1);
-- CALL create_tp(1, 1, '2022-03-03', 222, 1);
-- CALL create_tp(1, 1, '2022-03-03', 222, 2);
-- CALL create_tp(1, 1, '2022-03-04', 333, 5);

-- CALL create_child_tp(2, '2022-03-20', 1, 3);
-- CALL update_tp(1, 4, '2022-03-04');
-- CALL update_date(8, '2022-03-07');



DELIMITER //

CREATE OR REPLACE FUNCTION is_op (iop_id INT UNSIGNED, fname CHAR(12))
RETURNS INT UNSIGNED
READS SQL DATA
BEGIN
    DECLARE _count INT UNSIGNED;

    SELECT op.ROWNUM 
    INTO _count
    FROM orden_programada as op
    WHERE op.iop_id = iop_id 
    AND op.fname = fname;

    RETURN _count;
END; //

CREATE OR REPLACE FUNCTION compute_priority (machine CHAR(25), date DATE)
RETURNS INT UNSIGNED
READS SQL DATA
BEGIN
    DECLARE priority INT UNSIGNED;

    SELECT COUNT(tp.id)
    INTO priority 
    FROM tarea_programada as tp
    WHERE tp.date = date
    AND tp.machine = machine;

    RETURN priority;
END; //

CREATE OR REPLACE FUNCTION get_priority (id INT UNSIGNED)
RETURNS INT UNSIGNED
READS SQL DATA
BEGIN
    DECLARE priority INT UNSIGNED;

    SELECT tp.priority
    INTO priority 
    FROM tarea_programada as tp  
    WHERE tp.id = id;

    RETURN priority;
END; //

CREATE OR REPLACE FUNCTION get_max_priority (machine CHAR(25), date DATE)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE priority INT;

    SELECT MAX(tp.priority) INTO priority
    FROM tarea_programada as tp
    WHERE tp.machine = machine
    AND tp.date = date;

    RETURN priority;
END; //


CREATE OR REPLACE FUNCTION get_parent (id INT UNSIGNED)
RETURNS INT UNSIGNED
READS SQL DATA
BEGIN
    DECLARE parent INT UNSIGNED;

    SELECT tp.parent
    INTO parent 
    FROM tarea_programada as tp  
    WHERE tp.id = id;

    RETURN parent;
END; //

CREATE OR REPLACE FUNCTION get_iop_id (id INT UNSIGNED)
RETURNS INT UNSIGNED
READS SQL DATA
BEGIN
    DECLARE iop_id INT UNSIGNED;

    SELECT op.iop_id
    INTO iop_id 
    FROM orden_programada as op  
    WHERE op.id = id;

    RETURN iop_id;
END; //

CREATE OR REPLACE PROCEDURE create_childs (parent INT UNSIGNED, machine CHAR(25), date DATE, amount INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    FOR i IN 0..amount-1
    DO
        INSERT INTO tarea_programada ( parent, machine, date) VALUES ( parent, machine, ADDDATE(date,i) );
    END FOR;
END; //

CREATE OR REPLACE PROCEDURE create_parent_and_childs (iop_id INT UNSIGNED, fname CHAR(12), machine CHAR(25), date DATE, cycles INT UNSIGNED, amount INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE parent INT UNSIGNED;
    INSERT INTO orden_programada (iop_id, fname, cycles)
    VALUES  (iop_id, fname, cycles); -- insert parent
    SET parent = LAST_INSERT_ID();
    CALL create_childs(parent, machine, date, amount);
END; //

CREATE OR REPLACE PROCEDURE priority_reassigment (machine CHAR(25), date DATE, priority_removed INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    UPDATE tarea_programada as tp 
    SET tp.priority = tp.priority - 1
    WHERE tp.machine = machine
    AND tp.date = date 
    AND tp.priority > priority_removed;
END; //

CREATE OR REPLACE PROCEDURE update_tp (id INT UNSIGNED, new_machine CHAR(25), new_date DATE)
MODIFIES SQL DATA
whole_proc:
BEGIN
    DECLARE old_machine CHAR(25);
    DECLARE old_priority INT UNSIGNED;
    DECLARE old_date DATE;
    DECLARE status INT UNSIGNED;

    SELECT tp.machine, tp.date, tp.priority, tp.status
    INTO old_machine, old_date, old_priority, status
    FROM tarea_programada as tp
    WHERE tp.id = id;

    IF status = 1 AND old_machine <> new_machine  THEN -- don't change machine if is an active tp
        LEAVE whole_proc;
    END IF;

    CALL priority_reassigment(old_machine, old_date, old_priority);
    -- actualizado datos
    UPDATE tarea_programada as tp
    SET
        tp.priority = compute_priority(new_machine, new_date),
        tp.date = new_date,
        tp.machine = new_machine
    WHERE tp.id = id;

END; //

CREATE OR REPLACE PROCEDURE bulk_update_date (machine CHAR(25), date DATE, amount INT)
MODIFIES SQL DATA
BEGIN
    UPDATE tarea_programada as tp
    SET tp.date = ADDDATE(tp.date, amount)
    WHERE tp.machine = machine
    AND tp.date >= date;
END; //

CREATE OR REPLACE PROCEDURE bulk_update_ope (id INT UNSIGNED, operator CHAR(25))
MODIFIES SQL DATA
BEGIN
    DECLARE parent INT UNSIGNED;
    SET parent = get_parent(id);

    UPDATE tarea_programada as tp
    SET tp.operator = operator
    WHERE tp.parent = parent;

END; //

CREATE OR REPLACE PROCEDURE bulk_update_cycles (id INT UNSIGNED, cycles INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE parent INT UNSIGNED;
    SET parent = get_parent(id);

    UPDATE tarea_programada as tp
    SET tp.cycles = cycles
    WHERE tp.parent = parent;

    UPDATE orden_programada as op
    SET op.cycles = cycles
    WHERE op.id = parent;
END; //

CREATE OR REPLACE PROCEDURE update_ope (id INT UNSIGNED, operator CHAR(25))
MODIFIES SQL DATA
BEGIN
    UPDATE tarea_programada as tp
    SET tp.operator = operator
    WHERE tp.id = id;

END; //

CREATE OR REPLACE PROCEDURE update_comment (id INT UNSIGNED, fname CHAR(12), comment CHAR(140))
MODIFIES SQL DATA
BEGIN
    UPDATE orden_produccion_item as iop
    SET iop.CM76_26 = comment -- change by CM76_26
    WHERE iop.id = id AND iop.fname = fname;
END; //

CREATE OR REPLACE PROCEDURE bulk_update_comment (id INT UNSIGNED, fname CHAR(12), comment CHAR(140))
MODIFIES SQL DATA
BEGIN
    DECLARE op INT(8);

    SELECT iop.CM76_01
    INTO op
    FROM orden_produccion_item as iop
    WHERE iop.id = id AND iop.fname = fname;
    
    UPDATE orden_produccion_item as iop
    SET iop.CM76_26 = comment -- change by CM76_26
    WHERE iop.CM76_01 = op AND iop.fname = fname;
END; //

-- CREATE OR REPLACE PROCEDURE update_opc_data (machine CHAR(15), cycles INT UNSIGNED, ton INT UNSIGNED, toff INT UNSIGNED)
-- MODIFIES SQL DATA
-- whole_proc: 
-- BEGIN
--     DECLARE id INT UNSIGNED;

--     SELECT opc.tp_id 
--     INTO id 
--     FROM opc_data as opc 
--     WHERE opc.machine = machine;

--     IF id is NULL THEN
--         LEAVE whole_proc;
--     END IF;

--     UPDATE opc_data as opc
--     SET opc.cycles = cycles,
--     opc.ton = ton,
--     opc.toff = toff
--     WHERE opc.machine = machine;

-- END; //

CREATE OR REPLACE PROCEDURE update_recipe (machine CHAR(15), SDESGA1 INT, SPRECUR1 INT, SPREDES1a INT, SPREDES1b INT, SPREDES1c INT, TINIDES INT, TBAJA1 INT, TESPE1 INT, TCURADO1 INT, SPTEMP1i INT, SPTEMP1s INT, SARRIMES INT, SPARRMAX INT, SPARRM INT, LIBRE1 INT, LIBRE2 INT)
MODIFIES SQL DATA
whole_proc: 
BEGIN
    DECLARE hr CHAR(15);
    DECLARE id INT UNSIGNED;

    SELECT atp.tp_id 
    INTO id 
    FROM active_tp as atp 
    WHERE atp.machine = machine;

    IF id is NULL THEN
        LEAVE whole_proc;
    END IF;

    SELECT tp.hr 
    INTO hr 
    FROM tarea_programada as tp 
    WHERE tp.id = id;
     
    UPDATE receta as rec
    SET rec.SDESGA1 = SDESGA1,
    rec.SPRECUR1 = SPRECUR1,
    rec.SPREDES1a = SPREDES1a,
    rec.SPREDES1b = SPREDES1b,
    rec.SPREDES1c = SPREDES1c,
    rec.TINIDES = TINIDES,
    rec.TBAJA1 = TBAJA1,
    rec.TESPE1 = TESPE1,
    rec.TCURADO1 = TCURADO1,
    rec.SPTEMP1i = SPTEMP1i,
    rec.SPTEMP1s = SPTEMP1s,
    rec.SARRIMES = SARRIMES,
    rec.SPARRMAX = SPARRMAX,
    rec.SPARRMIN = SPARRMIN,
    rec.LIBRE1 = LIBRE1,
    rec.LIBRE2 = LIBRE2
    WHERE rec.hr = hr;

END; //

CREATE OR REPLACE PROCEDURE delete_tp (id INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE machine CHAR(25);
    DECLARE date DATE;
    DECLARE priority INT UNSIGNED;
    DECLARE status INT UNSIGNED;

    SELECT tp.machine, tp.date, tp.priority, tp.status
    INTO machine, date, priority, status
    FROM tarea_programada as tp 
    WHERE tp.id = id ;

    IF status <> 1 THEN
        CALL priority_reassigment(machine, date, priority);

        DELETE FROM tarea_programada
        WHERE tarea_programada.id = id;
    END IF;

END; //

CREATE OR REPLACE PROCEDURE delete_op (id INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE parent INT UNSIGNED;
    DECLARE childs INT UNSIGNED;
    DECLARE op_status INT UNSIGNED;
    DECLARE tp_id INT UNSIGNED;

    SET parent = get_parent(id);

    SELECT op.childs
    INTO childs
    FROM orden_programada as op 
    WHERE op.id = parent;

    SELECT SUM(IF(status = 1, 1, 0))
    INTO op_status
    FROM tarea_programada as tp 
    WHERE tp.parent = parent;

    IF op_status = 0 THEN -- any ready
        FOR i IN 1..childs DO
            SELECT tp.id 
            INTO tp_id 
            FROM tarea_programada as tp 
            WHERE tp.parent = parent
            LIMIT 1;
            CALL delete_tp(tp_id);
        END FOR;
    END IF;

END; //

CREATE OR REPLACE PROCEDURE forward_shift (machine CHAR(25), date DATE, amount INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    CALL bulk_update_date(machine, date, CAST(amount as INT));
END; //

CREATE OR REPLACE PROCEDURE backward_shift (machine CHAR(25), date DATE, amount INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE _offset INT UNSIGNED;

    FOR i IN 1..amount DO
        UPDATE tarea_programada as tp 
        SET tp.priority = COALESCE(tp.priority + get_max_priority(machine, ADDDATE(date, i-1)) + 1, tp.priority)
        WHERE tp.machine = machine
        AND tp.date = ADDDATE(date, -(amount-i+1));
    END FOR;
    CALL bulk_update_date(machine, date, -amount);
END; //

CREATE OR REPLACE PROCEDURE swap_priorities (id_a INT UNSIGNED, id_b INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE priority_a INT UNSIGNED;
    DECLARE priority_b INT UNSIGNED;
    
    SET priority_a = get_priority(id_a);
    SET priority_b = get_priority(id_b);

    UPDATE tarea_programada as tp 
    SET tp.priority = priority_b
    WHERE tp.id = id_a;

    UPDATE tarea_programada as tp 
    SET tp.priority = priority_a
    WHERE tp.id = id_b;
END; //

CREATE OR REPLACE PROCEDURE up_priority (id INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE machine CHAR(25);
    DECLARE date DATE;
    DECLARE priority INT UNSIGNED;
    DECLARE swap_id INT UNSIGNED;

    SELECT tp.machine, tp.date, tp.priority INTO machine, date, priority 
    FROM tarea_programada as tp 
    WHERE tp.id = id;

    IF priority < get_max_priority(machine, date) THEN
        
        SELECT tp.id INTO swap_id
        FROM tarea_programada as tp 
        WHERE tp.date = date 
        AND tp.machine = machine
        AND tp.priority = priority + 1;

        CALL swap_priorities(id, swap_id);
        
    END IF;
END; //

CREATE OR REPLACE PROCEDURE down_priority (id INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE machine CHAR(25);
    DECLARE date DATE;
    DECLARE priority INT UNSIGNED;
    DECLARE swap_id INT UNSIGNED;
    
    SELECT tp.machine, tp.date, tp.priority INTO machine, date, priority 
    FROM tarea_programada as tp 
    WHERE tp.id = id;

    IF priority > 0 THEN
        
        SELECT tp.id INTO swap_id
        FROM tarea_programada as tp 
        WHERE tp.date = date 
        AND tp.machine = machine
        AND tp.priority = priority - 1;

        CALL swap_priorities(id, swap_id);
        
    END IF;
END; //

CREATE OR REPLACE PROCEDURE set_status (id INT UNSIGNED, new_status INT UNSIGNED, cycles INT UNSIGNED, ton INT UNSIGNED, toff INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE status INT UNSIGNED;
    DECLARE parent INT UNSIGNED;
    DECLARE machine CHAR(15);
    DECLARE loaded_id INT UNSIGNED;

    SELECT tp.status, tp.machine, tp.parent
    INTO status, machine, parent
    FROM tarea_programada as tp 
    WHERE tp.id = id;
    
    IF status <> new_status THEN 

        IF new_status = 1 THEN -- case transition of 0->1 or 2->1

            -- loaded_id is NULL if machine is offline
            SELECT atp.tp_id 
            INTO loaded_id
            FROM active_tp as atp 
            WHERE atp.machine = machine;

            IF loaded_id IS NOT NULL THEN 
                CALL checkout_tp(loaded_id, parent, 0, cycles, ton, toff);
            END IF;

            UPDATE active_tp as atp
            SET atp.tp_id = id
            WHERE atp.machine = machine;

        END IF;

        IF new_status = 2 THEN -- finished 0->2 or 1->2

            UPDATE orden_programada as op
            SET op.finished_childs = op.finished_childs + 1
            WHERE op.id = parent;

        END IF;

        IF status = 2 THEN -- case transition of 2->0 or 2->1

            UPDATE orden_programada as op
            SET op.finished_childs = op.finished_childs - 1
            WHERE op.id = parent;
            
        END IF;

        IF status = 1 THEN -- case transition of 1->0 or 1->2

            CALL checkout_tp(id, parent, new_status, cycles, ton, toff);

            UPDATE active_tp as atp
            SET atp.tp_id = NULL
            WHERE atp.machine = machine;

        END IF; -- case transitions 0/2 -> 2/0

        -- update status
        UPDATE tarea_programada as tp
        SET tp.status = new_status
        WHERE tp.id = id;

    END IF; 
END; //

CREATE OR REPLACE PROCEDURE checkout_tp (id INT UNSIGNED, parent INT UNSIGNED, status INT UNSIGNED, cycles INT UNSIGNED, ton INT UNSIGNED, toff INT UNSIGNED)
MODIFIES SQL DATA
BEGIN
    DECLARE sum_cycles INT UNSIGNED;
    DECLARE sum_ton INT UNSIGNED;
    DECLARE sum_toff INT UNSIGNED;

    -- save data and update status
    UPDATE tarea_programada as tp 
    SET tp.saved_cycles = cycles,
    tp.saved_ton = ton, 
    tp.saved_toff = toff,
    tp.status = status
    WHERE tp.id = id;

    -- save self acum
    UPDATE tarea_programada as tp 
    SET tp.acum_cycles = tp.acum_cycles + cycles,
    tp.acum_ton = tp.acum_ton + ton, 
    tp.acum_toff = tp.acum_toff + toff 
    WHERE tp.id = id;

    -- compute sums
    SELECT SUM(tp.acum_cycles), SUM(tp.acum_ton), SUM(tp.acum_toff)
    INTO sum_cycles, sum_ton, sum_toff
    FROM tarea_programada as tp 
    WHERE tp.parent = parent;

    -- save total acum 
    UPDATE tarea_programada as tp 
    SET tp.total_cycles = sum_cycles,
    tp.total_ton = sum_ton, 
    tp.total_toff = sum_toff 
    WHERE tp.parent = parent;
    
END; //

-- CREATE OR REPLACE PROCEDURE create_calendar (start_date DATE, span INT UNSIGNED)
-- READS SQL DATA
-- BEGIN
--     WITH count_tps AS (
--         SELECT 
--             tp.machine,
--             tp.date,
--             COUNT(tp.id) AS _count
--         FROM tarea_programada as tp
--         WHERE tp.date BETWEEN start_date AND ADDDATE(start_date, span)
--         GROUP BY tp.machine, tp.date
--     ), max_tps AS (
--         SELECT 
--             machine,
--             MAX(_count) AS amount
--         FROM count_tps
--         GROUP BY machine
--     ), acum_tps AS (
--         SELECT
--             machine,
--             CAST(SUM(amount) OVER (ORDER BY machine ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)  AS INT) AS acum
--         FROM max_tps
--     ), offset_tps AS (
--         SELECT
--             machine,
--             COALESCE(LAG(acum_tps.acum, 1) OVER (ORDER BY acum_tps.machine), 0) AS _offset
--         FROM acum_tps
--     )
--     SELECT 
--         tp.id as tp_id,
--         tp.priority + offset_tps._offset as _row,
--         CAST(DATEDIFF(tp.date, start_date) AS INT) AS _col,
--         offset_tps._offset AS _offset
--     FROM tarea_programada as tp
--     INNER JOIN offset_tps ON offset_tps.machine = tp.machine;
-- END; //

CREATE OR REPLACE TRIGGER tp_insert BEFORE INSERT
ON tarea_programada FOR EACH ROW
BEGIN
    DECLARE iop_id INT UNSIGNED;
    DECLARE op_id INT(8);
    DECLARE hr CHAR(15);
    DECLARE cycles INT UNSIGNED;

    SET iop_id = get_iop_id(NEW.parent);

    SELECT iop.CM76_01, iop.CM76_06
    INTO op_id, hr
    FROM orden_produccion_item as iop
    WHERE iop.id = iop_id;

    SELECT op.cycles
    INTO cycles
    FROM orden_programada as op
    WHERE op.id = NEW.parent;

    SET NEW.op_id = op_id;
    SET NEW.hr = hr;
    SET NEW.cycles = cycles;
    SET NEW.priority = compute_priority(NEW.machine, NEW.date);

    UPDATE orden_programada as op 
    SET op.childs = op.childs + 1
    WHERE op.id = NEW.parent;
END; //

CREATE OR REPLACE TRIGGER op_delete AFTER DELETE
ON tarea_programada FOR EACH ROW
BEGIN
    DECLARE childs INT UNSIGNED;
    
    SELECT op.childs INTO childs
    FROM orden_programada as op 
    WHERE op.id = OLD.parent;

    IF childs = 0 THEN
        DELETE FROM orden_programada 
        WHERE orden_programada.id = OLD.parent;
    END IF;

END; //

CREATE OR REPLACE TRIGGER tp_delete BEFORE DELETE
ON tarea_programada FOR EACH ROW
BEGIN
    UPDATE orden_programada as op 
    SET op.childs = op.childs - 1
    WHERE op.id = OLD.parent;
END; //

DELIMITER ;