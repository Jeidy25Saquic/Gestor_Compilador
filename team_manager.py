# team_manager.py - Nuevo módulo para gestión de equipos y flujo de trabajo
from typing import Dict, List, Any
from collections import defaultdict


class TeamManager:
    """Gestiona la relación usuarios-equipos-tareas y el flujo de trabajo visual"""

    def __init__(self, tabla_simbolos):
        self.tabla = tabla_simbolos

    def get_user_teams(self, usuario: str) -> List[Dict]:
        """Obtiene los equipos a los que pertenece un usuario"""
        teams = []
        for grupo in self.tabla.por_categoria("GRUPO"):
            if usuario in grupo.get("miembros", []) or grupo.get("asignado_a") == usuario:
                teams.append({
                    "nombre": grupo["identificador"],
                    "rol": "coordinador" if grupo.get("asignado_a") == usuario else "miembro",
                    "miembros": grupo.get("miembros", [])
                })
        return teams

    def get_team_tasks(self, equipo: str) -> List[Dict]:
        """Obtiene todas las tareas de un equipo"""
        tasks = []
        for tarea in self.tabla.por_categoria("TAREA"):
            if tarea.get("contexto") == equipo:
                tasks.append(self._format_task(tarea))
            # También tareas asignadas a miembros del equipo
            elif tarea.get("asignado_a") != "—":
                grupo = self._get_user_group(tarea.get("asignado_a"))
                if grupo and grupo["identificador"] == equipo:
                    tasks.append(self._format_task(tarea))
        return tasks

    def _get_user_group(self, usuario: str) -> Dict:
        for grupo in self.tabla.por_categoria("GRUPO"):
            if usuario in grupo.get("miembros", []) or grupo.get("asignado_a") == usuario:
                return grupo
        return None

    def _format_task(self, tarea: Dict) -> Dict:
        """Formatea una tarea para visualización"""
        return {
            "nombre": tarea["identificador"],
            "estado": tarea.get("estado", "PENDIENTE"),
            "prioridad": tarea.get("prioridad", "—"),
            "fecha_limite": tarea.get("fecha_limite", "—"),
            "asignado_a": tarea.get("asignado_a", "—"),
            "descripcion": tarea.get("descripcion", "—"),
            "etiquetas": tarea.get("etiquetas", []),
            "subtareas": tarea.get("subtareas", []),
            "progreso": self._calculate_progress(tarea)
        }

    def _calculate_progress(self, tarea: Dict) -> int:
        """Calcula el progreso de una tarea basado en subtareas"""
        subtareas = tarea.get("subtareas", [])
        if not subtareas:
            # Si no tiene subtareas, 100% si está finalizada
            return 100 if tarea.get("estado") == "EST.FIN" else 0

        completadas = 0
        for sub_id in subtareas:
            sub = self.tabla.obtener(sub_id)
            if sub and sub.get("estado") == "EST.FIN":
                completadas += 1
        return int((completadas / len(subtareas)) * 100)

    def get_workflow_data(self) -> Dict:
        """Obtiene datos completos para el flujo de trabajo visual"""
        users = []
        for usuario in self.tabla.por_categoria("USUARIO"):
            user_data = {
                "nombre": usuario["identificador"],
                "rol": usuario.get("tipo", "ROL.MIEM"),
                "sesion": usuario.get("sesion", "inactiva"),
                "equipos": self.get_user_teams(usuario["identificador"]),
                "tareas": []
            }

            # Tareas asignadas a este usuario
            for tarea in self.tabla.por_categoria("TAREA"):
                if tarea.get("asignado_a") == usuario["identificador"]:
                    user_data["tareas"].append(self._format_task(tarea))

            users.append(user_data)

        teams = []
        for grupo in self.tabla.por_categoria("GRUPO"):
            teams.append({
                "nombre": grupo["identificador"],
                "coordinador": grupo.get("asignado_a", "—"),
                "miembros": grupo.get("miembros", []),
                "tareas": self.get_team_tasks(grupo["identificador"])
            })

        return {
            "usuarios": users,
            "equipos": teams,
            "estadisticas": {
                "total_usuarios": len(users),
                "total_equipos": len(teams),
                "total_tareas": len(self.tabla.por_categoria("TAREA")),
                "tareas_completadas": len(
                    [t for t in self.tabla.por_categoria("TAREA") if t.get("estado") == "EST.FIN"])
            }
        }

    def get_user_workflow(self, usuario: str) -> Dict:
        """Obtiene el flujo de trabajo específico de un usuario"""
        equipos = self.get_user_teams(usuario)

        workflow = {
            "usuario": usuario,
            "equipos": equipos,
            "tareas_personales": [],
            "tareas_equipo": defaultdict(list),
            "estadisticas": {
                "pendientes": 0,
                "en_curso": 0,
                "revision": 0,
                "completadas": 0
            }
        }

        # Tareas personales
        for tarea in self.tabla.por_categoria("TAREA"):
            if tarea.get("asignado_a") == usuario:
                task_data = self._format_task(tarea)
                workflow["tareas_personales"].append(task_data)
                self._update_stats(workflow["estadisticas"], task_data["estado"])

        # Tareas por equipo
        for equipo in equipos:
            for tarea in self.get_team_tasks(equipo["nombre"]):
                if tarea["asignado_a"] != usuario:  # No duplicar personales
                    workflow["tareas_equipo"][equipo["nombre"]].append(tarea)
                    self._update_stats(workflow["estadisticas"], tarea["estado"])

        return workflow

    def _update_stats(self, stats: Dict, estado: str):
        if estado == "EST.PEN":
            stats["pendientes"] += 1
        elif estado == "EST.ACT":
            stats["en_curso"] += 1
        elif estado == "EST.REV":
            stats["revision"] += 1
        elif estado == "EST.FIN":
            stats["completadas"] += 1

    def filter_tasks(self, tasks: List[Dict], usuario: str = None,
                     equipo: str = None, estado: str = None,
                     prioridad: str = None) -> List[Dict]:
        """Filtra tareas según criterios"""
        result = tasks

        if usuario:
            result = [t for t in result if t.get("asignado_a") == usuario]

        if equipo:
            result = [t for t in result if t.get("contexto") == equipo]

        if estado:
            result = [t for t in result if t.get("estado") == estado]

        if prioridad:
            result = [t for t in result if t.get("prioridad") == prioridad]

        return result
    