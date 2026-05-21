import sys
import os

# Añadir el directorio padre al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generador_dashboard import app

# Vercel necesita una variable 'app' (ya la tenemos)