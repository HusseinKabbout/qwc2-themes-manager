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
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from shutil import copyfile
from qgis.core import *
from qgis.gui import *
from qgis.PyQt import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'theme_settings.ui'))


class ThemeSettingsDialog(QDialog, FORM_CLASS):

    def __init__(self, parent, method, iface, default_true, theme=None):
        super(ThemeSettingsDialog, self).__init__(parent)
        self.setupUi(self)

        self.method = method
        self.iface = iface
        self.default_true = default_true
        self.settings = QSettings()
        self.theme = theme
        self.index = None
        if self.theme:
            self.index = self.theme.pop("index")
        if method == "create":
            self.buttonBox.button(QDialogButtonBox.Apply).setText("Create")
        else:
            self.buttonBox.button(QDialogButtonBox.Apply).setText("Save")
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            self.save_theme)
        self.thumbnail_button.clicked.connect(self.open_thumbnail_fileBrowser)
        self.thumbnail_button.setIcon(QIcon(
            ":/images/themes/default/mActionFileOpen.svg"))

        self.prepate_dlg()

    def prepate_dlg(self):
        if self.method == "create":
            self.title_lineEdit.setText(QgsProject.instance().baseName())
            self.mapCrs_widget.setCrs(QgsProject.instance().crs())
            self.extent_lineEdit.setText(
                self.iface.mapCanvas().extent().toString(0).replace(
                    " : ", ","))
        else:
            for child in self.children():
                child_name = child.objectName().split("_")[0]
                if child_name not in self.theme.keys():
                    continue
                if child_name == "extent" or child_name == "scales" or \
                        child_name == "printScales" or \
                        child_name == "printResolutions" or \
                        child_name == "searchProviders":
                    child.setText(",".join(
                        str(item) for item in self.theme[child_name]))
                    continue
                elif isinstance(child, QLineEdit):
                    child.setText(self.theme[child_name])
                    continue
                elif isinstance(child, QCheckBox):
                    child.setChecked(self.theme[child_name])
                    continue
                elif isinstance(child, QgsProjectionSelectionWidget):
                    child.setCrs(QgsCoordinateReferenceSystem(
                        self.theme[child_name]))
                    continue
                elif isinstance(child, QComboBox):
                    child.setCurrentText(self.theme[child_name])
                    continue

    def save_theme(self):
        if self.save_project() is not True:
            return
        if not self.check_inputs():
            return
        if not self.url_lineEdit.text():
            QMessageBox.warning(None, "Missing parameter",
                                "WMS url of the project is missing!")
            return
        new_theme = {}
        for child in self.children():
            child_name = child.objectName().split("_")[0]
            if child_name == "scales" or \
                    child_name == "printScales" or \
                    child_name == "printResolutions":
                numbers = []
                for num in child.text().split(","):
                    if num:
                        numbers.append(int(num.strip()))
                if numbers:
                    new_theme[child_name] = numbers
                continue
            elif isinstance(child, QCheckBox):
                if child.isChecked():
                    new_theme[child_name] = True
        wms_url = self.url_lineEdit.text()
        if not wms_url.startswith("http"):
            wms_url = "http://" + wms_url
        new_theme["url"] = wms_url
        new_theme["title"] = self.title_lineEdit.text() \
            if self.title_lineEdit.text() else os.path.basename(
                self.url_lineEdit.text())
        if self.thumbnail_lineEdit.text() and self.copy_thumbnail(
                self.thumbnail_lineEdit.text()):
            new_theme["thumbnail"] = os.path.basename(
                self.thumbnail_lineEdit.text())
        elif self.thumbnail_lineEdit.text():
            return
        if self.attribution_lineEdit.text():
            new_theme["attribution"] = self.attribution_lineEdit.text()
            new_theme["attributionUrl"] = self.attributionUrl_lineEdit.text()
        new_theme[
            "searchProviders"] = self.searchProviders_lineEdit.text().split(
            ",") if self.searchProviders_lineEdit.text() else ["coordinates"]
        new_theme["mapCrs"] = self.mapCrs_widget.crs().authid()
        new_theme["format"] = self.format_comboBox.currentText()

        numbers = []
        for num in self.extent_lineEdit.text().split(","):
            if num:
                numbers.append(int(num.strip()))
        if numbers:
            new_theme["extent"] = numbers[:4]

        if self.default_true == 0:
            new_theme["default"] = True
        path = os.path.join(self.settings.value(
            "qwc2-themes-manager/qwc2_directory"), "themesConfig.json")
        try:
            themes_config = open(path, "r", encoding="utf-8")
            themes_dict = json.load(themes_config)
            if "themes" not in themes_dict.keys() or \
                    "items" not in themes_dict["themes"].keys():
                themes_dict["themes"] = {"items": []}
            if self.index is not None:
                old_theme = themes_dict["themes"]["items"].pop(self.index)
                if "default" in old_theme.keys():
                    new_theme["default"] = old_theme["default"]
            themes_dict["themes"]["items"].append(new_theme)
            themes_config.close()
            themes_config = open(path, "w", encoding="utf-8")
            themes_config.write(json.dumps(themes_dict, indent=2,
                                           sort_keys=True))
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
                              self.printResolutions_lineEdit]

        for lineEdit in lineEdits_to_check:
            lineEdit.setStyleSheet("background: #FFFFFF; color: #000000;")
            if lineEdit.text():
                for number in lineEdit.text().split(","):
                    if number.isdigit():
                        continue
                    else:
                        lineEdit.setStyleSheet(
                            "background: #FF7777; color: #FFFFFF;")
                        break

        self.extent_lineEdit.setStyleSheet(
            "background: #FFFFFF; color: #000000;")
        if self.extent_lineEdit.text():
            for number in self.extent_lineEdit.text().split(","):
                try:
                    int(number)
                except:
                    self.extent_lineEdit.setStyleSheet(
                        "background: #FF7777; color: #FFFFFF;")
                    break

        lineEdits_to_check.append(self.extent_lineEdit)
        for lineEdit in lineEdits_to_check:
            if lineEdit.styleSheet() == "background: #FF7777; color: #FFFFFF;":
                msg = "Please check all marked fields.\nNote that all " \
                    "numbers must be whole numbers and if there are multiple" \
                    " numbers in one field, then the numbers must" \
                    " be seperated by a single comma."

                QMessageBox.critical(None, "Invalid inputs", msg)
                return False
        if self.check_wms() is False:
            self.url_lineEdit.setStyleSheet(
                "background: #FF7777; color: #FFFFFF;")
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
        if os.path.exists(assets_path):
            return True
        elif not os.path.exists(os.path.join(self.settings.value(
                "qwc2-themes-manager/qwc2_directory"),
                "assets/img/mapthumbs/")):
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Thumbnail directory not found",
                "The thumbnail directory couldn't be found.\n"
                "Please check your QWC2 installation!")
            QgsMessageLog.logMessage(
                "The thumbnail directory couldn't be found.\n"
                "Please check your QWC2 installation!",
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        try:
            copyfile(img_path, assets_path)
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "The thumbnail couldn't be copied to the thumbnail directory."
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Couln't copy thumbnail picture "
                "to the path: %s." % assets_path,
                "QWC2 Theme Manager", Qgis.Critical)
            self.thumbnail_lineEdit.setStyleSheet(
                "background: #FF7777; color: #FFFFFF;")
            return False
        except FileNotFoundError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: File not found",
                "Please check the thumbnail path.")
            QgsMessageLog.logMessage(
                "FileNotFoundError: The path: %s "
                "does not exist." % img_path,
                "QWC2 Theme Manager", Qgis.Critical)
            self.thumbnail_lineEdit.setStyleSheet(
                "background: #FF7777; color: #FFFFFF;")
            return False
        return True

    def check_wms(self):
        wms_url = self.url_lineEdit.text()
        if not wms_url.startswith("http"):
            wms_url = "http://" + wms_url
        url = wms_url + \
            "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
        try:
            urlopen(url).read()
        except ValueError:
            QMessageBox.critical(None, "Invalid URL",
                                 "The given WMS URL is not valid.")
            QgsMessageLog.logMessage(
                "Invalid WMS URL: Couln't test WMS GetCapabilities "
                "on the url: %s" % url,
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        except HTTPError:
            QMessageBox.critical(None, "Invalid URL",
                                 "The given WMS URL is not valid.")
            QgsMessageLog.logMessage(
                "Invalid WMS URL: Couln't test WMS GetCapabilities "
                "on the url: %s" % url,
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        except URLError:
            QMessageBox.critical(None, "Invalid URL",
                                 "The given WMS URL is not valid.")
            QgsMessageLog.logMessage(
                "Invalid WMS URL: Couln't test WMS GetCapabilities "
                "on the url: %s" % url,
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        return True

    def save_project(self):
        project_path = QgsProject.instance().absoluteFilePath()
        projects_dir_path = os.path.join(self.settings.value(
            "qwc2-themes-manager/project_directory"),
            os.path.basename(project_path))
        if os.path.exists(projects_dir_path):
            return True
        try:
            copyfile(project_path, projects_dir_path)
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Couldn't save project in projects directory."
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Couldn't copy project to"
                " the path: %s." % projects_dir_path,
                "QWC2 Theme Manager", Qgis.Critical)
            return False
        return True
