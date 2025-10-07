from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem
)

class DriftParamsDialog(QDialog):
    def __init__(self, drift_config, variables, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Drift Settings")
        self.resize(900, 400)
        layout = QVBoxLayout(self)

        # Tạo bảng với 7 cột: baseline, k, h, lambda, L
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Variable", "Load Group", "Baseline", "k", "h", "λ (EWMA)", "L (EWMA)"
        ])
        self.variables = variables
        self.load_to_table(drift_config)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def load_to_table(self, drift_config):
        rows = []
        load_groups = ["low", "high"]
        for var in self.variables:
            cfg = drift_config.get(var, {})
            for group in load_groups:
                vals = cfg.get(group, {
                    "baseline": "", "k": "", "h": "", "lambda": "0.2", "L": "3"
                })
                rows.append([
                    var, group,
                    str(vals.get("baseline", "")),
                    str(vals.get("k", "")),
                    str(vals.get("h", "")),
                    str(vals.get("lambda", "0.2")),
                    str(vals.get("L", "3"))
                ])

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(val))

    def get_params(self):
        params = {}
        for i in range(self.table.rowCount()):
            var = self.table.item(i, 0)
            group = self.table.item(i, 1)
            baseline = self.table.item(i, 2)
            k = self.table.item(i, 3)
            h = self.table.item(i, 4)
            lamb = self.table.item(i, 5)
            L = self.table.item(i, 6)

            if not (var and group and baseline and k and h and lamb and L):
                continue  # skip invalid
            try:
                v = var.text().strip()
                g = group.text().strip()
                b = float(baseline.text())
                k_ = float(k.text())
                h_ = float(h.text())
                l_ = float(lamb.text())
                L_ = float(L.text())
            except Exception:
                continue
            if v not in params:
                params[v] = {}
            params[v][g] = {
                'baseline': b, 'k': k_, 'h': h_, 'lambda': l_, 'L': L_
            }
        return params
