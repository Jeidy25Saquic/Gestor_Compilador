"""
Analizador Semantico - Lenguaje de Gestion de Proyectos
"""
from sintactico import AnalizadorSintactico, Nodo
import datetime

class ErrorSemantico(Exception):
    def __init__(self, codigo, regla, mensaje, sentencia="", linea=None):
        super().__init__(mensaje)
        self.codigo = codigo
        self.regla = regla
        self.sentencia = sentencia
        self.linea = linea
        linea_str = f"Linea {linea}: " if linea else ""
        self.mensaje = f"{linea_str}[{codigo}] {mensaje}"
        self.detalle = f"Regla violada: {regla} | Sentencia: {sentencia}" if sentencia else f"Regla violada: {regla}"

class TablaSimbolos:
    def __init__(self):
        self._tabla = {}
        self._log = []

    def agregar(self, identificador, categoria, tipo="—", linea=None, contexto="—", **extra):
        entrada = {
            "identificador": identificador,
            "categoria": categoria,
            "tipo": tipo,
            "valor": extra.get("valor", "—"),
            "estado": extra.get("estado", "PENDIENTE"),
            "sesion": extra.get("sesion", "inactiva"),
            "prioridad": extra.get("prioridad", "—"),
            "asignado_a": extra.get("asignado_a", "—"),
            "grupo": extra.get("grupo", "—"),
            "fecha_limite": extra.get("fecha_limite", "—"),
            "descripcion": extra.get("descripcion", "—"),
            "etiquetas": extra.get("etiquetas", []),
            "subtareas": extra.get("subtareas", []),
            "suscriptores": extra.get("suscriptores", []),
            "miembros": extra.get("miembros", []),
            "tareas_lista": extra.get("tareas_lista", []),
            "linea": linea or 0,
            "contexto": contexto,
        }
        self._tabla[identificador] = entrada
        self._log.append({
            "accion": "AGREGAR",
            "detalle": f"[{categoria}] '{identificador}' tipo={tipo}",
            "linea": linea or 0,
            "paso": len(self._log) + 1,
        })

    def actualizar(self, identificador, campo, valor, razon="", linea=None):
        if identificador not in self._tabla:
            return
        anterior = self._tabla[identificador].get(campo, "—")
        self._tabla[identificador][campo] = valor
        self._log.append({
            "accion": "ACTUALIZAR",
            "detalle": f"'{identificador}'.{campo}: '{anterior}' -> '{valor}' ({razon})",
            "linea": linea or 0,
            "paso": len(self._log) + 1,
        })

    def validar(self, identificador, campo, descripcion="", linea=None):
        self._log.append({
            "accion": "VALIDAR",
            "detalle": f"'{identificador}' - {descripcion}",
            "linea": linea or 0,
            "paso": len(self._log) + 1,
        })

    def existe(self, identificador):
        return identificador in self._tabla

    def obtener(self, identificador):
        return self._tabla.get(identificador)

    def por_categoria(self, categoria):
        return [e for e in self._tabla.values() if e["categoria"] == categoria]

    def usuario_activo(self):
        for e in self._tabla.values():
            if e["categoria"] == "USUARIO" and e.get("sesion") == "activa":
                return e["identificador"]
        return None

    def a_lista(self):
        return list(self._tabla.values())

    def log(self):
        return self._log

class AnalizadorSemantico:
    HOY = datetime.date.today()
    PRIORIDADES_VALIDAS = {"PRI.URG", "PRI.ALT", "PRI.MED", "PRI.BAJ"}
    ESTADOS_VALIDOS = {"EST.PEN", "EST.ACT", "EST.REV", "EST.COR", "EST.APROB", "EST.RECH", "EST.FIN"}

    def __init__(self):
        self.sint = AnalizadorSintactico()
        self.tabla = TablaSimbolos()

    def analizar(self, texto):
        self.tabla = TablaSimbolos()
        arbol, _, ok_sint, msg_sint = self.sint.analizar(texto)
        if not ok_sint:
            return self.tabla, [], False, f"[Sintactico] {msg_sint}", ""

        try:
            self._recorrer_programa(arbol)
            return (self.tabla, self.tabla.log(), True, "Analisis semantico correcto", "")
        except ErrorSemantico as e:
            return (self.tabla, self.tabla.log(), False, e.mensaje, e.detalle)

    def _recorrer_programa(self, raiz):
        for sent in raiz.hijos:
            self._despachar(sent)

    DISPATCH = {
        "SENT_REG_USUARIO": "_reg_usuario",
        "SENT_CREAR_USUARIO": "_reg_usuario",
        "SENT_INGRESO_USUARIO": "_ing_usuario",
        "SENT_BUSCAR_USUARIO": "_bus_usuario",
        "SENT_CREAR_GRUPO": "_cre_grupo",
        "SENT_ASIGNAR_USUARIO": "_asig_usuario_solo",
        "SENT_CREAR_TAREA": "_cre_tarea",
        "SENT_ASIGNAR_TAREA": "_asig_tarea",
        "SENT_DIVIDIR_TAREA": "_div_tarea",
        "SENT_CREAR_SUBTAREA": "_cre_subtarea",
        "SENT_TAREA_RECURRENTE": "_rec_tarea",
        "SENT_VER_TAREAS_IND": "_ignorar",
        "SENT_VER_AVANCE": "_ver_avan",
        "SENT_AUTOEVALUAR": "_autoevaluar",
        "SENT_CALIFICAR": "_calificar",
        "SENT_ETIQUETAR": "_etiquetar",
        "SENT_FILTRO": "_filtro",
        "SENT_VER_VISTA": "_ver_vista",
        "SENT_NOTIF_CUANDO": "_notif_cuando",
        "SENT_NOTIF_RECORDAR": "_notif_recordar",
        "SENT_SUSCRIBIR": "_suscribir",
        "SENT_CREAR_LISTA": "_cre_lista",
        "SENT_AGREGAR_LISTA": "_ag_lista",
        "SENT_VER_LISTA": "_ver_lista",
        "SENT_ELIMINAR_LISTA": "_elim_lista",
        "SENT_COMENTARIO": "_comentario",
        "SENT_ENVIAR_MENSAJE": "_env_msg",
        "SENT_ENVIAR_ENLACE": "_env_enl",
        "SENT_VER_MENSAJES": "_ignorar",
        "SENT_IMPORTAR": "_importar",
        "SENT_EXPORTAR": "_exportar",
        "SENT_USAR_BIBLIOTECA": "_usar_bib",
        "SENT_CAMBIAR_ESTADO": "_cambiar_estado",
        "SENT_CAMBIAR_PRIORIDAD": "_cambiar_prioridad",
    }

    def _despachar(self, nodo):
        metodo = self.DISPATCH.get(nodo.etiqueta)
        if metodo:
            getattr(self, metodo)(nodo)

    def _ignorar(self, nodo):
        pass

    def _hijo(self, nodo, etiqueta):
        for h in nodo.hijos:
            if h.etiqueta == etiqueta:
                return h
        return None

    def _valor_hijo(self, nodo, etiqueta):
        h = self._hijo(nodo, etiqueta)
        if h and h.hijos:
            return h.hijos[0].etiqueta.strip('"').strip("'")
        return None

    def _parse_fecha(self, texto):
        try:
            return datetime.date.fromisoformat(texto)
        except Exception:
            return None

    def _nombre_sentencia(self, nodo):
        partes = []
        for h in nodo.hijos:
            if not h.hijos:
                partes.append(h.etiqueta)
            else:
                partes.append(h.etiqueta + "(" + ", ".join(hh.etiqueta for hh in h.hijos) + ")")
        return " ".join(partes[:5])

    def _chk_usuario_existe(self, nombre, sentencia="", linea=None):
        if not nombre or nombre == "—":
            return
        if not self.tabla.existe(nombre):
            raise ErrorSemantico("E002", "R2", f"Usuario '{nombre}' no ha sido registrado", sentencia, linea)
        self.tabla.validar(nombre, "existe", f"usuario existe", linea)

    def _chk_sesion_activa(self, sentencia="", linea=None):
        if not self.tabla.usuario_activo():
            raise ErrorSemantico("E003", "R3", "No hay usuario con sesion activa", sentencia, linea)

    def _chk_grupo_existe(self, nombre, sentencia="", linea=None):
        if not nombre or nombre == "—":
            return
        entrada = self.tabla.obtener(nombre)
        if not entrada or entrada["categoria"] != "GRUPO":
            raise ErrorSemantico("E005", "R6", f"Grupo '{nombre}' no existe", sentencia, linea)
        self.tabla.validar(nombre, "existe", "grupo existe", linea)

    def _chk_tarea_existe(self, nombre, sentencia="", linea=None):
        if not nombre or nombre == "—":
            return
        entrada = self.tabla.obtener(nombre)
        if not entrada or entrada["categoria"] != "TAREA":
            raise ErrorSemantico("E007", "R8", f"Tarea '{nombre}' no declarada", sentencia, linea)
        self.tabla.validar(nombre, "existe", "tarea existe", linea)

    def _chk_lista_existe(self, nombre, sentencia="", linea=None):
        if not nombre or nombre == "—":
            return
        entrada = self.tabla.obtener(nombre)
        if not entrada or entrada["categoria"] != "LISTA":
            raise ErrorSemantico("E014", "R17", f"Lista '{nombre}' no existe", sentencia, linea)
        self.tabla.validar(nombre, "existe", "lista existe", linea)

    def _chk_fecha_valida(self, fecha_str, nombre_tarea, sentencia="", linea=None):
        if not fecha_str or fecha_str in ("—", "PROX.LUN", "FIN.MES", "FIN.SEM", "INI.MES", "INI.SEM", "HOY"):
            return
        fecha = self._parse_fecha(fecha_str)
        if fecha and fecha < self.HOY:
            raise ErrorSemantico("E012", "R14/R15", f"Fecha '{fecha_str}' es anterior a hoy", sentencia, linea)

    # ---------- Métodos existentes (se mantienen igual, solo se añaden los nuevos) ----------
    def _reg_usuario(self, nodo):
        nombre = self._valor_hijo(nodo, "USUARIO")
        if not nombre:
            return
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        if self.tabla.existe(nombre):
            raise ErrorSemantico("E001", "R1", f"Usuario '{nombre}' ya fue registrado", sent, linea)
        rol = "ROL.MIEM"
        for h in nodo.hijos:
            if h.etiqueta in ("ROL.COORD", "ROL.MIEM"):
                rol = h.etiqueta
        nombre_completo = self._valor_hijo(nodo, "NOMBRE_COMPLETO") or "—"
        self.tabla.agregar(nombre, "USUARIO", tipo=rol, valor=nombre_completo, sesion="inactiva", linea=linea)

    def _ing_usuario(self, nodo):
        nombre = self._valor_hijo(nodo, "USUARIO")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_usuario_existe(nombre, sent, linea)
        self.tabla.actualizar(nombre, "sesion", "activa", "ING.USR", linea)

    def _bus_usuario(self, nodo):
        pass

    def _asig_usuario_solo(self, nodo):
        nombre = self._valor_hijo(nodo, "USUARIO")
        linea = getattr(nodo, 'linea', 0)
        self._chk_usuario_existe(nombre, self._nombre_sentencia(nodo), linea)

    def _cre_grupo(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_GRUPO")
        if not nombre:
            return
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        if self.tabla.existe(nombre):
            raise ErrorSemantico("E004", "R5", f"Grupo '{nombre}' ya fue declarado", sent, linea)
        miembros = []
        asig = self._hijo(nodo, "ASIG_USUARIO")
        if asig:
            usr = self._valor_hijo(asig, "USUARIO")
            self._chk_usuario_existe(usr, sent, linea)
            miembros.append(usr)
        self.tabla.agregar(nombre, "GRUPO", tipo="GRP", miembros=miembros, linea=linea)
        if miembros:
            self.tabla.actualizar(nombre, "asignado_a", miembros[0], "coordinador", linea)

    def _cre_tarea(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        if not nombre:
            return
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_sesion_activa(sent, linea)
        if self.tabla.existe(nombre):
            raise ErrorSemantico("E006", "R8", f"Tarea '{nombre}' ya fue declarada", sent, linea)
        tipo = "TAREA"
        for h in nodo.hijos:
            if h.etiqueta == "CRE.TAR.GRP":
                tipo = "TAREA.GRP"
                break
            if h.etiqueta == "CRE.TAR.IND":
                tipo = "TAREA.IND"
                break
        prioridad = "—"
        fecha_lim = "—"
        descripcion = "—"
        asignado = "—"
        for h in nodo.hijos:
            if h.etiqueta == "PRIORIDAD" and h.hijos:
                prioridad = h.hijos[0].etiqueta
            if h.etiqueta == "FECHA_MOD":
                ef = self._hijo(h, "EXPR_FECHA")
                if ef and ef.hijos:
                    fecha_lim = ef.hijos[0].etiqueta
            if h.etiqueta == "DESCRIPCION":
                dn = self._hijo(h, "TEXTO")
                if dn and dn.hijos:
                    descripcion = dn.hijos[0].etiqueta
            if h.etiqueta == "ASIG_USUARIO":
                usr = self._valor_hijo(h, "USUARIO")
                self._chk_usuario_existe(usr, sent, linea)
                asignado = usr
        self._chk_fecha_valida(fecha_lim, nombre, sent, linea)
        usuario_act = self.tabla.usuario_activo()
        grupo_ctx = "—"
        for g in self.tabla.por_categoria("GRUPO"):
            if usuario_act in g.get("miembros", []) or g.get("asignado_a") == usuario_act:
                grupo_ctx = g["identificador"]
                break
        self.tabla.agregar(nombre, "TAREA", tipo=tipo, prioridad=prioridad, fecha_limite=fecha_lim,
                           descripcion=descripcion, contexto=grupo_ctx, asignado_a=asignado, linea=linea)

    def _asig_tarea(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        asig = self._hijo(nodo, "ASIG_USUARIO")
        if asig:
            usr = self._valor_hijo(asig, "USUARIO")
            self._chk_usuario_existe(usr, sent, linea)
            self.tabla.actualizar(nombre, "asignado_a", usr, "ASIG.TAR", linea)

    def _div_tarea(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        entrada = self.tabla.obtener(nombre)
        if entrada.get("subtareas"):
            raise ErrorSemantico("E009", "R11", f"Tarea '{nombre}' ya tiene subtareas", sent, linea)
        nuevas_subs = []
        for h in nodo.hijos:
            if h.etiqueta == "SUBTAREA":
                sub_nom = self._valor_hijo(h, "NOMBRE")
                if sub_nom:
                    if self.tabla.existe(sub_nom):
                        raise ErrorSemantico("E006", "R8", f"Subtarea '{sub_nom}' ya existe", sent, linea)
                    self.tabla.agregar(sub_nom, "TAREA", tipo="SUBTAREA", grupo=nombre, contexto=nombre, linea=linea)
                    nuevas_subs.append(sub_nom)
        self.tabla.actualizar(nombre, "subtareas", nuevas_subs, "DIV.TAR", linea)

    def _cre_subtarea(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_SUBTAREA")
        if not nombre:
            return
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        if self.tabla.existe(nombre):
            raise ErrorSemantico("E006", "R8", f"Subtarea '{nombre}' ya existe", sent, linea)
        self.tabla.agregar(nombre, "TAREA", tipo="SUBTAREA", linea=linea)

    def _rec_tarea(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        if not nombre:
            return
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_sesion_activa(sent, linea)
        if self.tabla.existe(nombre):
            raise ErrorSemantico("E006", "R8", f"Tarea recurrente '{nombre}' ya declarada", sent, linea)
        frec = self._hijo(nodo, "FRECUENCIA")
        tipo_rec = "—"
        if frec and frec.hijos:
            for h in frec.hijos:
                if h.etiqueta not in ("CADA", "(", ")"):
                    tipo_rec = h.etiqueta
        limite = self._hijo(nodo, "LIMITE")
        fecha_str = "—"
        if limite:
            ef = self._hijo(limite, "EXPR_FECHA")
            if ef and ef.hijos:
                fecha_str = ef.hijos[0].etiqueta
                self._chk_fecha_valida(fecha_str, nombre, sent, linea)
        self.tabla.agregar(nombre, "TAREA", tipo=f"RECURRENTE/{tipo_rec}", fecha_limite=fecha_str, linea=linea)

    def _ver_avan(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, self._nombre_sentencia(nodo), linea)

    def _autoevaluar(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        entrada = self.tabla.obtener(nombre)
        usuario_act = self.tabla.usuario_activo()
        asignado = entrada.get("asignado_a", "—")
        if asignado != "—" and usuario_act and asignado != usuario_act:
            raise ErrorSemantico("E010", "R12", f"AUTO.EVAL no permitida: la tarea '{nombre}' esta asignada a '{asignado}'", sent, linea)

    def _calificar(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        calificacion = None
        for h in nodo.hijos:
            if h.etiqueta.isdigit():
                calificacion = int(h.etiqueta)
                break
            try:
                calificacion = int(h.etiqueta)
                break
            except (ValueError, AttributeError):
                pass
        if calificacion is not None and not (0 <= calificacion <= 100):
            raise ErrorSemantico("E011", "R13", f"Calificacion {calificacion} fuera de rango", sent, linea)
        if calificacion is not None:
            self.tabla.actualizar(nombre, "estado", f"CAL:{calificacion}", "calificacion", linea)

    def _etiquetar(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        agregar = self._hijo(nodo, "AGREGAR")
        if agregar:
            etiquetas = [h.hijos[0].etiqueta.strip('"') for h in agregar.hijos if h.etiqueta == "ETIQUETA" and h.hijos]
            entrada = self.tabla.obtener(nombre)
            actuales = entrada.get("etiquetas", [])
            self.tabla.actualizar(nombre, "etiquetas", actuales + etiquetas, "ETIQ.TAR", linea)

    def _filtro(self, nodo):
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        cond_comb = self._hijo(nodo, "CONDICION_COMBINADA")
        if cond_comb:
            for c in cond_comb.hijos:
                if c.etiqueta == "CONDICION":
                    for hh in c.hijos:
                        if hh.etiqueta in self.PRIORIDADES_VALIDAS:
                            self.tabla.validar(hh.etiqueta, "prioridad valida", linea)
                        elif hh.etiqueta in self.ESTADOS_VALIDOS:
                            self.tabla.validar(hh.etiqueta, "estado valido", linea)
                        elif hh.etiqueta == "TAREA":
                            tar = self._valor_hijo(c, "TAREA")
                            if tar:
                                self._chk_tarea_existe(tar, sent, linea)
        vista = self._hijo(nodo, "VISTA")
        if vista:
            nombre_vista = self._valor_hijo(vista, "NOMBRE_VISTA")
            if nombre_vista:
                if self.tabla.existe(nombre_vista):
                    raise ErrorSemantico("E015", "R18", f"Vista '{nombre_vista}' ya existe", sent, linea)
                self.tabla.agregar(nombre_vista, "VISTA", tipo="VISTA/filtro", linea=linea)

    def _ver_vista(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_VISTA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        if nombre and not self.tabla.existe(nombre):
            raise ErrorSemantico("E015", "R18", f"Vista '{nombre}' no existe", sent, linea)
        if nombre:
            self.tabla.validar(nombre, "vista existe", linea)

    def _notif_cuando(self, nodo):
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        cond = self._hijo(nodo, "CONDICION_COMBINADA")
        if cond:
            for c in cond.hijos:
                if c.etiqueta == "CONDICION":
                    tarea_n = self._hijo(c, "TAREA")
                    if tarea_n and tarea_n.hijos:
                        nom = tarea_n.hijos[0].etiqueta
                        self._chk_tarea_existe(nom, sent, linea)
        enviar = self._hijo(nodo, "ENVIAR")
        if enviar:
            usr = self._valor_hijo(enviar, "USUARIO")
            self._chk_usuario_existe(usr, sent, linea)

    def _notif_recordar(self, nodo):
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        usr_ref = self._hijo(nodo, "USUARIO_REF")
        if usr_ref:
            usr = self._valor_hijo(usr_ref, "USUARIO")
            self._chk_usuario_existe(usr, sent, linea)

    def _suscribir(self, nodo):
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        usr = self._valor_hijo(nodo, "USUARIO")
        self._chk_usuario_existe(usr, sent, linea)
        tar_ref = self._hijo(nodo, "TAREA_REF")
        if tar_ref:
            nom_tarea = self._valor_hijo(tar_ref, "NOMBRE_TAREA")
            self._chk_tarea_existe(nom_tarea, sent, linea)
            entrada = self.tabla.obtener(nom_tarea)
            subs = entrada.get("suscriptores", [])
            if usr not in subs:
                self.tabla.actualizar(nom_tarea, "suscriptores", subs + [usr], "SUSCRIBIR", linea)

    def _cre_lista(self, nodo):
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        titulo = None
        tit_n = self._hijo(nodo, "TITULO_LISTA")
        if tit_n:
            t = self._hijo(tit_n, "TEXTO")
            if t and t.hijos:
                titulo = t.hijos[0].etiqueta.strip('"')
        nombre = titulo or f"lista_{len(self.tabla.por_categoria('LISTA')) + 1}"
        if self.tabla.existe(nombre):
            raise ErrorSemantico("E013", "R16", f"Lista '{nombre}' ya fue declarada", sent, linea)
        desc = None
        desc_n = self._hijo(nodo, "DESC_LISTA")
        if desc_n:
            d = self._hijo(desc_n, "TEXTO")
            if d and d.hijos:
                desc = d.hijos[0].etiqueta.strip('"')
        self.tabla.agregar(nombre, "LISTA", tipo="LISTA", descripcion=desc or "—", linea=linea)

    def _ag_lista(self, nodo):
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        nombre_list = self._valor_hijo(nodo, "NOMBRE_LISTA")
        self._chk_lista_existe(nombre_list, sent, linea)
        en_lis = self._hijo(nodo, "EN_LISTA")
        if en_lis:
            tarea = self._valor_hijo(en_lis, "NOMBRE_LISTA")
            self._chk_tarea_existe(tarea, sent, linea)
            entrada = self.tabla.obtener(nombre_list)
            tl = entrada.get("tareas_lista", [])
            if tarea not in tl:
                self.tabla.actualizar(nombre_list, "tareas_lista", tl + [tarea], "AG.LIS", linea)

    def _ver_lista(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_LISTA")
        linea = getattr(nodo, 'linea', 0)
        self._chk_lista_existe(nombre, self._nombre_sentencia(nodo), linea)

    def _elim_lista(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_LISTA")
        linea = getattr(nodo, 'linea', 0)
        self._chk_lista_existe(nombre, self._nombre_sentencia(nodo), linea)

    def _comentario(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, self._nombre_sentencia(nodo), linea)

    def _env_msg(self, nodo):
        dest = self._valor_hijo(nodo, "DESTINATARIO")
        linea = getattr(nodo, 'linea', 0)
        self._chk_usuario_existe(dest, self._nombre_sentencia(nodo), linea)

    def _env_enl(self, nodo):
        dest = self._valor_hijo(nodo, "DESTINATARIO")
        linea = getattr(nodo, 'linea', 0)
        self._chk_usuario_existe(dest, self._nombre_sentencia(nodo), linea)

    def _importar(self, nodo):
        archivo = self._valor_hijo(nodo, "ARCHIVO")
        nombre = archivo or "modulo_importado"
        linea = getattr(nodo, 'linea', 0)
        if not self.tabla.existe(nombre):
            self.tabla.agregar(nombre, "MODULO", tipo="IMPORT", linea=linea)

    def _exportar(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        destino = self._hijo(nodo, "DESTINO")
        if destino:
            arch = self._valor_hijo(destino, "ARCHIVO")
            self.tabla.actualizar(nombre, "descripcion", f"exportada -> {arch}", "EXPORTAR.TAR", linea)

    def _usar_bib(self, nodo):
        nombre = self._valor_hijo(nodo, "BIBLIOTECA")
        linea = getattr(nodo, 'linea', 0)
        if nombre and not self.tabla.existe(nombre):
            self.tabla.agregar(nombre, "BIBLIOTECA", tipo="BIB", linea=linea)

    # ---------- Nuevos métodos ----------
    def _cambiar_estado(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        # Obtener el nuevo estado (tercer hijo hoja)
        nuevo_estado = None
        for h in nodo.hijos:
            if h.etiqueta in self.ESTADOS_VALIDOS:
                nuevo_estado = h.etiqueta
                break
        if not nuevo_estado:
            raise ErrorSemantico("E016", "R19", "No se especificó un estado válido", sent, linea)
        # Verificar permisos: usuario activo debe ser el asignado o coordinador del grupo
        usuario_act = self.tabla.usuario_activo()
        tarea = self.tabla.obtener(nombre)
        asignado = tarea.get("asignado_a", "—")
        if asignado != "—" and usuario_act != asignado:
            # Verificar si es coordinador de algún grupo al que pertenezca la tarea
            grupo_ctx = tarea.get("contexto", "—")
            if grupo_ctx != "—":
                grupo = self.tabla.obtener(grupo_ctx)
                if grupo and usuario_act == grupo.get("asignado_a"):
                    pass  # permitido
                else:
                    raise ErrorSemantico("E017", "R20", f"Usuario '{usuario_act}' no tiene permiso para cambiar estado de la tarea '{nombre}'", sent, linea)
            else:
                raise ErrorSemantico("E017", "R20", f"Usuario '{usuario_act}' no tiene permiso para cambiar estado de la tarea '{nombre}'", sent, linea)
        self.tabla.actualizar(nombre, "estado", nuevo_estado, "CAM.EST", linea)

    def _cambiar_prioridad(self, nodo):
        nombre = self._valor_hijo(nodo, "NOMBRE_TAREA")
        sent = self._nombre_sentencia(nodo)
        linea = getattr(nodo, 'linea', 0)
        self._chk_tarea_existe(nombre, sent, linea)
        nueva_prioridad = None
        for h in nodo.hijos:
            if h.etiqueta in self.PRIORIDADES_VALIDAS:
                nueva_prioridad = h.etiqueta
                break
        if not nueva_prioridad:
            raise ErrorSemantico("E018", "R21", "No se especificó una prioridad válida", sent, linea)
        usuario_act = self.tabla.usuario_activo()
        tarea = self.tabla.obtener(nombre)
        asignado = tarea.get("asignado_a", "—")
        if asignado != "—" and usuario_act != asignado:
            grupo_ctx = tarea.get("contexto", "—")
            if grupo_ctx != "—":
                grupo = self.tabla.obtener(grupo_ctx)
                if grupo and usuario_act == grupo.get("asignado_a"):
                    pass
                else:
                    raise ErrorSemantico("E019", "R22", f"Usuario '{usuario_act}' no tiene permiso para cambiar prioridad de la tarea '{nombre}'", sent, linea)
            else:
                raise ErrorSemantico("E019", "R22", f"Usuario '{usuario_act}' no tiene permiso para cambiar prioridad de la tarea '{nombre}'", sent, linea)
        self.tabla.actualizar(nombre, "prioridad", nueva_prioridad, "CAM.PRI", linea)