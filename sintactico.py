from lexico import AnalizadorLexico

class Nodo:
    def __init__(self, etiqueta, valor=None, linea=0):
        self.etiqueta = etiqueta
        self.valor = valor
        self.hijos = []
        self.linea = linea

    def agregar(self, hijo):
        self.hijos.append(hijo)
        return hijo

    def hoja(self, lexema, linea=0):
        n = Nodo(lexema, linea=linea)
        self.hijos.append(n)
        return n

    def a_dict(self):
        return {"nombre": self.etiqueta, "linea": self.linea, "hijos": [h.a_dict() for h in self.hijos]}

    def imprimir(self, prefijo="", es_ultimo=True):
        # Método opcional, no se usa en el flujo principal
        pass

    def a_texto(self, prefijo="", es_ultimo=True):
        conector = "└── " if es_ultimo else "├── "
        linea_info = f" (L{self.linea})" if self.linea > 0 else ""
        linea = prefijo + conector + self.etiqueta + linea_info + "\n"
        extension = "    " if es_ultimo else "│   "
        for i, hijo in enumerate(self.hijos):
            linea += hijo.a_texto(prefijo + extension, i == len(self.hijos) - 1)
        return linea

class ErrorSintactico(Exception):
    def __init__(self, mensaje, linea=0):
        super().__init__(mensaje)
        self.linea = linea
        self.mensaje = f"Linea {linea}: {mensaje}" if linea else mensaje

class AnalizadorSintactico:
    def __init__(self):
        self.lexico = AnalizadorLexico()
        self.tokens = []
        self.pos = 0
        self.lineas = []

    def token_actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return ("EOF", "EOF")

    def lexema(self):
        return self.token_actual()[0]

    def tipo(self):
        return self.token_actual()[1]

    def linea_actual(self):
        if self.pos < len(self.lineas):
            return self.lineas[self.pos]
        return 0

    def avanzar(self):
        tok = self.token_actual()
        self.pos += 1
        return tok

    def consumir(self, lexema_esperado=None, tipo_esperado=None):
        lex, tip = self.token_actual()
        linea = self.linea_actual()
        if lexema_esperado and lex != lexema_esperado:
            raise ErrorSintactico(f"Se esperaba '{lexema_esperado}' pero se encontro '{lex}'", linea)
        if tipo_esperado and tip != tipo_esperado:
            raise ErrorSintactico(f"Se esperaba tipo {tipo_esperado} pero se encontro '{lex}' ({tip})", linea)
        self.pos += 1
        return lex

    def es_fin(self):
        return self.pos >= len(self.tokens)

    def analizar(self, texto):
        lineas_texto = texto.splitlines()
        tokens_con_lineas = []
        for num_linea, linea in enumerate(lineas_texto, 1):
            if linea.strip():
                tokens_linea = self.lexico.analizar(linea)
                for token in tokens_linea:
                    tokens_con_lineas.append((token[0], token[1], num_linea))

        self.tokens = [(t[0], t[1]) for t in tokens_con_lineas]
        self.lineas = [t[2] for t in tokens_con_lineas]

        errores_lexicos = [(lex, tip) for lex, tip in self.tokens
                           if tip in ("ERROR_LEXICO", "ERR_INV_DATE", "ERR_INV_TIME")]
        if errores_lexicos:
            msgs = [f"Error lexico: '{lex}' ({tip})" for lex, tip in errores_lexicos]
            return None, "", False, "\n".join(msgs)

        self.pos = 0
        try:
            arbol = self.programa()
            if not self.es_fin():
                lex, tip = self.token_actual()
                raise ErrorSintactico(f"Token inesperado al final: '{lex}'", self.linea_actual())
            return arbol, arbol.a_texto(), True, "Cadena aceptada"
        except ErrorSintactico as e:
            return None, "", False, e.mensaje

    def programa(self):
        nodo = Nodo("PROGRAMA")
        while not self.es_fin():
            nodo.agregar(self.sentencia())
        return nodo

    # ------------------------------------------------------------
    # SENTENCIAS
    # ------------------------------------------------------------
    def sentencia(self):
        lex = self.lexema()
        metodo = self.DISPATCH.get(lex)
        if metodo:
            return getattr(self, metodo)()
        raise ErrorSintactico(f"Instruccion no reconocida: '{lex}'", self.linea_actual())

    DISPATCH = {
        "REG.USR": "sent_reg_usr", "ING.USR": "sent_ing_usr", "CRE.USR": "sent_cre_usr",
        "BUS.USR": "sent_bus_usr", "SALIR": "sent_simple", "MENU": "sent_simple",
        "CRE.GRP": "sent_cre_grp", "ASIG.USR": "sent_asig_usr", "CRE.TAR": "sent_cre_tar",
        "CRE.TAR.IND": "sent_cre_tar", "CRE.TAR.GRP": "sent_cre_tar", "VER.TAR.IND": "sent_ver_tar_ind",
        "ASIG.TAR": "sent_asig_tar", "VER.AVAN": "sent_ver_avan", "CRE.SUBTAR": "sent_cre_subtar",
        "DIV.TAR": "sent_div_tar", "AUTO.EVAL": "sent_autoevaluar", "CAL": "sent_calificar",
        "REC.TAR": "sent_recurrente", "ETIQ.TAR": "sent_etiqueta", "FILTRO.TAR": "sent_filtro",
        "VER.VISTA": "sent_ver_vista", "NOTIF.CUANDO": "sent_notif_cuando",
        "NOTIF.RECORDAR": "sent_notif_recordar", "SUSCRIBIR": "sent_suscribir", "CRE.LIS": "sent_cre_lis",
        "VER.LIS": "sent_ver_lis", "AG.LIS": "sent_ag_lis", "ELIM.LIS": "sent_elim_lis",
        "COM": "sent_comentario", "COM.MEJ": "sent_comentario", "COM.AVAN": "sent_comentario",
        "COM.ASIG": "sent_comentario", "ENV.MSG": "sent_env_msg", "ENV.ENL": "sent_env_enl",
        "VER.MSG": "sent_ver_msg", "IMPORT": "sent_import", "EXPORTAR.TAR": "sent_exportar",
        "USAR.BIB": "sent_usar_bib",
    }

    def abrir(self, nodo):
        nodo.hoja(self.consumir("("), self.linea_actual())

    def cerrar(self, nodo):
        nodo.hoja(self.consumir(")"), self.linea_actual())

    def punto_coma(self, nodo):
        nodo.hoja(self.consumir(";"), self.linea_actual())

    def coma(self, nodo):
        nodo.hoja(self.consumir(","), self.linea_actual())

    def arg_texto_o_cadena(self, nodo_padre, etiqueta="ARG"):
        STOP = {")", ",", ";", "EOF"}
        linea = self.linea_actual()
        if self.lexema() in STOP:
            raise ErrorSintactico(f"Se esperaba un argumento pero se encontro '{self.lexema()}'", linea)
        partes = []
        while not self.es_fin() and self.lexema() not in STOP:
            tok = self.avanzar()
            partes.append(tok[0])
        n = Nodo(etiqueta, linea=linea)
        n.hoja(" ".join(partes), linea)
        nodo_padre.agregar(n)
        return n

    def bloque_par(self, nodo_padre, etiqueta, fn_interior):
        n = Nodo(etiqueta, linea=self.linea_actual())
        nodo_padre.agregar(n)
        self.abrir(n)
        fn_interior(n)
        self.cerrar(n)
        return n

    MODIFICADORES_PRIORIDAD = {"PRI.URG", "PRI.ALT", "PRI.MED", "PRI.BAJ"}
    MODIFICADORES_ESTADO = {"EST.PEN", "EST.ACT", "EST.REV", "EST.COR", "EST.APROB", "EST.RECH", "EST.FIN"}
    KEYWORDS_FECHA = {"HOY", "FIN.MES", "FIN.SEM", "INI.MES", "INI.SEM",
                      "PROX.LUN", "PROX.MAR", "PROX.MIE", "PROX.JUE", "PROX.VIE", "PROX.SAB", "PROX.DOM"}
    UNIDADES_TIEMPO = {"DIA", "DIAS", "SEMANA", "SEMANAS", "MES", "MESES", "ANNO"}

    def modificadores(self, nodo):
        while not self.es_fin() and self.lexema() != ";":
            lex = self.lexema()
            if lex == "DES":
                self.mod_descripcion(nodo)
            elif lex == "FEC":
                self.mod_fecha(nodo)
            elif lex in self.MODIFICADORES_PRIORIDAD:
                m = Nodo("PRIORIDAD", linea=self.linea_actual())
                nodo.agregar(m)
                m.hoja(self.avanzar()[0], self.linea_actual())
            elif lex in self.MODIFICADORES_ESTADO:
                m = Nodo("ESTADO", linea=self.linea_actual())
                nodo.agregar(m)
                m.hoja(self.avanzar()[0], self.linea_actual())
            elif lex == "EN.LIS":
                self.mod_en_lis(nodo)
            elif lex == "ASIG.USR":
                self.mod_asig_usr(nodo)
            elif lex == "LIS.TIT":
                self.mod_lis_tit(nodo)
            elif lex == "LIS.DESC":
                self.mod_lis_desc(nodo)
            else:
                break

    def mod_descripcion(self, nodo):
        m = Nodo("DESCRIPCION", linea=self.linea_actual())
        nodo.agregar(m)
        m.hoja(self.consumir("DES"), self.linea_actual())
        self.abrir(m)
        self.arg_texto_o_cadena(m, "TEXTO")
        self.cerrar(m)

    def mod_fecha(self, nodo):
        m = Nodo("FECHA_MOD", linea=self.linea_actual())
        nodo.agregar(m)
        m.hoja(self.consumir("FEC"), self.linea_actual())
        self.abrir(m)
        self.expr_fecha(m)
        self.cerrar(m)

    def mod_en_lis(self, nodo):
        m = Nodo("EN_LISTA", linea=self.linea_actual())
        nodo.agregar(m)
        m.hoja(self.consumir("EN.LIS"), self.linea_actual())
        self.abrir(m)
        self.arg_texto_o_cadena(m, "NOMBRE_LISTA")
        self.cerrar(m)

    def mod_asig_usr(self, nodo):
        m = Nodo("ASIG_USUARIO", linea=self.linea_actual())
        nodo.agregar(m)
        m.hoja(self.consumir("ASIG.USR"), self.linea_actual())
        self.abrir(m)
        self.arg_texto_o_cadena(m, "USUARIO")
        self.cerrar(m)

    def mod_lis_tit(self, nodo):
        m = Nodo("TITULO_LISTA", linea=self.linea_actual())
        nodo.agregar(m)
        m.hoja(self.consumir("LIS.TIT"), self.linea_actual())
        self.abrir(m)
        self.arg_texto_o_cadena(m, "TEXTO")
        self.cerrar(m)

    def mod_lis_desc(self, nodo):
        m = Nodo("DESC_LISTA", linea=self.linea_actual())
        nodo.agregar(m)
        m.hoja(self.consumir("LIS.DESC"), self.linea_actual())
        self.abrir(m)
        self.arg_texto_o_cadena(m, "TEXTO")
        self.cerrar(m)

    def expr_fecha(self, nodo):
        tip = self.tipo()
        lex = self.lexema()
        ef = Nodo("EXPR_FECHA", linea=self.linea_actual())
        nodo.agregar(ef)
        if tip in ("FECHA", "EXPR_FECHA", "HORA"):
            ef.hoja(self.avanzar()[0], self.linea_actual())
        elif lex == "HOY":
            ef.hoja(self.avanzar()[0], self.linea_actual())
            if self.lexema() in ("+", "-"):
                ef.hoja(self.avanzar()[0], self.linea_actual())
                if self.tipo() != "NUMERO":
                    raise ErrorSintactico("Se esperaba un numero despues de HOY +/-", self.linea_actual())
                ef.hoja(self.avanzar()[0], self.linea_actual())
                if self.lexema() not in self.UNIDADES_TIEMPO:
                    raise ErrorSintactico(f"Se esperaba unidad de tiempo (DIA, SEMANA...) pero se encontro '{self.lexema()}'", self.linea_actual())
                ef.hoja(self.avanzar()[0], self.linea_actual())
        elif lex in self.KEYWORDS_FECHA:
            ef.hoja(self.avanzar()[0], self.linea_actual())
        else:
            raise ErrorSintactico(f"Se esperaba una expresion de fecha pero se encontro '{lex}'", self.linea_actual())
        return ef

    def condicion_simple(self, nodo):
        c = Nodo("CONDICION", linea=self.linea_actual())
        nodo.agregar(c)
        lex = self.lexema()
        if lex == "EST.TAR":
            c.hoja(self.avanzar()[0], self.linea_actual())
            self.abrir(c)
            self.arg_texto_o_cadena(c, "TAREA")
            self.cerrar(c)
            if self.tipo() != "OPERADOR_COMPARACION":
                raise ErrorSintactico(f"Se esperaba operador de comparacion pero se encontro '{self.lexema()}'", self.linea_actual())
            c.hoja(self.avanzar()[0], self.linea_actual())
            if self.lexema() not in self.MODIFICADORES_ESTADO:
                raise ErrorSintactico(f"Se esperaba un estado (EST.PEN, EST.ACT...) pero se encontro '{self.lexema()}'", self.linea_actual())
            c.hoja(self.avanzar()[0], self.linea_actual())
        elif lex in self.MODIFICADORES_PRIORIDAD:
            c.hoja(self.avanzar()[0], self.linea_actual())
        elif lex in self.MODIFICADORES_ESTADO:
            c.hoja(self.avanzar()[0], self.linea_actual())
        elif lex == "ETIQ":
            c.hoja(self.avanzar()[0], self.linea_actual())
            self.abrir(c)
            self.arg_texto_o_cadena(c, "ETIQUETA")
            self.cerrar(c)
        else:
            raise ErrorSintactico(f"Se esperaba una condicion valida pero se encontro '{lex}'", self.linea_actual())
        return c

    def condicion_combinada(self, nodo):
        cc = Nodo("CONDICION_COMBINADA", linea=self.linea_actual())
        nodo.agregar(cc)
        self.condicion_simple(cc)
        while self.tipo() == "OPERADOR_LOGICO":
            cc.hoja(self.avanzar()[0], self.linea_actual())
            self.condicion_simple(cc)
        return cc

    # ---------- SENTENCIAS CONCRETAS ----------
    def sent_reg_usr(self):
        s = Nodo("SENT_REG_USUARIO", linea=self.linea_actual())
        s.hoja(self.consumir("REG.USR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "USUARIO")
        if self.lexema() == ",":
            self.coma(s)
            self.arg_texto_o_cadena(s, "NOMBRE_COMPLETO")
        if self.lexema() == ",":
            self.coma(s)
            rol = self.lexema()
            if rol not in ("ROL.COORD", "ROL.MIEM"):
                raise ErrorSintactico(f"Se esperaba ROL.COORD o ROL.MIEM pero se encontro '{rol}'", self.linea_actual())
            s.hoja(self.avanzar()[0], self.linea_actual())
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_ing_usr(self):
        s = Nodo("SENT_INGRESO_USUARIO", linea=self.linea_actual())
        s.hoja(self.consumir("ING.USR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "USUARIO")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_cre_usr(self):
        s = Nodo("SENT_CREAR_USUARIO", linea=self.linea_actual())
        s.hoja(self.consumir("CRE.USR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "USUARIO")
        self.cerrar(s)
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_bus_usr(self):
        s = Nodo("SENT_BUSCAR_USUARIO", linea=self.linea_actual())
        s.hoja(self.consumir("BUS.USR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "CRITERIO")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_simple(self):
        s = Nodo(f"SENT_{self.lexema()}", linea=self.linea_actual())
        s.hoja(self.avanzar()[0], self.linea_actual())
        self.punto_coma(s)
        return s

    def sent_cre_grp(self):
        s = Nodo("SENT_CREAR_GRUPO", linea=self.linea_actual())
        s.hoja(self.consumir("CRE.GRP"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_GRUPO")
        self.cerrar(s)
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_asig_usr(self):
        s = Nodo("SENT_ASIGNAR_USUARIO", linea=self.linea_actual())
        s.hoja(self.consumir("ASIG.USR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "USUARIO")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_cre_tar(self):
        s = Nodo("SENT_CREAR_TAREA", linea=self.linea_actual())
        s.hoja(self.avanzar()[0], self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_ver_tar_ind(self):
        s = Nodo("SENT_VER_TAREAS_IND", linea=self.linea_actual())
        s.hoja(self.consumir("VER.TAR.IND"), self.linea_actual())
        self.punto_coma(s)
        return s

    def sent_asig_tar(self):
        s = Nodo("SENT_ASIGNAR_TAREA", linea=self.linea_actual())
        s.hoja(self.consumir("ASIG.TAR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_ver_avan(self):
        s = Nodo("SENT_VER_AVANCE", linea=self.linea_actual())
        s.hoja(self.consumir("VER.AVAN"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_cre_subtar(self):
        s = Nodo("SENT_CREAR_SUBTAREA", linea=self.linea_actual())
        s.hoja(self.consumir("CRE.SUBTAR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_SUBTAREA")
        self.cerrar(s)
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_div_tar(self):
        s = Nodo("SENT_DIVIDIR_TAREA", linea=self.linea_actual())
        s.hoja(self.consumir("DIV.TAR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        while self.lexema() == "CRE.SUBTAR":
            sub = Nodo("SUBTAREA", linea=self.linea_actual())
            s.agregar(sub)
            sub.hoja(self.consumir("CRE.SUBTAR"), self.linea_actual())
            self.abrir(sub)
            self.arg_texto_o_cadena(sub, "NOMBRE")
            self.cerrar(sub)
        self.punto_coma(s)
        return s

    def sent_autoevaluar(self):
        s = Nodo("SENT_AUTOEVALUAR", linea=self.linea_actual())
        s.hoja(self.consumir("AUTO.EVAL"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_calificar(self):
        s = Nodo("SENT_CALIFICAR", linea=self.linea_actual())
        s.hoja(self.consumir("CAL"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.coma(s)
        if self.tipo() != "NUMERO":
            raise ErrorSintactico(f"Se esperaba una calificacion numerica pero se encontro '{self.lexema()}'", self.linea_actual())
        s.hoja(self.avanzar()[0], self.linea_actual())
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_recurrente(self):
        s = Nodo("SENT_TAREA_RECURRENTE", linea=self.linea_actual())
        s.hoja(self.consumir("REC.TAR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        if self.lexema() != "CADA":
            raise ErrorSintactico(f"Se esperaba CADA despues de REC.TAR(...) pero se encontro '{self.lexema()}'", self.linea_actual())
        c = Nodo("FRECUENCIA", linea=self.linea_actual())
        s.agregar(c)
        c.hoja(self.consumir("CADA"), self.linea_actual())
        self.abrir(c)
        if self.lexema() not in self.UNIDADES_TIEMPO:
            raise ErrorSintactico(f"Se esperaba unidad de tiempo (DIA, SEMANA, MES...) pero se encontro '{self.lexema()}'", self.linea_actual())
        c.hoja(self.avanzar()[0], self.linea_actual())
        self.cerrar(c)
        if self.lexema() == "HASTA":
            h = Nodo("LIMITE", linea=self.linea_actual())
            s.agregar(h)
            h.hoja(self.consumir("HASTA"), self.linea_actual())
            self.abrir(h)
            self.expr_fecha(h)
            self.cerrar(h)
        if self.lexema() == "A":
            hora_n = Nodo("HORA_EJECUCION", linea=self.linea_actual())
            s.agregar(hora_n)
            hora_n.hoja(self.consumir("A"), self.linea_actual())
            self.abrir(hora_n)
            if self.tipo() != "HORA":
                raise ErrorSintactico(f"Se esperaba una hora (HH:MM) pero se encontro '{self.lexema()}'", self.linea_actual())
            hora_n.hoja(self.avanzar()[0], self.linea_actual())
            self.cerrar(hora_n)
        self.punto_coma(s)
        return s

    def sent_etiqueta(self):
        s = Nodo("SENT_ETIQUETAR", linea=self.linea_actual())
        s.hoja(self.consumir("ETIQ.TAR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        if self.lexema() != "AGREGAR":
            raise ErrorSintactico(f"Se esperaba AGREGAR pero se encontro '{self.lexema()}'", self.linea_actual())
        a = Nodo("AGREGAR", linea=self.linea_actual())
        s.agregar(a)
        a.hoja(self.consumir("AGREGAR"), self.linea_actual())
        self.abrir(a)
        self.arg_texto_o_cadena(a, "ETIQUETA")
        while self.lexema() == ",":
            self.coma(a)
            self.arg_texto_o_cadena(a, "ETIQUETA")
        self.cerrar(a)
        self.punto_coma(s)
        return s

    def sent_filtro(self):
        s = Nodo("SENT_FILTRO", linea=self.linea_actual())
        s.hoja(self.consumir("FILTRO.TAR"), self.linea_actual())
        self.abrir(s)
        self.condicion_combinada(s)
        self.cerrar(s)
        if self.lexema() != "VISTA":
            raise ErrorSintactico(f"Se esperaba VISTA despues del filtro pero se encontro '{self.lexema()}'", self.linea_actual())
        v = Nodo("VISTA", linea=self.linea_actual())
        s.agregar(v)
        v.hoja(self.consumir("VISTA"), self.linea_actual())
        self.abrir(v)
        self.arg_texto_o_cadena(v, "NOMBRE_VISTA")
        self.cerrar(v)
        self.punto_coma(s)
        return s

    def sent_ver_vista(self):
        s = Nodo("SENT_VER_VISTA", linea=self.linea_actual())
        s.hoja(self.consumir("VER.VISTA"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_VISTA")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_notif_cuando(self):
        s = Nodo("SENT_NOTIF_CUANDO", linea=self.linea_actual())
        s.hoja(self.consumir("NOTIF.CUANDO"), self.linea_actual())
        self.abrir(s)
        self.condicion_combinada(s)
        self.cerrar(s)
        if self.lexema() != "ENVIAR":
            raise ErrorSintactico(f"Se esperaba ENVIAR pero se encontro '{self.lexema()}'", self.linea_actual())
        e = Nodo("ENVIAR", linea=self.linea_actual())
        s.agregar(e)
        e.hoja(self.consumir("ENVIAR"), self.linea_actual())
        self.abrir(e)
        self.arg_texto_o_cadena(e, "USUARIO")
        self.cerrar(e)
        self.punto_coma(s)
        return s

    def sent_notif_recordar(self):
        s = Nodo("SENT_NOTIF_RECORDAR", linea=self.linea_actual())
        s.hoja(self.consumir("NOTIF.RECORDAR"), self.linea_actual())
        self.abrir(s)
        usr = Nodo("USUARIO_REF", linea=self.linea_actual())
        s.agregar(usr)
        usr.hoja(self.consumir("USR"), self.linea_actual())
        self.abrir(usr)
        self.arg_texto_o_cadena(usr, "USUARIO")
        self.cerrar(usr)
        self.coma(s)
        fec = Nodo("FECHA_REF", linea=self.linea_actual())
        s.agregar(fec)
        fec.hoja(self.consumir("FEC"), self.linea_actual())
        self.abrir(fec)
        self.expr_fecha(fec)
        self.cerrar(fec)
        self.coma(s)
        self.arg_texto_o_cadena(s, "MENSAJE")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_suscribir(self):
        s = Nodo("SENT_SUSCRIBIR", linea=self.linea_actual())
        s.hoja(self.consumir("SUSCRIBIR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "USUARIO")
        self.coma(s)
        tar = Nodo("TAREA_REF", linea=self.linea_actual())
        s.agregar(tar)
        tar.hoja(self.consumir("TAR"), self.linea_actual())
        self.abrir(tar)
        self.arg_texto_o_cadena(tar, "NOMBRE_TAREA")
        self.cerrar(tar)
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_cre_lis(self):
        s = Nodo("SENT_CREAR_LISTA", linea=self.linea_actual())
        s.hoja(self.consumir("CRE.LIS"), self.linea_actual())
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_ver_lis(self):
        s = Nodo("SENT_VER_LISTA", linea=self.linea_actual())
        s.hoja(self.consumir("VER.LIS"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_LISTA")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_ag_lis(self):
        s = Nodo("SENT_AGREGAR_LISTA", linea=self.linea_actual())
        s.hoja(self.consumir("AG.LIS"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_LISTA")
        self.cerrar(s)
        self.modificadores(s)
        self.punto_coma(s)
        return s

    def sent_elim_lis(self):
        s = Nodo("SENT_ELIMINAR_LISTA", linea=self.linea_actual())
        s.hoja(self.consumir("ELIM.LIS"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_LISTA")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_comentario(self):
        s = Nodo("SENT_COMENTARIO", linea=self.linea_actual())
        s.hoja(self.avanzar()[0], self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        sub = self.lexema()
        if sub in ("COM.MEJ", "COM.AVAN", "COM.ASIG"):
            c = Nodo("CONTENIDO_COMENTARIO", linea=self.linea_actual())
            s.agregar(c)
            c.hoja(self.avanzar()[0], self.linea_actual())
            self.abrir(c)
            self.arg_texto_o_cadena(c, "TEXTO")
            self.cerrar(c)
        self.punto_coma(s)
        return s

    def sent_env_msg(self):
        s = Nodo("SENT_ENVIAR_MENSAJE", linea=self.linea_actual())
        s.hoja(self.consumir("ENV.MSG"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "DESTINATARIO")
        self.coma(s)
        self.arg_texto_o_cadena(s, "MENSAJE")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_env_enl(self):
        s = Nodo("SENT_ENVIAR_ENLACE", linea=self.linea_actual())
        s.hoja(self.consumir("ENV.ENL"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "DESTINATARIO")
        self.coma(s)
        self.arg_texto_o_cadena(s, "ENLACE")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_ver_msg(self):
        s = Nodo("SENT_VER_MENSAJES", linea=self.linea_actual())
        s.hoja(self.consumir("VER.MSG"), self.linea_actual())
        self.punto_coma(s)
        return s

    def sent_import(self):
        s = Nodo("SENT_IMPORTAR", linea=self.linea_actual())
        s.hoja(self.consumir("IMPORT"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "ARCHIVO")
        self.cerrar(s)
        self.punto_coma(s)
        return s

    def sent_exportar(self):
        s = Nodo("SENT_EXPORTAR", linea=self.linea_actual())
        s.hoja(self.consumir("EXPORTAR.TAR"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "NOMBRE_TAREA")
        self.cerrar(s)
        if self.lexema() != "A":
            raise ErrorSintactico(f"Se esperaba A despues de EXPORTAR.TAR(...) pero se encontro '{self.lexema()}'", self.linea_actual())
        d = Nodo("DESTINO", linea=self.linea_actual())
        s.agregar(d)
        d.hoja(self.consumir("A"), self.linea_actual())
        self.abrir(d)
        self.arg_texto_o_cadena(d, "ARCHIVO")
        self.cerrar(d)
        self.punto_coma(s)
        return s

    def sent_usar_bib(self):
        s = Nodo("SENT_USAR_BIBLIOTECA", linea=self.linea_actual())
        s.hoja(self.consumir("USAR.BIB"), self.linea_actual())
        self.abrir(s)
        self.arg_texto_o_cadena(s, "BIBLIOTECA")
        self.cerrar(s)
        self.punto_coma(s)
        return s