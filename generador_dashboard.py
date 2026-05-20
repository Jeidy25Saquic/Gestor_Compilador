import json
from flask import Flask, render_template, jsonify
from flask import request

app = Flask(__name__)
tabla_simbolos = None


def set_tabla_simbolos(tabla):
    global tabla_simbolos
    tabla_simbolos = tabla


def construir_json_proyecto():
    """Convierte la tabla de símbolos en un JSON completo para el frontend"""
    if tabla_simbolos is None:
        return {"error": "No hay datos"}

    # Tareas
    tareas = []
    for e in tabla_simbolos.por_categoria("TAREA"):
        tareas.append({
            "nombre": e["identificador"],
            "estado": e["estado"] if e["estado"] != "PENDIENTE" else "EST.PEN",
            "prioridad": e["prioridad"],
            "fecha_limite": e["fecha_limite"] if e["fecha_limite"] != "—" else None,
            "asignado_a": e["asignado_a"] if e["asignado_a"] != "—" else None,
            "etiquetas": e["etiquetas"],
            "subtareas": e["subtareas"],
            "descripcion": e["descripcion"] if e["descripcion"] != "—" else "",
            "tipo": e["tipo"]
        })

    # Usuarios
    usuarios = []
    for u in tabla_simbolos.por_categoria("USUARIO"):
        usuarios.append({
            "nombre": u["identificador"],
            "rol": u["tipo"],
            "sesion": u["sesion"]
        })

    # Grupos
    grupos = []
    for g in tabla_simbolos.por_categoria("GRUPO"):
        grupos.append({
            "nombre": g["identificador"],
            "miembros": g["miembros"]
        })

    # Listas
    listas = []
    for l in tabla_simbolos.por_categoria("LISTA"):
        listas.append({
            "nombre": l["identificador"],
            "tareas": l["tareas_lista"],
            "descripcion": l["descripcion"]
        })

    # Vistas (filtros guardados)
    vistas = []
    for v in tabla_simbolos.a_lista():
        if v["categoria"] == "VISTA":
            vistas.append({"nombre": v["identificador"]})

    # Estadísticas para gráficos
    total_tareas = len(tareas)
    completadas = sum(1 for t in tareas if t["estado"] == "EST.FIN")
    por_completar = total_tareas - completadas
    prioridades = {
        "PRI.URG": sum(1 for t in tareas if t["prioridad"] == "PRI.URG"),
        "PRI.ALT": sum(1 for t in tareas if t["prioridad"] == "PRI.ALT"),
        "PRI.MED": sum(1 for t in tareas if t["prioridad"] == "PRI.MED"),
        "PRI.BAJ": sum(1 for t in tareas if t["prioridad"] == "PRI.BAJ")
    }

    return {
        "tareas": tareas,
        "usuarios": usuarios,
        "grupos": grupos,
        "listas": listas,
        "vistas": vistas,
        "stats": {
            "total": total_tareas,
            "completadas": completadas,
            "pendientes": por_completar,
            "prioridades": prioridades
        }
    }
@app.route('/api/ejecutar', methods=['POST'])
def ejecutar_codigo():
    from semantico import AnalizadorSemantico
    data = request.get_json()
    codigo = data.get('codigo', '')
    sem = AnalizadorSemantico()
    tabla, log, ok, msg, detalle = sem.analizar(codigo)
    if ok:
        global tabla_simbolos
        tabla_simbolos = tabla
        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False, "error": msg}), 400
@app.route('/editor')
def editor():
    return render_template('editor.html')

@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/datos')
def api_datos():
    return jsonify(construir_json_proyecto())