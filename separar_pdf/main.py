import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, threading, re

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        raise ImportError("Instala pypdf: pip install pypdf")

# ─── RAZONES SOCIALES ─────────────────────────────────────────────────────────
RAZONES_SOCIALES = {
    "Manufacturas Bancor": "MBCR",
    "LOGYM":               "LGM",
    "AMAGEDON":            "AMG",
}

# ─── COLORES ──────────────────────────────────────────────────────────────────
BG_DARK  = "#0f1b2d"
BG_CARD  = "#16213e"
BG_INPUT = "#1a2a45"
ACCENT   = "#00d2ff"
ACCENT2  = "#3a7bd5"
TEXT     = "#ffffff"
TEXT_DIM = "#7a8fa6"
SUCCESS  = "#4ade80"
ERROR    = "#f87171"
INFO     = "#60a5fa"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Separador de PDF")
        self.geometry("640x720")
        self.resizable(False, False)
        self.configure(bg=BG_DARK)
        self.archivo_path = None
        self.total_paginas = 0
        self.titulares_por_pagina = []
        self.indice_titular = 1   # por defecto: segunda aparición
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_CARD, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📄", font=("Segoe UI Emoji", 28), bg=BG_CARD, fg=ACCENT).pack(side="left", padx=(20, 10))
        info = tk.Frame(hdr, bg=BG_CARD)
        info.pack(side="left")
        tk.Label(info, text="Separador de PDF", font=("Segoe UI", 14, "bold"),
                 bg=BG_CARD, fg=TEXT).pack(anchor="w")
        tk.Label(info, text="Divide cada página en un archivo PDF individual",
                 font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=24, pady=18)

        # ── Selección de archivo ──
        self._section_label(body, "📂  Archivo PDF")
        file_frame = tk.Frame(body, bg=BG_INPUT, highlightthickness=2,
                              highlightbackground=ACCENT2, highlightcolor=ACCENT)
        file_frame.pack(fill="x", pady=(4, 14))
        self.lbl_archivo = tk.Label(file_frame, text="Ningún archivo seleccionado",
                                    font=("Segoe UI", 9), bg=BG_INPUT, fg=TEXT_DIM,
                                    anchor="w", padx=12, pady=10)
        self.lbl_archivo.pack(side="left", fill="x", expand=True)
        self._btn(file_frame, "Examinar", self._seleccionar_archivo, side="right", padx=8, pady=6)

        # ── Razón social ──
        self._section_label(body, "🏢  Razón social")
        self.razon_var = tk.StringVar(value=list(RAZONES_SOCIALES.keys())[0])
        razon_frame = tk.Frame(body, bg=BG_INPUT, highlightthickness=1,
                               highlightbackground=ACCENT2, highlightcolor=ACCENT)
        razon_frame.pack(fill="x", pady=(4, 14))
        style_cb = ttk.Style()
        style_cb.theme_use("clam")
        style_cb.configure("TCombobox",
                           fieldbackground=BG_INPUT, background=BG_INPUT,
                           foreground=TEXT, selectbackground=ACCENT2,
                           selectforeground=TEXT, bordercolor=ACCENT2,
                           arrowcolor=ACCENT)
        self.combo_razon = ttk.Combobox(
            razon_frame, textvariable=self.razon_var,
            values=list(RAZONES_SOCIALES.keys()),
            state="readonly", font=("Segoe UI", 10)
        )
        self.combo_razon.pack(fill="x", ipady=6, padx=2, pady=2)
        self.combo_razon.bind("<<ComboboxSelected>>", self._on_razon_change)

        # ── Páginas detectadas ──
        self._section_label(body, "📋  Páginas detectadas (titular extraído)")
        paginas_outer = tk.Frame(body, bg=BG_INPUT, height=110,
                                 highlightthickness=1, highlightbackground=ACCENT2)
        paginas_outer.pack(fill="x", pady=(4, 14))
        paginas_outer.pack_propagate(False)
        self.canvas_paginas = tk.Canvas(paginas_outer, bg=BG_INPUT, highlightthickness=0,
                                        height=110)
        scroll_pag = tk.Scrollbar(paginas_outer, orient="vertical",
                                  command=self.canvas_paginas.yview, bg=BG_INPUT)
        self.canvas_paginas.configure(yscrollcommand=scroll_pag.set)
        scroll_pag.pack(side="right", fill="y")
        self.canvas_paginas.pack(side="left", fill="both", expand=True)
        self.frame_paginas = tk.Frame(self.canvas_paginas, bg=BG_INPUT)
        self._canvas_window = self.canvas_paginas.create_window(
            (0, 0), window=self.frame_paginas, anchor="nw"
        )
        self.frame_paginas.bind(
            "<Configure>",
            lambda e: self.canvas_paginas.configure(
                scrollregion=self.canvas_paginas.bbox("all")
            )
        )
        self.canvas_paginas.bind(
            "<Configure>",
            lambda e: self.canvas_paginas.itemconfig(self._canvas_window, width=e.width)
        )
        self.lbl_paginas = tk.Label(self.frame_paginas,
                                    text="— Carga un archivo para ver las páginas —",
                                    font=("Segoe UI", 9), bg=BG_INPUT, fg=TEXT_DIM)
        self.lbl_paginas.pack(expand=True)

        # ── Preview ──
        self._section_label(body, "👁️  Vista previa del nombre")
        self.lbl_preview = tk.Label(body, text="—", font=("Segoe UI", 9, "italic"),
                                    bg=BG_INPUT, fg=ACCENT, anchor="w", padx=12, pady=8,
                                    highlightthickness=1, highlightbackground=ACCENT2)
        self.lbl_preview.pack(fill="x", pady=(4, 18))

        # ── Botón exportar ──
        self.btn_exportar = tk.Button(
            body, text="⬇️  Exportar páginas separadas",
            font=("Segoe UI", 11, "bold"), bg=ACCENT2, fg=TEXT,
            activebackground=ACCENT, activeforeground=TEXT,
            relief="flat", bd=0, pady=12, cursor="hand2",
            state="disabled", command=self._exportar_thread
        )
        self.btn_exportar.pack(fill="x", pady=(0, 14))

        # ── Progreso ──
        style = ttk.Style()
        style.configure("TProgressbar", troughcolor=BG_INPUT, background=ACCENT, thickness=8)
        self.progress = ttk.Progressbar(body, length=100, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 4))
        self.lbl_progress = tk.Label(body, text="", font=("Segoe UI", 8),
                                     bg=BG_DARK, fg=TEXT_DIM)
        self.lbl_progress.pack(anchor="e")

        # ── Log ──
        self._section_label(body, "📜  Registro")
        log_frame = tk.Frame(body, bg=BG_INPUT, highlightthickness=1, highlightbackground=ACCENT2)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.log_text = tk.Text(log_frame, bg=BG_INPUT, fg=TEXT_DIM,
                                font=("Consolas", 8), relief="flat",
                                state="disabled", height=8, padx=10, pady=8,
                                insertbackground=TEXT, wrap="word")
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=BG_INPUT)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("success", foreground=SUCCESS)
        self.log_text.tag_config("error",   foreground=ERROR)
        self.log_text.tag_config("info",    foreground=INFO)

    # ── Helpers UI ────────────────────────────────────────────────────────────
    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 8),
                 bg=parent.cget("bg"), fg=TEXT_DIM).pack(anchor="w", pady=(0, 2))

    def _btn(self, parent, text, cmd, side="left", padx=0, pady=0):
        b = tk.Button(parent, text=text, font=("Segoe UI", 9, "bold"),
                      bg=ACCENT2, fg=TEXT, activebackground=ACCENT,
                      activeforeground=TEXT, relief="flat", bd=0,
                      padx=padx, pady=pady, cursor="hand2", command=cmd)
        b.pack(side=side, padx=6, pady=6)
        return b

    # ── Helpers lógica ────────────────────────────────────────────────────────
    def _normalizar(self, texto):
        return texto.strip().replace(" ", "_")

    def _extraer_matches_titular(self, pagina):
        """Devuelve todos los valores encontrados para 'Titular de la cuenta'."""
        texto = pagina.extract_text() or ""
        # Dividir el texto en cada aparición del campo; partes[1], [2]... son los valores
        partes = re.split(r"Titular de la cuenta[:\s]*", texto, flags=re.IGNORECASE)
        return [p.strip().split("\n")[0].strip() for p in partes[1:] if p.strip()]

    def _extraer_titular(self, pagina, razon_social):
        matches = self._extraer_matches_titular(pagina)
        if not matches:
            return None
        idx = min(self.indice_titular, len(matches) - 1)
        return self._normalizar(matches[idx])

    def _elegir_titular(self, reader):
        """
        Busca la primera página con 2+ apariciones y muestra un diálogo
        para que el usuario elija cuál usar. Actualiza self.indice_titular.
        """
        opciones = None
        for pagina in reader.pages:
            m = self._extraer_matches_titular(pagina)
            if len(m) >= 2:
                opciones = m
                break

        if opciones is None:
            return  # solo una aparición, no hace falta preguntar

        # ── Diálogo modal ───────────────────────────────────────────────
        dialogo = tk.Toplevel(self)
        dialogo.title("Seleccionar campo")
        dialogo.configure(bg=BG_DARK)
        dialogo.resizable(False, False)
        dialogo.grab_set()

        tk.Label(dialogo,
                 text="Se encontraron varios campos 'Titular de la cuenta'.\n"
                      "Elige cuál usar como nombre de archivo:",
                 font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT,
                 justify="left", padx=20, pady=8).pack(pady=(16, 4))

        seleccion = tk.IntVar(value=self.indice_titular)

        for i, opcion in enumerate(opciones[:4]):   # máximo 4 opciones
            tk.Radiobutton(
                dialogo,
                text=f"  [{i+1}]  {opcion}",
                variable=seleccion, value=i,
                font=("Segoe UI", 10),
                bg=BG_DARK, fg=TEXT,
                activebackground=BG_DARK, activeforeground=ACCENT,
                selectcolor=BG_INPUT,
                anchor="w", padx=24
            ).pack(fill="x", pady=2)

        def confirmar():
            self.indice_titular = seleccion.get()
            dialogo.destroy()

        tk.Button(
            dialogo, text="Confirmar",
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT2, fg=TEXT, activebackground=ACCENT,
            relief="flat", bd=0, padx=20, pady=8,
            cursor="hand2", command=confirmar
        ).pack(pady=(12, 16))

        self.wait_window(dialogo)

    def _recargar_titulares(self):
        """Re-extrae titulares con la razón social actualmente seleccionada."""
        if not self.archivo_path:
            return
        razon = self.razon_var.get()
        try:
            reader = PdfReader(self.archivo_path)
            self.titulares_por_pagina = [self._extraer_titular(p, razon) for p in reader.pages]
            self._mostrar_paginas()
            self._update_preview()
        except Exception as ex:
            self._log(f"❌ Error al re-extraer titulares: {ex}", "error")

    # ── Eventos ───────────────────────────────────────────────────────────────
    def _on_razon_change(self, event=None):
        """Al cambiar la razón social, re-extrae titulares y actualiza la vista."""
        self._recargar_titulares()

    # ── Lógica ────────────────────────────────────────────────────────────────
    def _seleccionar_archivo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        self.archivo_path = path
        nombre = os.path.basename(path)

        try:
            razon = self.razon_var.get()
            reader = PdfReader(path)
            self.total_paginas = len(reader.pages)
            self._elegir_titular(reader)
            self.titulares_por_pagina = [self._extraer_titular(p, razon) for p in reader.pages]
            self.lbl_archivo.config(text=f"  {nombre}", fg=TEXT)
            self._mostrar_paginas()
            self._update_preview()
            self.btn_exportar.config(state="normal")
            self._log(f"📂 Archivo cargado: {nombre} ({self.total_paginas} páginas)", "info")
        except Exception as ex:
            self._log(f"❌ Error al leer: {ex}", "error")

    def _mostrar_paginas(self):
        for w in self.frame_paginas.winfo_children():
            w.destroy()
        for i in range(self.total_paginas):
            titular = self.titulares_por_pagina[i] or "⚠️ No encontrado"
            tk.Label(self.frame_paginas, text=f"Pág {i+1}:", font=("Segoe UI", 8, "bold"),
                     bg=BG_INPUT, fg=ACCENT, padx=8).grid(row=i, column=0, sticky="w", pady=2)
            tk.Label(self.frame_paginas, text=titular, font=("Segoe UI", 8),
                     bg=BG_INPUT, fg=TEXT_DIM).grid(row=i, column=1, sticky="w", padx=(0, 8))

    def _update_preview(self):
        if not self.total_paginas:
            return
        abrev = RAZONES_SOCIALES.get(self.razon_var.get(), "???")
        ejemplos = []
        for i, t in enumerate(self.titulares_por_pagina[:3]):
            titular = t or "Sin_titular"
            ejemplos.append(f"{abrev}_{titular}.pdf")
        self.lbl_preview.config(text="  " + "  |  ".join(ejemplos))

    def _exportar_thread(self):
        threading.Thread(target=self._exportar, daemon=True).start()

    def _exportar(self):
        # Re-extraer con la razón social actual por si cambió después de cargar
        razon = self.razon_var.get()
        abrev = RAZONES_SOCIALES.get(razon, "???")

        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if not carpeta:
            return

        self.btn_exportar.config(state="disabled")
        self.progress["value"] = 0

        try:
            reader = PdfReader(self.archivo_path)
            total  = len(reader.pages)
            # Re-extraer titulares con la razón social actual
            titulares = [self._extraer_titular(p, razon) for p in reader.pages]
            conteo_titulares = {}

            for i, pagina in enumerate(reader.pages):
                titular = titulares[i] or f"pagina_{i+1}"
                conteo_titulares[titular] = conteo_titulares.get(titular, 0) + 1
                sufijo = f"_{conteo_titulares[titular]}" if conteo_titulares[titular] > 1 else ""
                nombre_archivo = f"{abrev}_{titular}{sufijo}.pdf"
                ruta_salida = os.path.join(carpeta, nombre_archivo)
                try:
                    writer = PdfWriter()
                    writer.add_page(pagina)
                    with open(ruta_salida, "wb") as f:
                        writer.write(f)
                    self._log(f"✅ {nombre_archivo}", "success")
                except Exception as ex:
                    self._log(f"❌ Error en página {i+1}: {ex}", "error")

                pct = int(((i + 1) / total) * 100)
                self.progress["value"] = pct
                self.lbl_progress.config(text=f"{pct}% — {i+1}/{total} páginas")
                self.update_idletasks()

        except Exception as ex:
            self._log(f"❌ No se pudo procesar el PDF: {ex}", "error")
            self.btn_exportar.config(state="normal")
            return

        self._log(f"🎉 ¡Listo! {total} archivos guardados en: {carpeta}", "info")
        self.btn_exportar.config(state="normal")
        messagebox.showinfo("Completado", f"✅ {total} páginas exportadas correctamente.")

    def _log(self, msg, tag=""):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()