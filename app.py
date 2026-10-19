"""Interfaz gráfica del simulador de paginación."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from simulador import Simulation, generate_operations, parse_operations


class SimulationApp(tk.Tk):
    RAM_COLUMNS = 50
    PID_COLORS = (
        "#c6efce", "#ffeb9c", "#f4cccc", "#c9daf8",
        "#d9d2e9", "#fce5cd", "#d0e0e3", "#ead1dc",
    )

    def __init__(self):
        super().__init__()
        self.title("Simulador de paginación - MMU")
        self.geometry("1440x920")
        self.minsize(1100, 700)
        self.simulation = None
        self._configure_styles()
        self._build()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 9))
        style.configure("MetricValue.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=22, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(12, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Simulador de paginación", style="Title.TLabel").pack(side="left")
        self.status = ttk.Label(header, text="No hay simulación cargada")
        self.status.pack(side="right")

        controls = ttk.LabelFrame(
            self, text="Configuración y control", style="Section.TLabelframe", padding=8
        )
        controls.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.seed = tk.StringVar(value="1")
        self.processes = tk.StringVar(value="10")
        self.operations = tk.StringVar(value="500")
        self.algorithm = tk.StringVar(value="FIFO")
        fields = (("Semilla", self.seed), ("Procesos", self.processes), ("Operaciones", self.operations))
        for column, (label, variable) in enumerate(fields):
            ttk.Label(controls, text=label).grid(row=0, column=column * 2, padx=(0, 4))
            ttk.Entry(controls, textvariable=variable, width=10).grid(
                row=0, column=column * 2 + 1, padx=(0, 14)
            )
        ttk.Label(controls, text="Algoritmo").grid(row=0, column=6, padx=(0, 4))
        ttk.Combobox(
            controls, textvariable=self.algorithm,
            values=("FIFO", "SC", "LRU", "LFU"),
            state="readonly", width=12,
        ).grid(row=0, column=7, padx=(0, 14))
        ttk.Button(controls, text="Cargar archivo", command=self.load_file).grid(row=0, column=8, padx=3)
        ttk.Button(controls, text="Generar", command=self.generate).grid(row=0, column=9, padx=3)
        ttk.Button(controls, text="Exportar", command=self.export).grid(row=0, column=10, padx=3)
        ttk.Separator(controls, orient="vertical").grid(row=0, column=11, sticky="ns", padx=8)
        ttk.Button(controls, text="Paso", command=self.step).grid(row=0, column=12, padx=3)
        ttk.Button(controls, text="Ejecutar", command=self.run).grid(row=0, column=13, padx=3)
        self.pause_button = ttk.Button(
            controls, text="Pausar", command=self.toggle_pause, state="disabled"
        )
        self.pause_button.grid(row=0, column=14, padx=3)

        self.content = ttk.Frame(self, padding=(12, 0, 12, 12))
        self.content.grid(row=2, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.columnconfigure(1, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.panels = {}
        self._create_algorithm_panel("OPT", 0)
        self._create_algorithm_panel(self.algorithm.get(), 1)

    def _create_algorithm_panel(self, name, column):
        panel = ttk.LabelFrame(
            self.content, text=f"  {name}  ", style="Section.TLabelframe", padding=6
        )
        panel.grid(row=0, column=column, padx=(0, 8) if column == 0 else (8, 0), sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)

        ram_frame = ttk.LabelFrame(panel, text=f"RAM - {name}", padding=4)
        ram_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ram_frame.columnconfigure(0, weight=1)
        canvas = tk.Canvas(ram_frame, height=43, background="white", highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="ew")
        canvas.bind("<Configure>", lambda event, algorithm=name: self._draw_ram(algorithm))

        table_frame = ttk.LabelFrame(panel, text=f"MMU - {name}", padding=3)
        table_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 6))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("page", "pid", "loaded", "laddr", "maddr", "daddr", "loaded_t", "mark")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
        headings = {
            "page": "PAGE ID", "pid": "PID", "loaded": "LOADED",
            "laddr": "L-ADDR", "maddr": "M-ADDR", "daddr": "D-ADDR",
            "loaded_t": "LOADED-T", "mark": "MARK",
        }
        widths = {"page": 62, "pid": 48, "loaded": 62, "laddr": 64,
                  "maddr": 64, "daddr": 64, "loaded_t": 70, "mark": 58}
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="center", stretch=False)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        for index, color in enumerate(self.PID_COLORS):
            tree.tag_configure(f"pid-{index}", background=color)
        tree.tag_configure("virtual", foreground="#666666")

        metrics_frame = ttk.Frame(panel)
        metrics_frame.grid(row=3, column=0, sticky="ew")
        metrics_frame.columnconfigure((0, 1, 2, 3), weight=1)
        metrics = {}
        metric_names = (
            ("Procesos", "active_processes"),
            ("Sim-Time", "total_time"),
            ("RAM KB", "ram_kb"),
            ("RAM %", "ram_percent"),
            ("V-RAM KB", "virtual_kb"),
            ("V-RAM %", "virtual_percent_of_ram"),
            ("Páginas cargadas", "ram_pages"),
            ("Páginas virtuales", "virtual_pages"),
            ("Thrashing", "thrashing"),
            ("Thrashing %", "thrashing_percent"),
            ("Fragmentación", "internal_fragmentation_kb"),
        )
        for index, (label, key) in enumerate(metric_names):
            cell = ttk.Frame(metrics_frame, relief="solid", borderwidth=1)
            cell.grid(row=index // 3, column=index % 3, sticky="ew")
            ttk.Label(cell, text=label, style="Metric.TLabel").pack()
            value = ttk.Label(cell, text="0", style="MetricValue.TLabel")
            value.pack(pady=(0, 2))
            metrics[key] = value

        self.panels[name] = {
            "panel": panel,
            "canvas": canvas,
            "tree": tree,
            "metrics": metrics,
            "ram_rectangles": [],
        }

    def _set_simulation(self, operations):
        for child in self.content.winfo_children():
            child.destroy()
        self.simulation = Simulation(operations, self.algorithm.get())
        self.panels = {}
        self._create_algorithm_panel("OPT", 0)
        self._create_algorithm_panel(self.algorithm.get(), 1)
        self.pause_button.configure(state="normal", text="Pausar")
        self._render("Simulación preparada")

    def generate(self):
        try:
            operations = generate_operations(
                int(self.seed.get()), int(self.processes.get()), int(self.operations.get())
            )
            self._set_simulation(operations)
        except ValueError as error:
            messagebox.showerror("Configuración inválida", str(error))

    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=(("Texto", "*.txt *.csv"), ("Todos", "*.*"))
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as source:
                self._set_simulation(parse_operations(source.read()))
        except (OSError, ValueError) as error:
            messagebox.showerror("Archivo inválido", str(error))

    def export(self):
        if not self.simulation:
            messagebox.showwarning("Sin simulación", "Prepare una simulación primero")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            self.simulation.export(path)

    def step(self):
        if not self.simulation:
            return
        try:
            result = self.simulation.step()
            self._render(f"Paso {self.simulation.index}/{len(self.simulation.operations)}: {result['operation']}")
        except (RuntimeError, StopIteration, ValueError) as error:
            messagebox.showinfo("Simulación", str(error))

    def run(self):
        if not self.simulation:
            return
        try:
            self.simulation.run()
            self._render("Simulación terminada")
        except (RuntimeError, StopIteration, ValueError) as error:
            messagebox.showerror("Simulación", str(error))

    def toggle_pause(self):
        if not self.simulation:
            return
        if self.simulation.paused:
            self.simulation.resume()
            self.pause_button.configure(text="Pausar")
            self._render("Simulación reanudada")
        else:
            self.simulation.pause()
            self.pause_button.configure(text="Reanudar")
            self._render("Simulación pausada")

    def _draw_ram(self, name):
        if name not in self.panels:
            return
        panel = self.panels[name]
        canvas = panel["canvas"]
        canvas.delete("all")
        width = max(canvas.winfo_width(), 500)
        cell_width = width / 100
        panel["ram_rectangles"] = []
        state = self.simulation.mmus[name].get_state() if self.simulation else None
        ram = state["ram"] if state else [None] * 100
        for index, page in enumerate(ram):
            x1 = index * cell_width
            x2 = (index + 1) * cell_width
            if page is None:
                color = "#ffffff"
                label = ""
            else:
                pid = state["pages"][page]["pid"]
                color = self.PID_COLORS[(pid - 1) % len(self.PID_COLORS)]
                label = str(page)
            canvas.create_rectangle(x1, 5, x2, 35, fill=color, outline="#555555")
            if label and cell_width >= 11:
                canvas.create_text((x1 + x2) / 2, 20, text=label, font=("Segoe UI", 7))
            panel["ram_rectangles"].append((x1, x2))

    def _format_metric(self, key, value):
        if key in ("ram_percent", "virtual_percent_of_ram"):
            return f"{value:.1f}%"
        if key == "thrashing_percent":
            return f"{value:.1f}%"
        if key in ("ram_kb", "virtual_kb", "internal_fragmentation_kb"):
            return f"{value:.2f} KB"
        if key == "thrashing":
            return f"{value}s"
        if key == "total_time":
            return f"{value}s"
        return str(value)

    def _render_table(self, name):
        panel = self.panels[name]
        tree = panel["tree"]
        for item in tree.get_children():
            tree.delete(item)
        if not self.simulation:
            return
        state = self.simulation.mmus[name].get_state()
        for page_id in sorted(state["pages"]):
            page = state["pages"][page_id]
            ptr = state["ptrs"][page["ptr"]]
            loaded = "X" if page["in_ram"] else ""
            frame = page["frame"] if page["in_ram"] else ""
            tag = f"pid-{(page['pid'] - 1) % len(self.PID_COLORS)}"
            if not page["in_ram"]:
                tag = "virtual"
            tree.insert(
                "", "end",
                values=(
                    page_id, page["pid"], loaded, page["ptr"], frame, "",
                    "", "",
                ),
                tags=(tag,),
            )

    def _render(self, message):
        self.status.configure(text=message)
        if not self.simulation:
            return
        snapshot = self.simulation.snapshot()
        for name, panel in self.panels.items():
            if name not in snapshot["algorithms"]:
                continue
            metrics = snapshot["algorithms"][name]
            for key, label in panel["metrics"].items():
                label.configure(text=self._format_metric(key, metrics[key]))
                if key == "thrashing" and metrics["thrashing_warning"]:
                    label.configure(foreground="#b00020")
                else:
                    label.configure(foreground="#111111")
            self._render_table(name)
            self._draw_ram(name)


if __name__ == "__main__":
    SimulationApp().mainloop()
