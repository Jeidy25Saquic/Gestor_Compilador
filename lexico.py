import json
import re

class AnalizadorLexico:
    def __init__(self):
        try:
            with open("tokens.json", "r", encoding="utf-8") as f:
                self.tokens = json.load(f)
        except Exception:
            self.tokens = {}

    def es_texto_libre(self, parte):
        if parte in self.tokens:
            return False
        if parte in ["(", ")", ",", ";", "+", "==", "!=", ">", "<", ">=", "<="]:
            return False
        if parte.startswith('"'):
            return False
        if re.fullmatch(r'\d+', parte):
            return False
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', parte):
            return False
        if re.fullmatch(r'\d{1,2}:\d{2}', parte):
            return False
        if re.fullmatch(r'HOY[+\-]\d+', parte):
            return False
        if re.fullmatch(r'[A-Za-zÁÉÍÓÚáéíóúñÑ][A-Za-zÁÉÍÓÚáéíóúñÑ0-9_\-]*', parte):
            return True
        return False

    def analizar(self, texto):
        # Eliminar comentarios de línea // y bloques /* ... */
        texto = re.sub(r'//.*?$', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'/\*.*?\*/', '', texto, flags=re.DOTALL)

        resultado = []
        texto = texto.replace("==", " == ").replace("!=", " != ")\
                     .replace(">=", " >= ").replace("<=", " <= ")
        texto = texto.replace("(", " ( ").replace(")", " ) ")\
                     .replace(",", " , ").replace(";", " ; ")\
                     .replace("+", " + ")
        partes = [p for p in texto.split() if p.strip()]
        dentro_parentesis = 0
        dentro_cadena = False
        cadena_actual = ""
        i = 0
        while i < len(partes):
            parte = partes[i]
            if parte.startswith('"') and not dentro_cadena:
                cadena_actual = parte
                if parte.endswith('"') and len(parte) > 1:
                    resultado.append((cadena_actual, "CADENA"))
                    cadena_actual = ""
                else:
                    dentro_cadena = True
                i += 1
                continue
            if dentro_cadena:
                cadena_actual += " " + parte
                if parte.endswith('"'):
                    resultado.append((cadena_actual, "CADENA"))
                    cadena_actual = ""
                    dentro_cadena = False
                i += 1
                continue
            if parte == "(":
                dentro_parentesis += 1
                resultado.append((parte, self.tokens.get(parte, "DELIMITADOR")))
                i += 1
                continue
            if parte == ")":
                dentro_parentesis = max(0, dentro_parentesis - 1)
                resultado.append((parte, self.tokens.get(parte, "DELIMITADOR")))
                i += 1
                continue
            if dentro_parentesis > 0 and self.es_texto_libre(parte):
                palabras = [parte]
                while i + 1 < len(partes) and self.es_texto_libre(partes[i + 1]):
                    i += 1
                    palabras.append(partes[i])
                lexema_completo = " ".join(palabras)
                resultado.append((lexema_completo, "TEXTO"))
                i += 1
                continue
            tipo = self.clasificar(parte, dentro_parentesis > 0)
            resultado.append((parte, tipo))
            i += 1
        return resultado

    def clasificar(self, lex, dentro_parentesis):
        lex = lex.strip()
        if not lex:
            return "ERROR_LEXICO"
        if lex in self.tokens:
            return self.tokens[lex]
        if re.fullmatch(r'HOY[+\-]\d+', lex):
            return "EXPR_FECHA"
        if re.fullmatch(r'\d{1,2}:\d{2}', lex):
            horas, minutos = map(int, lex.split(':'))
            if 0 <= horas <= 23 and 0 <= minutos <= 59:
                return "HORA"
            return "ERR_INV_TIME"
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', lex):
            if self.fecha_valida(lex):
                return "FECHA"
            return "ERR_INV_DATE"
        if re.fullmatch(r'"[^"]*"', lex):
            return "CADENA"
        if lex.isdigit():
            return "NUMERO"
        if re.fullmatch(r'[A-Za-zÁÉÍÓÚáéíóúñÑ][A-Za-zÁÉÍÓÚáéíóúñÑ0-9 _.\-]*', lex):
            if dentro_parentesis:
                return "TEXTO"
            if re.fullmatch(r'[a-z][a-z0-9_]*', lex):
                return "IDENTIFICADOR"
            return "TEXTO"
        if lex in ["(", ")", ",", ";", "-", "+", "==", "!=", ">", "<", ">=", "<="]:
            if lex in [",", "+", "-"]:
                return "SIMBOLO"
            if lex in ["==", "!=", ">", "<", ">=", "<="]:
                return "OPERADOR_COMPARACION"
            return "DELIMITADOR"
        return "ERROR_LEXICO"

    def fecha_valida(self, fecha):
        try:
            anio, mes, dia = map(int, fecha.split("-"))
            if 1 <= mes <= 12 and 1 <= dia <= 31:
                dias_por_mes = [31, 29 if self.es_bisiesto(anio) else 28, 31, 30, 31, 30,
                                31, 31, 30, 31, 30, 31]
                return dia <= dias_por_mes[mes - 1]
            return False
        except:
            return False

    def es_bisiesto(self, anio):
        return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)