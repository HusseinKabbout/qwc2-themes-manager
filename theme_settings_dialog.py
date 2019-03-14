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
import json
import os
from shutil import copyfile
from qgis.core import *
from qgis.PyQt import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'theme_settings.ui'))


class ThemeSettingsDialog(QDialog, FORM_CLASS):

    def __init__(self, parent, method, iface):
        super(ThemeSettingsDialog, self).__init__(parent)
        self.setupUi(self)

        self.method = method
        self.iface = iface
        self.settings = QSettings()
        self.buttonBox.button(QDialogButtonBox.Apply).setText("Create")
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            self.save_theme)
        self.thumbnail_button.clicked.connect(self.open_thumbnail_fileBrowser)

        self.prepate_dlg()

    def prepate_dlg(self):
        if self.method == "create":
            self.title_lineEdit.setText(QgsProject.instance().baseName())
            self.mapCrs_widget.setCrs(QgsProject.instance().crs())
            self.extent_lineEdit.setText(
                self.iface.mapCanvas().extent().toString(0).replace(
                    " : ", ","))

    def save_theme(self):
        if not self.check_inputs():
            return
        if not self.url_lineEdit.text():
            QMessageBox.warning(None, "Missing parameter",
                                "WMS url of the project is missing!")
            return
        new_theme = {}
        for child in self.children():
            child_name = child.objectName().split("_")[0]
            if child_name == "extent" or child_name == "scales" or child_name == "printScales" or child_name == "printResolutions":
                numbers = []
                for num in child.text().split(","):
                    if num:
                        numbers.append(int(num.strip()))
                if numbers:
                    new_theme[child_name] = numbers
                continue
            elif isinstance(child, QLineEdit):
                if child.text():
                    if child_name == "thumbnail":
                        if not self.copy_thumbnail(child.text()):
                            return
                        new_theme[child_name] = os.path.basename(child.text())
                        continue
                    new_theme[child_name] = child.text()
            elif isinstance(child, QCheckBox):
                new_theme[child_name] = child.isChecked()
        new_theme["mapCrs"] = self.mapCrs_widget.crs().authid()
        new_theme["format"] = self.format_comboBox.currentText()
        path = os.path.join(self.settings.value(
            "qwc2-themes-manager/qwc2_directory"), "themesConfig.json")
        try:
            themes_config = open(path, "r", encoding="utf-8")
            config = json.load(themes_config)
            if "themes" not in config.keys() or "items" not in config["themes"].keys():
                config["themes"] = {"items": []}
            config["themes"]["items"].append(new_theme)
            themes_config.close()
            themes_config = open(path, "w", encoding="utf-8")
            themes_config.write(json.dumps(config, indent=2))
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Cannot create/override themes configuration file"
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Cannot create/override file: %s." % path,
                "QWC2 Theme Manager", Qgis.Critical)
        self.close()

    def check_inputs(self):
        lineEdits_to_check = [self.scales_lineEdit,
                              self.printScales_lineEdit,
                              self.printResolutions_lineEdit,
                              self.extent_lineEdit]

        for lineEdit in lineEdits_to_check:
            lineEdit.setStyleSheet("background: #FFFFFF; color: #000000;")
            for number in lineEdit.text().split(","):
                if not number.strip():
                    continue
                elif number.strip().isdigit():
                    continue
                else:
                    lineEdit.setStyleSheet(
                        "background: #FF7777; color: #FFFFFF;")
                    break

        for lineEdit in lineEdits_to_check:
            if lineEdit.styleSheet() == "background: #FF7777; color: #FFFFFF;":
                msg = "Please check all marked fields.\nNote that all" \
                    "numbers must be whole numbers and if there are multiple" \
                    "numbers in one field, then the numbers must" \
                    " be seperated by single comma."

                QMessageBox.critical(None, "Invalid inputs", msg)
                return False
        return True

    def open_thumbnail_fileBrowser(self):
        path = QFileDialog.getOpenFileName(
            self, "Select a picture")[0]
        if path:
            self.thumbnail_lineEdit.setText(path)

    def copy_thumbnail(self, img_path):
        assets_path = os.path.join(self.settings.value(
            "qwc2-themes-manager/qwc2_directory"),
            "assets/img/mapthumbs/" + os.path.basename(img_path))
        try:
            copyfile(img_path, assets_path)
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "The thumbnail couldn't be copied to the thumbnail directory."
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Couln't copy thumbnail picture "
                "to the path: %s." % img_path,
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        except FileNotFoundError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: File not found",
                "Please check the thumbnail path.")
            QgsMessageLog.logMessage(
                "FileNotFoundError: The path: %s "
                "does not exist." % img_path,
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        return True
