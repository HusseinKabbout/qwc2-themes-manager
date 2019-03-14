# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ThemesManager
                                 A QGIS plugin
 This plugin helps users manage QWC2 Themes and deploys the edited themes
 configuration to the QWC2 installation directory.
                             -------------------
        begin                : 2019-03-13
        copyright            : (C) 2019 by Hussein Kabbout
        email                : hussein.kabbout@sourcepole.ch
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    from .themes_manager import ThemesManager
    return ThemesManager(iface)
