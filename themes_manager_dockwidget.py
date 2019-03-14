# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ThemeManagerDockWidget
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
import json
from urllib.request import urlopen
import xml.etree.ElementTree as ET
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (QDockWidget, QFileDialog, QMessageBox, QGridLayout,
                                 QDialogButtonBox, QListWidgetItem)
from qgis.PyQt.QtCore import QSettings

from qgis.core import QgsMessageLog, Qgis


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'themes_manager.ui'))


class ThemeManagerDockWidget(QDockWidget, FORM_CLASS):

    def __init__(self, iface, parent=None):
        super(ThemeManagerDockWidget, self).__init__(parent)

        self.setupUi(self)
        self.settings = QSettings()
        self.iface = iface

        self.buttonBox.button(QDialogButtonBox.Retry).setText("Refresh")

        self.qwc2Dir_button.clicked.connect(
            lambda: self.open_file_browser(self.qwc2Dir_lineEdit))
        self.qwc2Dir_lineEdit.textChanged.connect(
            lambda: self.check_path(self.qwc2Dir_lineEdit))
        self.projectsDir_button.clicked.connect(
            lambda: self.open_file_browser(self.projectsDir_lineEdit))
        self.projectsDir_lineEdit.textChanged.connect(
            lambda: self.check_path(self.projectsDir_lineEdit))
        self.buttonBox.button(QDialogButtonBox.Save).clicked.connect(
            self.save_themes_config)
        self.buttonBox.button(QDialogButtonBox.Retry).clicked.connect(
            self.load_themes_config)
        self.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(
            self.reset_themes_config)
        self.defaultScales_lineEdit.textChanged.connect(
            lambda: self.check_list(self.defaultScales_lineEdit))
        self.defaultPrintScales_lineEdit.textChanged.connect(
            lambda: self.check_list(self.defaultPrintScales_lineEdit))
        self.defaultPrintResolutions_lineEdit.textChanged.connect(
            lambda: self.check_list(self.defaultPrintResolutions_lineEdit))

        self.set_qwc2_dir_path(self.settings.value(
            "qwc2-themes-manager/qwc2_directory"))
        self.set_projects_dir_path(self.settings.value(
            "qwc2-themes-manager/project_directory"))
        self.set_qwc2_url(self.settings.value("qwc2-themes-manager/qwc2_url"))

        self.load_themes_config()

    def check_path(self, lineEdit):
        if os.path.isdir(lineEdit.text()):
            lineEdit.setStyleSheet("background: #FFFFFF; color: #000000;")
        else:
            lineEdit.setStyleSheet("background: #FF7777; color: #FFFFFF;")

        self.activate_themes_tab()

    def activate_themes_tab(self):
        if os.path.isdir(self.qwc2Dir_lineEdit.text()) and os.path.isdir(
                self.projectsDir_lineEdit.text()):
            self.tabWidget.setTabEnabled(0, True)
        else:
            self.tabWidget.setTabEnabled(0, False)

    def set_qwc2_dir_path(self, path):
        self.qwc2Dir_lineEdit.setText(path)

    def set_projects_dir_path(self, path):
        self.projectsDir_lineEdit.setText(path)

    def set_qwc2_url(self, url):
        self.QWC2Url_lineEdit.setText(url)

    def open_file_browser(self, lineEdit):
        path = QFileDialog.getExistingDirectory(
            self, "Select a directory",
            options=QFileDialog.ShowDirsOnly)
        if path:
            lineEdit.setText(path)

    def save_paths(self):
        self.settings.setValue("qwc2-themes-manager/qwc2_directory",
                               self.qwc2Dir_lineEdit.text())
        self.settings.setValue("qwc2-themes-manager/project_directory",
                               self.projectsDir_lineEdit.text())
        self.settings.setValue("qwc2-themes-manager/qwc2_url",
                               self.QWC2Url_lineEdit.text())

    def read_themes_config(self, path):
        try:
            themes_config = open(path, encoding="utf-8")
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Cannot open themes configuration file"
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Cannot open file: %s." % path,
                "QWC2 Theme Manager", Qgis.Critical)
            self.deactivate_themes_tab()
            return None
        except FileNotFoundError:
            return self.create_themes_config(path)

        return themes_config

    def check_config(self):
        path = os.path.join(self.qwc2Dir_lineEdit.text(), "themesConfig.json")
        themes_config = self.read_themes_config(path)
        if not themes_config:
            return

        try:
            config = json.load(themes_config)
        except:
            QgsMessageLog.logMessage(
                "Corrupt JSON file: The JSON module couldn't read the "
                "themesConfig.json file.",
                "QWC2 Theme Manager", Qgis.Critical)
            res = QMessageBox.question(
                None, "QWC2 Theme Manager",
                "It seems that your themesConfig.json file is corrupt.\n"
                "Would you like to create a new themesConfig.json file"
                " and override the existing one?")
            if res == QMessageBox.No:
                self.deactivate_themes_tab()
                return
            else:
                themes_config = self.create_themes_config(path)
                if themes_config:
                    config = json.load(themes_config)

        themes_config.close()
        return config

    def load_themes_config(self):
        config = self.check_config()
        if not config:
            return
        self.reset_ui()

        if "defaultScales" in config:
            self.defaultScales_lineEdit.setText(
                ",".join(str(num) for num in config["defaultScales"]))

        if "defaultPrintScales" in config:
            self.defaultPrintScales_lineEdit.setText(
                ",".join(str(num) for num in config["defaultPrintScales"]))

        if "defaultPrintResolutions" in config:
            self.defaultPrintResolutions_lineEdit.setText(
                ",".join(str(num) for num in config["defaultPrintScales"]))

        self.fill_listView(config["themes"]["items"])
        for item in config["themes"]["items"]:
            if "default" in item.keys():
                if "title" in item.keys():
                    self.defaultTheme_comboBox.setCurrentText(item["title"])
                    break
                else:
                    title = self.get_title_from_wms(item["url"])
                    self.defaultTheme_comboBox.setCurrentText(title)
                    break
        self.old_config = config

    def deactivate_themes_tab(self):
        for child in self.themes_tab.children():
            if isinstance(child, QGridLayout):
                continue
            child.setEnabled(False)
        self.defaultScales_lineEdit.setText("")
        self.buttonBox.setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Reset).setEnabled(False)

    def create_themes_config(self, path):
        themes_config = open(path, 'w')
        themes_config.write("{}")
        return themes_config

    def fill_listView(self, themes):
        for theme in themes:
            if "title" in theme.keys():
                self.defaultTheme_comboBox.addItem(theme["title"])
                item = QListWidgetItem(theme["title"])
                self.themes_listWidget.addItem(item)
            else:
                title = self.get_title_from_wms(theme["url"])
                self.defaultTheme_comboBox.addItem(title)
                item = QListWidgetItem(title)
                self.themes_listWidget.addItem(item)

    def reset_themes_config(self):
        self.reset_ui()
        if "defaultScales" in self.old_config:
            self.defaultScales_lineEdit.setText(
                ",".join(
                    str(num) for num in self.old_config["defaultScales"]))

        if "defaultPrintScales" in self.old_config:
            self.defaultPrintScales_lineEdit.setText(
                ",".join(
                    str(num) for num in self.old_config["defaultPrintScales"]))

        if "defaultPrintResolutions" in self.old_config:
            self.defaultPrintResolutions_lineEdit.setText(
                ",".join(
                    str(num) for num in self.old_config["defaultPrintScales"]))

        self.defaultTheme_comboBox.clear()
        self.fill_listView(self.old_config["themes"]["items"])
        for item in self.old_config["themes"]["items"]:
            if "default" in item.keys():
                if "title" in item.keys():
                    self.defaultTheme_comboBox.setCurrentText(item["title"])
                    break
                else:
                    title = self.get_title_from_wms(item["url"])
                    self.defaultTheme_comboBox.setCurrentText(title)
                    break

    def save_themes_config(self):
        if not self.checks_before_saving():
            QMessageBox.critical(None, "QWC2 Theme Manager",
                                 "Some fields have incorrect inputs.\n"
                                 "Please check all fields!")
            return
        path = os.path.join(self.qwc2Dir_lineEdit.text(), "themesConfig.json")
        themes_config = self.read_themes_config(path)
        config = json.load(themes_config)
        themes_config.close()
        if self.defaultScales_lineEdit.text():
            config["defaultScales"] = [
                int(num.strip()) for num in self.defaultScales_lineEdit.text().split(",")]
        else:
            config["defaultScales"] = [1000000, 500000, 250000, 100000,
                                       50000, 25000, 10000, 5000, 2500, 1000,
                                       500]
        if self.defaultPrintScales_lineEdit.text():
            config["defaultPrintScales"] = [
                int(num.strip()) for num in self.defaultPrintScales_lineEdit.text().split(",")]
        else:
            if "defaultPrintScales" in config.keys():
                config.pop("defaultPrintScales")
        if self.defaultPrintResolutions_lineEdit.text():
            config["defaultPrintResolutions"] = [
                int(num.strip()) for num in self.defaultPrintResolutions_lineEdit.text().split(",")]
        else:
            if "defaultPrintResolutions" in config.keys():
                config.pop("defaultPrintResolutions")

        for item in config["themes"]["items"]:
            if "default" in item.keys():
                item.pop("default")
                if "title" in item.keys():
                    if self.defaultTheme_comboBox.currentText() == item["title"]:
                        item["default"] = True
                        continue
                else:
                    title = self.get_title_from_wms(item["url"])
                    if self.defaultTheme_comboBox.currentText() == title:
                        item["default"] = True
                        continue

        themes_config = open(path, 'w')
        themes_config.write(json.dumps(config))
        themes_config.close()

    def get_title_from_wms(self, url):
        url = url + "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetProjectSettings"
        wms_xml = urlopen(url).read()
        root = ET.fromstring(wms_xml)
        for child in root:
            if "Service" in child.tag:
                for subchild in child.getchildren():
                    if "Title" in subchild.tag:
                        return subchild.text

    def reset_ui(self):
        self.defaultScales_lineEdit.setText(
            "1000000,500000,250000,100000,50000,25000,10000,5000,2500,1000,500")
        self.defaultPrintScales_lineEdit.setText("")
        self.defaultPrintResolutions_lineEdit.setText("")
        self.defaultTheme_comboBox.clear()
        self.themes_listWidget.clear()

    def check_list(self, lineEdit):
        numbers_list = lineEdit.text()
        if not numbers_list:
            lineEdit.setStyleSheet("background: #FFFFFF; color: #000000;")
            return
        for number in numbers_list.split(","):
            if not number:
                continue
            elif number.isdigit():
                continue
            else:
                lineEdit.setStyleSheet("background: #FF7777; color: #FFFFFF;")
                return
        lineEdit.setStyleSheet("background: #FFFFFF; color: #000000;")

    def checks_before_saving(self):
        notok_style = "background: #FF7777; color: #FFFFFF;"
        if self.defaultScales_lineEdit.styleSheet() == notok_style:
            return False
        elif self.defaultPrintScales_lineEdit.styleSheet() == notok_style:
            return False
        elif self.defaultPrintResolutions_lineEdit.styleSheet() == notok_style:
            return False
        return True
