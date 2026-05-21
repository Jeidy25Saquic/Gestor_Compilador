# history_manager.py - Nuevo módulo para historial y versionado
import json
import os
import datetime
from typing import Dict, List, Any, Optional

HISTORY_FILE = "history.json"
MAX_HISTORY_ENTRIES = 100


class HistoryManager:
    """Gestiona el historial de cambios del sistema"""

    def __init__(self):
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_history(self):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            # Mantener solo las últimas MAX_HISTORY_ENTRIES
            to_save = self.history[-MAX_HISTORY_ENTRIES:] if len(self.history) > MAX_HISTORY_ENTRIES else self.history
            json.dump(to_save, f, indent=2, ensure_ascii=False)

    def add_entry(self, usuario: str, accion: str, entidad: str,
                  entidad_id: str, datos_previos: Any, datos_nuevos: Any,
                  descripcion: str = ""):
        """Agrega una entrada al historial"""
        entry = {
            "id": len(self.history) + 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "usuario": usuario,
            "accion": accion,  # "crear", "editar", "eliminar", "mover", "cambiar_estado"
            "entidad": entidad,  # "tarea", "usuario", "grupo", "lista"
            "entidad_id": entidad_id,
            "datos_previos": self._serialize_data(datos_previos),
            "datos_nuevos": self._serialize_data(datos_nuevos),
            "descripcion": descripcion
        }
        self.history.append(entry)
        self._save_history()
        return entry

    def _serialize_data(self, data: Any) -> Any:
        """Serializa datos para almacenamiento"""
        if data is None:
            return None
        if hasattr(data, '__dict__'):
            return {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        return str(data)

    def get_history(self, entidad: str = None, entidad_id: str = None,
                    limit: int = 50) -> List[Dict]:
        """Obtiene el historial filtrado"""
        result = self.history
        if entidad:
            result = [e for e in result if e["entidad"] == entidad]
        if entidad_id:
            result = [e for e in result if e["entidad_id"] == entidad_id]
        return result[-limit:]

    def get_snapshot(self, timestamp: str) -> Optional[Dict]:
        """Obtiene el estado del sistema en un momento específico"""
        # Implementar lógica de snapshot
        for entry in reversed(self.history):
            if entry["timestamp"] <= timestamp:
                return entry["datos_nuevos"]
        return None

    def restore_version(self, entry_id: int) -> Optional[Dict]:
        """Restaura una versión anterior"""
        for entry in self.history:
            if entry["id"] == entry_id:
                return entry["datos_previos"]
        return None

    def clear_history(self, confirm: bool = False):
        """Limpia el historial (solo si el usuario lo confirma)"""
        if confirm:
            self.history = []
            self._save_history()
            return True
        return False


# Instancia global
history_manager = HistoryManager()