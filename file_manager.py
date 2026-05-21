# file_manager.py - CORREGIDO
import os
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional
from werkzeug.utils import secure_filename
from flask import send_file, abort

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {
    'pdf', 'txt', 'json', 'py', 'js', 'html', 'css',
    'png', 'jpg', 'jpeg', 'gif', 'svg', 'md'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class FileManager:
    """Gestiona la subida, descarga y eliminación de archivos adjuntos"""

    def __init__(self):
        self._ensure_upload_folder()

    def _ensure_upload_folder(self):
        Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

    def _get_task_folder(self, task_id: str) -> str:
        """Obtiene la carpeta específica de una tarea"""
        task_folder = os.path.join(UPLOAD_FOLDER, secure_filename(task_id))
        Path(task_folder).mkdir(parents=True, exist_ok=True)
        return task_folder

    def is_allowed_file(self, filename: str) -> bool:
        """Verifica si el archivo está permitido"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_file_size(self, filepath: str) -> int:
        """Obtiene el tamaño del archivo"""
        return os.path.getsize(filepath) if os.path.exists(filepath) else 0

    def save_file(self, task_id: str, file) -> Dict:
        """Guarda un archivo asociado a una tarea"""
        if not file or file.filename == '':
            return {"error": "No se seleccionó ningún archivo"}

        if not self.is_allowed_file(file.filename):
            return {"error": f"Tipo de archivo no permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}"}

        filename = secure_filename(file.filename)
        task_folder = self._get_task_folder(task_id)
        filepath = os.path.join(task_folder, filename)

        # Verificar tamaño
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)

        if size > MAX_FILE_SIZE:
            return {"error": f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE // (1024 * 1024)}MB"}

        # Guardar archivo
        file.save(filepath)

        # Obtener tipo MIME
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        return {
            "success": True,
            "filename": filename,
            "size": size,
            "mime_type": mime_type,
            "path": filepath
        }

    def get_files(self, task_id: str) -> List[Dict]:
        """Obtiene la lista de archivos de una tarea"""
        task_folder = self._get_task_folder(task_id)
        files = []

        if os.path.exists(task_folder):
            for filename in os.listdir(task_folder):
                filepath = os.path.join(task_folder, filename)
                if os.path.isfile(filepath):
                    files.append({
                        "filename": filename,
                        "size": os.path.getsize(filepath),
                        "mime_type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
                        "modified": os.path.getmtime(filepath)
                    })
        return files

    def delete_file(self, task_id: str, filename: str) -> bool:
        """Elimina un archivo de una tarea"""
        filename = secure_filename(filename)
        task_folder = self._get_task_folder(task_id)
        filepath = os.path.join(task_folder, filename)

        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def get_file(self, task_id: str, filename: str):
        """Obtiene un archivo para descarga o previsualización"""
        filename = secure_filename(filename)
        task_folder = self._get_task_folder(task_id)
        filepath = os.path.join(task_folder, filename)

        if not os.path.exists(filepath):
            abort(404)

        return send_file(filepath, as_attachment=False)

    def delete_task_files(self, task_id: str):
        """Elimina todos los archivos de una tarea"""
        task_folder = self._get_task_folder(task_id)
        if os.path.exists(task_folder):
            shutil.rmtree(task_folder)

    def preview_file(self, task_id: str, filename: str) -> Optional[str]:
        """Obtiene el contenido para previsualización"""
        filename = secure_filename(filename)
        task_folder = self._get_task_folder(task_id)
        filepath = os.path.join(task_folder, filename)

        if not os.path.exists(filepath):
            return None

        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

        # Archivos que se pueden previsualizar como texto
        text_extensions = {'txt', 'json', 'py', 'js', 'html', 'css', 'md'}

        if ext in text_extensions:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return None

        # Imágenes se previsualizan como base64
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
        if ext in image_extensions:
            import base64
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')

        return None


# Instancia global
file_manager = FileManager()