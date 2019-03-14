# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ThemesManager
                                 A QGIS plugin
 This plugin lets users configure QWC2 Themes with a UI
                              -------------------
        begin                : 2019-03-12
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Hussein Kabbout
        email                : hussein.kabbout@sourcepole.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction
from .resources import *

from .themes_manager_dockwidget import ThemeManagerDockWidget


class ThemesManager:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        icon_path = ":/plugins/qwc2-themes-manager/icon.png"
        self.action = QAction(QIcon(icon_path), "Themes Manager",
                              self.iface.mainWindow())
        self.action.triggered.connect(self.show_hide_dockwidget)
        self.iface.addToolBarIcon(self.action)

        self.dockWidget = ThemeManagerDockWidget(
            self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockWidget)

    def unload(self):
        self.iface.removePluginMenu("QWC2 Themes Manager",
                                    self.action)
        self.iface.removeToolBarIcon(self.action)
        self.dockWidget.save_paths()
        self.iface.removeDockWidget(self.dockWidget)

    def show_hide_dockwidget(self):
        if self.dockWidget.isVisible():
            self.dockWidget.hide()
        else:
            self.dockWidget.show()
