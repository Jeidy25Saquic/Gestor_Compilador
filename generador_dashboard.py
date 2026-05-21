# generador_dashboard.py - ACTUALIZADO con nuevos módulos y endpoints
import json
import os
import datetime
from flask import Flask, render_template, jsonify, request, session, send_from_directory
from flask_cors import CORS

# Importar nuevos módulos
from history_manager import history_manager
from file_manager import file_manager
from team_manager import TeamManager

app = Flask(__name__)
app.secret_key = "flowforge_secret_key_2024"
CORS(app)

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
            "tipo": e["tipo"],
            "archivos": file_manager.get_files(e["identificador"]) if e["identificador"] else []
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

    # Vistas
    vistas = []
    for v in tabla_simbolos.a_lista():
        if v["categoria"] == "VISTA":
            vistas.append({"nombre": v["identificador"]})

    # Estadísticas
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

        # Registrar en historial
        history_manager.add_entry(
            usuario=session.get('usuario_actual', 'sistema'),
            accion="compilar",
            entidad="proyecto",
            entidad_id="main",
            datos_previos=None,
            datos_nuevos=construir_json_proyecto(),
            descripcion="Compilación exitosa del código DSL"
        )

        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False, "error": msg}), 400


@app.route('/api/mover_tarea', methods=['POST'])
def mover_tarea():
    global tabla_simbolos
    if tabla_simbolos is None:
        return jsonify({"error": "No hay datos"}), 400

    data = request.get_json()
    nombre = data.get('nombre')
    nuevo_estado = data.get('estado')

    if not nombre or not nuevo_estado:
        return jsonify({"error": "Faltan parámetros"}), 400

    tarea = tabla_simbolos.obtener(nombre)
    if not tarea or tarea["categoria"] != "TAREA":
        return jsonify({"error": "Tarea no encontrada"}), 404

    estado_anterior = tarea.get("estado", "EST.PEN")

    if nuevo_estado not in ("EST.PEN", "EST.ACT", "EST.REV", "EST.COR", "EST.APROB", "EST.RECH", "EST.FIN"):
        return jsonify({"error": "Estado inválido"}), 400

    # Registrar en historial antes del cambio
    history_manager.add_entry(
        usuario=session.get('usuario_actual', 'usuario'),
        accion="mover",
        entidad="tarea",
        entidad_id=nombre,
        datos_previos={"estado": estado_anterior},
        datos_nuevos={"estado": nuevo_estado},
        descripcion=f"Tarea movida de {estado_anterior} a {nuevo_estado}"
    )

    tabla_simbolos.actualizar(nombre, "estado", nuevo_estado, razon="Movimiento en Kanban", linea=0)
    return jsonify({"ok": True})


# ========== NUEVOS ENDPOINTS ==========

# 1. ENDPOINTS PARA ARCHIVOS
@app.route('/api/tarea/<tarea_id>/archivos', methods=['GET'])
def get_tarea_archivos(tarea_id):
    """Obtiene la lista de archivos de una tarea"""
    if tabla_simbolos is None:
        return jsonify({"error": "No hay datos"}), 400

    tarea = tabla_simbolos.obtener(tarea_id)
    if not tarea:
        return jsonify({"error": "Tarea no encontrada"}), 404

    return jsonify({"archivos": file_manager.get_files(tarea_id)})


@app.route('/api/tarea/<tarea_id>/archivos/subir', methods=['POST'])
def subir_archivo(tarea_id):
    """Sube un archivo a una tarea"""
    if tabla_simbolos is None:
        return jsonify({"error": "No hay datos"}), 400

    tarea = tabla_simbolos.obtener(tarea_id)
    if not tarea:
        return jsonify({"error": "Tarea no encontrada"}), 404

    if 'archivo' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    archivo = request.files['archivo']
    resultado = file_manager.save_file(tarea_id, archivo)

    if resultado.get("success"):
        # Registrar en historial
        history_manager.add_entry(
            usuario=session.get('usuario_actual', 'usuario'),
            accion="subir_archivo",
            entidad="tarea",
            entidad_id=tarea_id,
            datos_previos=None,
            datos_nuevos={"archivo": resultado["filename"], "size": resultado["size"]},
            descripcion=f"Archivo '{resultado['filename']}' subido a la tarea"
        )
        return jsonify(resultado)
    else:
        return jsonify({"error": resultado.get("error")}), 400


@app.route('/api/tarea/<tarea_id>/archivos/<filename>/eliminar', methods=['DELETE'])
def eliminar_archivo(tarea_id, filename):
    """Elimina un archivo de una tarea"""
    if file_manager.delete_file(tarea_id, filename):
        history_manager.add_entry(
            usuario=session.get('usuario_actual', 'usuario'),
            accion="eliminar_archivo",
            entidad="tarea",
            entidad_id=tarea_id,
            datos_previos={"archivo": filename},
            datos_nuevos=None,
            descripcion=f"Archivo '{filename}' eliminado de la tarea"
        )
        return jsonify({"success": True})
    return jsonify({"error": "Archivo no encontrado"}), 404


@app.route('/api/tarea/<tarea_id>/archivos/<filename>/descargar', methods=['GET'])
def descargar_archivo(tarea_id, filename):
    """Descarga un archivo"""
    return file_manager.get_file(tarea_id, filename)


@app.route('/api/tarea/<tarea_id>/archivos/<filename>/preview', methods=['GET'])
def preview_archivo(tarea_id, filename):
    """Previsualiza un archivo"""
    contenido = file_manager.preview_file(tarea_id, filename)
    if contenido is not None:
        return jsonify({"content": contenido, "filename": filename})
    return jsonify({"error": "No se puede previsualizar"}), 400


# 2. ENDPOINTS PARA HISTORIAL
@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtiene el historial completo"""
    entidad = request.args.get('entidad')
    entidad_id = request.args.get('entidad_id')
    limit = int(request.args.get('limit', 50))

    history = history_manager.get_history(entidad, entidad_id, limit)
    return jsonify({"history": history, "total": len(history)})


@app.route('/api/history/restore/<int:entry_id>', methods=['POST'])
def restore_version(entry_id):
    """Restaura una versión anterior"""
    global tabla_simbolos

    datos_previos = history_manager.restore_version(entry_id)
    if datos_previos:
        # Aquí se implementaría la lógica de restauración específica
        # Por ahora, registramos la restauración
        history_manager.add_entry(
            usuario=session.get('usuario_actual', 'usuario'),
            accion="restaurar",
            entidad="version",
            entidad_id=str(entry_id),
            datos_previos=None,
            datos_nuevos=datos_previos,
            descripcion=f"Versión {entry_id} restaurada"
        )
        return jsonify({"success": True, "datos": datos_previos})
    return jsonify({"error": "Entrada no encontrada"}), 404


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Limpia el historial (requiere confirmación)"""
    data = request.get_json()
    confirm = data.get('confirm', False)

    if history_manager.clear_history(confirm):
        return jsonify({"success": True})
    return jsonify({"error": "Se requiere confirmación para limpiar el historial"}), 400


# 3. ENDPOINTS PARA EQUIPOS Y FLUJO DE TRABAJO
@app.route('/api/workflow', methods=['GET'])
def get_workflow():
    """Obtiene datos completos del flujo de trabajo"""
    if tabla_simbolos is None:
        return jsonify({"error": "No hay datos"}), 400

    team_mgr = TeamManager(tabla_simbolos)
    usuario = request.args.get('usuario')

    if usuario:
        return jsonify(team_mgr.get_user_workflow(usuario))
    return jsonify(team_mgr.get_workflow_data())


@app.route('/api/workflow/filter', methods=['POST'])
def filter_workflow():
    """Filtra tareas según criterios"""
    if tabla_simbolos is None:
        return jsonify({"error": "No hay datos"}), 400

    data = request.get_json()
    team_mgr = TeamManager(tabla_simbolos)

    # Obtener todas las tareas formateadas
    todas_tareas = []
    for t in tabla_simbolos.por_categoria("TAREA"):
        todas_tareas.append(team_mgr._format_task(t))

    filtradas = team_mgr.filter_tasks(
        todas_tareas,
        usuario=data.get('usuario'),
        equipo=data.get('equipo'),
        estado=data.get('estado'),
        prioridad=data.get('prioridad')
    )

    return jsonify({"tareas": filtradas, "total": len(filtradas)})


# 4. ENDPOINT PARA ACTUALIZAR TAREA COMPLETA
@app.route('/api/tarea/<tarea_id>', methods=['PUT'])
def update_tarea(tarea_id):
    """Actualiza una tarea completa"""
    global tabla_simbolos

    if tabla_simbolos is None:
        return jsonify({"error": "No hay datos"}), 400

    tarea = tabla_simbolos.obtener(tarea_id)
    if not tarea:
        return jsonify({"error": "Tarea no encontrada"}), 404

    data = request.get_json()
    cambios = []

    # Guardar estado anterior
    estado_anterior = {
        "estado": tarea.get("estado"),
        "prioridad": tarea.get("prioridad"),
        "asignado_a": tarea.get("asignado_a"),
        "descripcion": tarea.get("descripcion")
    }

    # Aplicar cambios
    if 'estado' in data and data['estado'] != tarea.get("estado"):
        tabla_simbolos.actualizar(tarea_id, "estado", data['estado'], "Actualización manual", 0)
        cambios.append(f"estado: {estado_anterior['estado']} -> {data['estado']}")

    if 'prioridad' in data and data['prioridad'] != tarea.get("prioridad"):
        tabla_simbolos.actualizar(tarea_id, "prioridad", data['prioridad'], "Actualización manual", 0)
        cambios.append(f"prioridad: {estado_anterior['prioridad']} -> {data['prioridad']}")

    if 'asignado_a' in data and data['asignado_a'] != tarea.get("asignado_a"):
        tabla_simbolos.actualizar(tarea_id, "asignado_a", data['asignado_a'], "Actualización manual", 0)
        cambios.append(f"asignado: {estado_anterior['asignado_a']} -> {data['asignado_a']}")

    if 'descripcion' in data and data['descripcion'] != tarea.get("descripcion"):
        tabla_simbolos.actualizar(tarea_id, "descripcion", data['descripcion'], "Actualización manual", 0)
        cambios.append("descripción actualizada")

    if cambios:
        history_manager.add_entry(
            usuario=session.get('usuario_actual', 'usuario'),
            accion="editar",
            entidad="tarea",
            entidad_id=tarea_id,
            datos_previos=estado_anterior,
            datos_nuevos=data,
            descripcion=f"Tarea actualizada: {', '.join(cambios)}"
        )

    return jsonify({"success": True, "cambios": cambios})


# 5. ENDPOINT PARA SINCRONIZACIÓN CON CODEMIRROR
@app.route('/api/compilar/tiempo-real', methods=['POST'])
def compilar_tiempo_real():
    """Compila código en tiempo real para sincronización con CodeMirror"""
    from semantico import AnalizadorSemantico

    data = request.get_json()
    codigo = data.get('codigo', '')
    sem = AnalizadorSemantico()
    tabla, log, ok, msg, detalle = sem.analizar(codigo)

    if ok:
        global tabla_simbolos
        tabla_simbolos = tabla
        return jsonify({
            "ok": True,
            "errores": [],
            "tareas": len(tabla.por_categoria("TAREA")),
            "usuarios": len(tabla.por_categoria("USUARIO"))
        })
    else:
        return jsonify({
            "ok": False,
            "error": msg,
            "detalle": detalle,
            "linea": detalle.split("Línea ")[1].split(":")[0] if "Línea " in detalle else None
        }), 400


# 6. ENDPOINT PARA OBTENER CÓDIGO ACTUAL
@app.route('/api/codigo', methods=['GET'])
def obtener_codigo_actual():
    """Obtiene el código DSL actual desde la tabla de símbolos"""
    if tabla_simbolos is None:
        return jsonify({"codigo": "", "error": "No hay código cargado"}), 404

    # Generar código DSL a partir de la tabla de símbolos
    lineas = []

    # Usuarios
    for u in tabla_simbolos.por_categoria("USUARIO"):
        lineas.append(f'REG.USR("{u["identificador"]}");')

    # Grupos
    for g in tabla_simbolos.por_categoria("GRUPO"):
        lineas.append(f'CRE.GRP("{g["identificador"]}");')

    # Tareas
    for t in tabla_simbolos.por_categoria("TAREA"):
        params = [f'"{t["identificador"]}"']
        if t.get("prioridad") and t["prioridad"] != "—":
            params.append(t["prioridad"])
        if t.get("fecha_limite") and t["fecha_limite"] != "—":
            params.append(f'FEC({t["fecha_limite"]})')
        lineas.append(f'CRE.TAR({", ".join(params)});')

    return jsonify({"codigo": "\n".join(lineas), "lineas": len(lineas)})


@app.route('/editor')
def editor():
    return render_template('editor.html')


@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/datos')
def api_datos():
    return jsonify(construir_json_proyecto())