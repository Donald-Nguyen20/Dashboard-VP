"""
Monitoring System - Cửa sổ chính cho tab Monitoring.
"""
from __future__ import annotations
import os
import sys
from PySide6.QtWidgets import QMainWindow, QTabWidget
from Monitoring.tabs.monitoring_main_tab import MonitoringMainTab


class Monitoring_Tab(QMainWindow):
    """Cửa sổ chính của bộ ứng dụng Monitoring System."""
    def __init__(self, df_provider=None, plot_provider=None):
        super().__init__()
        self.setWindowTitle("Monitoring Dashboard")
        self.resize(1400, 800)
        self.setObjectName("MonitoringDashboardWindow")

        tabs = QTabWidget(self)
        tabs.setTabPosition(QTabWidget.North)
        tabs.setDocumentMode(True)
        tabs.setTabsClosable(False)
        self.setCentralWidget(tabs)

        self.monitoring_main = MonitoringMainTab(self, df_provider=df_provider, plot_provider=plot_provider)
        tabs.addTab(self.monitoring_main, "Monitoring")
