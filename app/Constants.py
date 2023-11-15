from PySide6.QtCore import QSettings

settings = QSettings('config.ini', QSettings.IniFormat)

MAQUINAS = (
    'PRE 001',
    'PRE 002',
    'PRE 003',
    'PRE 004',
    'PRE 005',
    'PRE 006',
    'PRE 007',
    'PRE 008',
    'PRE 009',
    'PRE 010',
    'INY 001',
    'INY 002',
    'INY 003',
)

RECETA = (
    'SDESGA1',
    'SPRECUR1',
    'SPREDES1a',
    'SPREDES1b',
    'SPREDES1c',
    'TINIDES',
    'TBAJA1',
    'TESPE1',
    'TCURADO1',
    'SPTEMP1i',
    'SPTEMP1s',
    'SARRIMES',
    'SPARRMAX',
    'SPARRMIN',
    'LIBRE1',
    'LIBRE2',
)

VARIABLES = (
    'cycles',
    'ton',
    'toff',
)

RECETA_SIZE = len(RECETA)
VARIABLES_SIZE = len(VARIABLES)
MAQUINAS_SIZE = len(MAQUINAS)

COLORES = (
    'darkmagenta',
    'darkgreen',
    'darkkhaki',
    'darkorange',
    'darkcyan',
    'darkblue',
    'deeppink',
    'deepskyblue',
    'darkred',
    'darkslategray',
)

MAX_COMMENT_SIZE = 140