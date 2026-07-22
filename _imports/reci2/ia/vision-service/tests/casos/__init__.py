# tests/casos/__init__.py
# Importa todos los casos de prueba de los módulos individuales

from tests.casos.casos_vidrio    import CASOS_VIDRIO
from tests.casos.casos_plastico  import CASOS_PLASTICO
from tests.casos.casos_ambiguos  import CASOS_AMBIGUOS
from tests.casos.casos_extremos  import CASOS_EXTREMOS
from tests.casos.casos_campus    import CASOS_CAMPUS

# Lista completa para el runner
TODOS_LOS_CASOS = (
    CASOS_VIDRIO +
    CASOS_PLASTICO +
    CASOS_AMBIGUOS +
    CASOS_EXTREMOS +
    CASOS_CAMPUS
)