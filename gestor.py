import sys
import webbrowser
from threading import Timer
from lexico import AnalizadorLexico
from sintactico import AnalizadorSintactico
from semantico import AnalizadorSemantico
from generador_dashboard import app, set_tabla_simbolos
from generador_dashboard import app
app.run(debug=True)

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")


def main(archivo_entrada):
    with open(archivo_entrada, 'r', encoding='utf-8') as f:
        codigo = f.read()

    print("🔍 Analizando léxicamente...")
    lex = AnalizadorLexico()
    sint = AnalizadorSintactico()
    sem = AnalizadorSemantico()

    print("📐 Analizando sintáctica y semánticamente...")
    tabla, log, ok, msg, detalle = sem.analizar(codigo)

    if not ok:
        print(f"\n❌ ERROR: {msg}")
        if detalle:
            print(f"   {detalle}")
        sys.exit(1)

    print("✅ Análisis exitoso. Construyendo dashboard...")

    # Pasar la tabla de símbolos al generador del dashboard
    set_tabla_simbolos(tabla)

    # Abrir navegador automáticamente después de 1 segundo
    Timer(1, abrir_navegador).start()

    # Ejecutar servidor Flask
    print("🌐 Servidor iniciado en http://127.0.0.1:5000/")
    app.run(debug=False, use_reloader=False)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python gestor.py archivo.lan")
        sys.exit(1)
    main(sys.argv[1])