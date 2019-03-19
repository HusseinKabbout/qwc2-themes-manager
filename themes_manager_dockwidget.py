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
import subprocess
import webbrowser
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *

from qgis.core import *

from .theme_settings_dialog import ThemeSettingsDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'themes_manager.ui'))


class ThemeManagerDockWidget(QDockWidget, FORM_CLASS):

    def __init__(self, iface, parent=None):
        super(ThemeManagerDockWidget, self).__init__(parent)

        self.setupUi(self)
        self.settings = QSettings()
        self.iface = iface

        self.buttonBox.button(QDialogButtonBox.Retry).setText("Refresh")

        QgsProject.instance().readProject.connect(self.enable_publish_button)
        self.themes_listWidget.itemClicked.connect(self.enable_buttons)
        self.qwc2Dir_button.clicked.connect(
            lambda: self.open_file_browser(self.qwc2Dir_lineEdit))
        self.qwc2Dir_lineEdit.textChanged.connect(
            lambda: self.check_path(self.qwc2Dir_lineEdit))
        self.projectsDir_button.clicked.connect(
            lambda: self.open_file_browser(self.projectsDir_lineEdit))
        self.projectsDir_lineEdit.textChanged.connect(
            lambda: self.check_path(self.projectsDir_lineEdit))
        self.qwc2Url_lineEdit.editingFinished.connect(self.enable_qwc2_button)
        self.buttonBox.button(QDialogButtonBox.Save).clicked.connect(
            self.save_themes_config)
        self.buttonBox.button(QDialogButtonBox.Save).clicked.connect(
            self.save_paths)
        self.buttonBox.button(QDialogButtonBox.Retry).clicked.connect(
            self.load_themes_config)
        self.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(
            self.reset_themes_config)
        self.defaultScales_lineEdit.textChanged.connect(
            lambda: self.check_numbers(self.defaultScales_lineEdit))
        self.defaultPrintScales_lineEdit.textChanged.connect(
            lambda: self.check_numbers(self.defaultPrintScales_lineEdit))
        self.defaultPrintResolutions_lineEdit.textChanged.connect(
            lambda: self.check_numbers(self.defaultPrintResolutions_lineEdit))
        self.addTheme_button.clicked.connect(
            lambda: self.create_or_edit_theme("create"))
        self.editTheme_button.clicked.connect(
            lambda: self.create_or_edit_theme("edit"))
        self.deleteTheme_button.clicked.connect(self.delete_theme)
        self.openProject_button.clicked.connect(self.open_project)
        self.showQWC2_button.clicked.connect(self.open_qwc2)

        self.set_qwc2_dir_path(self.settings.value(
            "qwc2-themes-manager/qwc2_directory"))
        self.set_projects_dir_path(self.settings.value(
            "qwc2-themes-manager/project_directory"))
        self.set_qwc2_url(self.settings.value("qwc2-themes-manager/qwc2_url"))
        self.tabWidget.currentChanged.connect(self.save_paths)

        self.load_themes_config()
        self.activate_themes_tab()

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
            self.load_themes_config()
        else:
            self.tabWidget.setTabEnabled(0, False)

    def set_qwc2_dir_path(self, path):
        self.qwc2Dir_lineEdit.setText(path)

    def set_projects_dir_path(self, path):
        self.projectsDir_lineEdit.setText(path)

    def set_qwc2_url(self, url):
        self.qwc2Url_lineEdit.setText(url)

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
                               self.qwc2Url_lineEdit.text())

    def read_themes_config(self, path):
        try:
            themes_config = open(path, "r", encoding="utf-8")
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
            return self.create_new_themes_config(path)

        return themes_config

    def check_config(self):
        path = os.path.join(self.qwc2Dir_lineEdit.text(), "themesConfig.json")
        themes_config = self.read_themes_config(path)
        themes_dict = None
        if not themes_config:
            return

        try:
            themes_dict = json.load(themes_config)
        except Exception:
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
                themes_config = self.create_new_themes_config(path)
                if themes_config:
                    themes_dict = json.load(themes_config)

        themes_config.close()
        return themes_dict

    def load_themes_config(self):
        themes_dict = self.check_config()
        if themes_dict is None:
            return
        for child in self.themes_tab.children():
            child.setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Reset).setEnabled(True)
        self.reset_ui()

        if "defaultScales" in themes_dict:
            self.defaultScales_lineEdit.setText(
                ",".join(str(num) for num in themes_dict["defaultScales"]))

        if "defaultPrintScales" in themes_dict:
            self.defaultPrintScales_lineEdit.setText(
                ",".join(
                    str(num) for num in themes_dict["defaultPrintScales"]))

        if "defaultPrintResolutions" in themes_dict:
            self.defaultPrintResolutions_lineEdit.setText(
                ",".join(str(num) for num in themes_dict[
                    "defaultPrintResolutions"]))

        if "themes" in themes_dict.keys() and "items" in themes_dict[
                "themes"].keys():
            self.fill_listView(themes_dict["themes"]["items"])
            for theme in themes_dict["themes"]["items"]:
                if "default" in theme.keys():
                    if "title" in theme.keys():
                        self.defaultTheme_comboBox.setCurrentText(
                            theme["title"])
                        break
                    elif "url" in theme.keys():
                        title = os.path.basename(theme["url"])
                        self.defaultTheme_comboBox.setCurrentText(title)
                        break
        self.old_themes_dict = themes_dict

    def deactivate_themes_tab(self):
        for child in self.themes_tab.children():
            if isinstance(child, QGridLayout):
                continue
            child.setEnabled(False)
        self.defaultScales_lineEdit.setText("")
        self.buttonBox.setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Reset).setEnabled(False)

    def create_new_themes_config(self, path):
        try:
            themes_dict = open(path, 'w')
            themes_dict.write("{}")
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Cannot override themes configuration file"
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Cannot override file: %s." % path,
                "QWC2 Theme Manager", Qgis.Critical)
            return
        return open(path, 'r')

    def fill_listView(self, themes):
        self.editTheme_button.setEnabled(False)
        self.deleteTheme_button.setEnabled(False)
        self.openProject_button.setEnabled(False)
        self.showQWC2_button.setEnabled(False)
        for index, theme in enumerate(themes):
            if "title" in theme.keys():
                self.defaultTheme_comboBox.addItem(theme["title"])
                list_item = QListWidgetItem(theme["title"])
                theme["index"] = index
                list_item.setData(Qt.UserRole, theme)
                self.themes_listWidget.addItem(list_item)
            else:
                if "url" not in theme.keys():
                    continue
                title = os.path.basename(theme["url"])
                self.defaultTheme_comboBox.addItem(title)
                list_item = QListWidgetItem(title)
                theme["index"] = index
                list_item.setData(Qt.UserRole, theme)
                self.themes_listWidget.addItem(list_item)
        self.themes_listWidget.clearSelection()

    def reset_themes_config(self):
        self.reset_ui()
        if "defaultScales" in self.old_themes_dict:
            self.defaultScales_lineEdit.setText(
                ",".join(
                    str(num) for num in self.old_themes_dict["defaultScales"]))

        if "defaultPrintScales" in self.old_themes_dict:
            self.defaultPrintScales_lineEdit.setText(
                ",".join(
                    str(num) for num in self.old_themes_dict[
                        "defaultPrintScales"]))

        if "defaultPrintResolutions" in self.old_themes_dict:
            self.defaultPrintResolutions_lineEdit.setText(
                ",".join(
                    str(num) for num in self.old_themes_dict[
                        "defaultPrintResolutions"]))

        self.defaultTheme_comboBox.clear()
        if "themes" in self.old_themes_dict.keys() and \
           "items" in self.old_themes_dict[
                "themes"].keys():
            self.fill_listView(self.old_themes_dict["themes"]["items"])
            for theme in self.old_themes_dict["themes"]["items"]:
                if "default" in theme.keys():
                    if "title" in theme.keys():
                        self.defaultTheme_comboBox.setCurrentText(
                            theme["title"])
                        break
                    elif "url" in theme.keys():
                        title = os.path.basename(theme["url"])
                        self.defaultTheme_comboBox.setCurrentText(title)
                        break

    def save_themes_config(self):
        if not self.checks_before_saving():
            QMessageBox.critical(None, "QWC2 Theme Manager",
                                 "Some fields have incorrect inputs.\n"
                                 "Please check all fields!")
            return
        config_path = os.path.join(
            self.qwc2Dir_lineEdit.text(), "themesConfig.json")
        themes_config = self.read_themes_config(config_path)
        themes_dict = json.load(themes_config)
        themes_config.close()
        if self.defaultScales_lineEdit.text():
            themes_dict["defaultScales"] = [
                int(num.strip()) for num in
                self.defaultScales_lineEdit.text().split(",")]
        else:
            themes_dict["defaultScales"] = [1000000, 500000, 250000, 100000,
                                            50000, 25000, 10000, 5000, 2500,
                                            1000, 500]
        if self.defaultPrintScales_lineEdit.text():
            themes_dict["defaultPrintScales"] = [
                int(num.strip()) for num in
                self.defaultPrintScales_lineEdit.text().split(",")]
        else:
            if "defaultPrintScales" in themes_dict.keys():
                themes_dict.pop("defaultPrintScales")
        if self.defaultPrintResolutions_lineEdit.text():
            themes_dict["defaultPrintResolutions"] = [
                int(num.strip()) for num in
                self.defaultPrintResolutions_lineEdit.text().split(",")]
        else:
            if "defaultPrintResolutions" in themes_dict.keys():
                themes_dict.pop("defaultPrintResolutions")
        if "themes" in themes_dict.keys() and "items" in themes_dict[
                "themes"].keys():
            for theme in themes_dict["themes"]["items"]:
                if "default" in theme.keys():
                    theme.pop("default")
                if "title" in theme.keys():
                    if self.defaultTheme_comboBox.currentText() == theme[
                            "title"]:
                        theme["default"] = True
                        continue
                elif "url" in theme.keys():
                    title = os.path.basename(theme["url"])
                    if self.defaultTheme_comboBox.currentText() == title:
                        theme["default"] = True
                        continue
        try:
            themes_config = open(config_path, 'w')
            themes_config.write(json.dumps(themes_dict, indent=2,
                                           sort_keys=True))
            themes_config.close()
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Cannot create/override themes configuration file"
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Cannot "
                "create/override file: %s." % config_path,
                "QWC2 Theme Manager", Qgis.Critical)
        self.gen_complete_config()
        self.load_themes_config()

    def reset_ui(self):
        self.defaultScales_lineEdit.setText(
            "1000000,500000,250000,100000,50000,"
            "25000,10000,5000,2500,1000,500")
        self.defaultPrintScales_lineEdit.setText("")
        self.defaultPrintResolutions_lineEdit.setText("")
        self.defaultTheme_comboBox.clear()
        self.themes_listWidget.clear()

    def check_numbers(self, lineEdit):
        numbers_list = lineEdit.text()
        if not numbers_list:
            lineEdit.setStyleSheet("background: #FFFFFF; color: #000000;")
            return
        for number in numbers_list.split(","):
            if number.isdigit():
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

    def create_or_edit_theme(self, method):
        self.save_paths()
        if method == "create":
            settings_dlg = self.theme_settings_dialog = ThemeSettingsDialog(
                self.iface.mainWindow(), method, self.iface,
                self.defaultTheme_comboBox.count())
            if settings_dlg.exec_() == 1:
                return
            self.load_themes_config()
            self.save_themes_config()
        else:
            theme = self.themes_listWidget.selectedItems()
            if not theme:
                QMessageBox.warning(None, "QWC2 Theme Manager",
                                    "No theme selected.")
                return
            settings_dlg = self.theme_settings_dialog = ThemeSettingsDialog(
                self.iface.mainWindow(), method, self.iface,
                self.defaultTheme_comboBox.count(), theme[0].data(Qt.UserRole))
            if settings_dlg.exec_() == 1:
                return
            self.load_themes_config()
            self.save_themes_config()
        self.enable_publish_button()
        self.gen_complete_config()

    def delete_theme(self):
        theme = self.themes_listWidget.selectedItems()
        if not theme:
            QMessageBox.warning(None, "QWC2 Theme Manager",
                                "No theme selected.")
            return

        res = QMessageBox.question(
            None, "QWC2 Theme Manager",
            "Do you really want to delete the selected theme?")
        if res == QMessageBox.No:
            return

        config_path = os.path.join(self.settings.value(
            "qwc2-themes-manager/qwc2_directory"), "themesConfig.json")
        theme = theme[0].data(Qt.UserRole)
        index = theme.pop("index")

        try:
            themes_config = open(config_path, "r", encoding="utf-8")
            themes_dict = json.load(themes_config)
            removed_theme = themes_dict["themes"]["items"].pop(index)
            themes_config.close()
            themes_config = open(config_path, "w", encoding="utf-8")
            themes_config.write(json.dumps(themes_dict, indent=2,
                                           sort_keys=True))
            themes_config.close()
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Cannot delete the selected theme"
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Cannot open/override "
                "file: %s." % config_path,
                "QWC2 Theme Manager", Qgis.Critical)
            return

        self.load_themes_config()
        self.enable_publish_button()
        self.gen_complete_config()

        res = QMessageBox.question(
            None, "QWC2 Theme Manager",
            "Do you also want to delete the QGIS project of "
            "the deleted Theme?")
        if res == QMessageBox.No:
            return

        try:
            projects_dir_path = os.path.join(self.settings.value(
                "qwc2-themes-manager/project_directory"),
                os.path.basename(removed_theme["url"]))
            os.remove(projects_dir_path + ".qgs")
        except PermissionError:
            QMessageBox.critical(
                None, "QWC2 Theme Manager: Permission Error",
                "Cannot delete the project"
                "\nInsufficient permissions!")
            QgsMessageLog.logMessage(
                "Permission Error: Cannot Delete the project with "
                "the path: %s." % projects_dir_path,
                "QWC2 Theme Manager", Qgis.Critical)
            return
        except FileNotFoundError:
            QgsMessageLog.logMessage(
                "Delete project Error: The path: %s doesn't "
                "exist." % projects_dir_path,
                "QWC2 Theme Manager", Qgis.Warning)

    def enable_publish_button(self):
        if not QgsProject.instance().baseName():
            return
        self.addTheme_button.setEnabled(True)
        for index in range(self.themes_listWidget.count()):
            if os.path.basename(
                self.themes_listWidget.item(
                    index).data(Qt.UserRole)[
                        "url"]) == QgsProject.instance().baseName():
                self.addTheme_button.setEnabled(False)

    def gen_complete_config(self):
        if self.themes_listWidget.count() == 0:
            return
        os.chdir(self.qwc2Dir_lineEdit.text())
        script_path = os.path.join(os.path.dirname(__file__),
                                   "themesConfig.py")
        output = subprocess.Popen(['python3', script_path],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)

        stdout, stderr = output.communicate()
        if stderr.decode("utf-8"):
            QMessageBox.warning(
                None, "QWC2 Theme Manager",
                "Couldn't generate themes.json\n"
                "Please run the script: themesConfig.py manually to generate"
                "the themes.json file.")
            QgsMessageLog.logMessage(
                "Python execution error: \n%s" % stderr.decode("utf-8"),
                "QWC2 Theme Manager", Qgis.Critical)

    def enable_buttons(self):
        self.editTheme_button.setEnabled(True)
        self.deleteTheme_button.setEnabled(True)
        self.openProject_button.setEnabled(True)
        self.enable_qwc2_button()

    def enable_qwc2_button(self):
        if self.qwc2Url_lineEdit.text() and \
                self.themes_listWidget.selectedItems():
            self.showQWC2_button.setEnabled(True)
        else:
            self.showQWC2_button.setEnabled(False)

    def open_project(self):
        theme = self.themes_listWidget.selectedItems()
        if not theme:
            QMessageBox.warning(None, "QWC2 Theme Manager",
                                "No theme selected.")
            return
        project_name = os.path.basename(
            theme[0].data(Qt.UserRole)["url"]) + ".qgs"
        projects_dir_path = os.path.join(
            self.projectsDir_lineEdit.text(), project_name)
        if os.path.exists(projects_dir_path):
            opened = QgsProject.instance().read(projects_dir_path)
            if not opened:
                QMessageBox.critical(
                    None, "QWC2 Theme Manager",
                    "Couldn't open the project of the selected theme.\n"
                    "Check if you have the needed permissions to "
                    "open the project.")
        else:
            QMessageBox.critical(
                None, "QWC2 Theme Manager",
                "Couldn't find the project of the selected theme.")
            QgsMessageLog.logMessage(
                "Project Error: Couldn't open project with the"
                " path: %s." % projects_dir_path,
                "QWC2 Theme Manager", Qgis.Warning)

    def open_qwc2(self):
        theme = self.themes_listWidget.selectedItems()[0].data(Qt.UserRole)
        url = os.path.join(
            self.qwc2Url_lineEdit.text(), "?t=") + os.path.basename(
                theme["url"])
        if not url.startswith("http"):
            url = "http://" + url
        webbrowser.open(url)
