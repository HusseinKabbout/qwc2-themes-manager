# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ThemeSettingsDialog
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

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'theme_settings.ui'))


class ThemeSettingsDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        super(ThemeSettingsDialog, self).__init__(parent)
        self.setupUi(self)
