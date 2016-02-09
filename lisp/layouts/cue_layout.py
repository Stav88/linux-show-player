# -*- coding: utf-8 -*-
#
# This file is part of Linux Show Player
#
# Copyright 2012-2016 Francesco Ceruti <ceppofrancy@gmail.com>
#
# Linux Show Player is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linux Show Player is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linux Show Player.  If not, see <http://www.gnu.org/licenses/>.

from abc import abstractmethod

from PyQt5.QtWidgets import QAction, QMenu, qApp

from lisp.core.actions_handler import MainActionsHandler
from lisp.core.signal import Signal
from lisp.cues.cue import Cue
from lisp.layouts.cue_layout_actions import ConfigureAction, \
    MultiConfigureAction
from lisp.layouts.cue_menu_registry import CueMenuRegistry
from lisp.ui.mainwindow import MainWindow
from lisp.ui.settings.cue_settings import CueSettings
from lisp.utils.util import greatest_common_superclass


class CueLayout:
    # Layout name
    NAME = 'Base'
    # Layout info (html)
    DESCRIPTION = '<p>No description</p>'

    cm_registry = CueMenuRegistry()

    def __init__(self, cue_model):
        self._cue_model = cue_model

        self.cue_executed = Signal()    # After a cue is executed
        self.focus_changed = Signal()   # After the focused cue is changed
        self.key_pressed = Signal()     # After a key is pressed

    @property
    def cue_model(self):
        """:rtype: lisp.model_view.cue_model.CueModel"""
        return self._cue_model

    @property
    @abstractmethod
    def model_adapter(self):
        """:rtype: lisp.model_view.model_adapter.ModelAdapter"""

    @abstractmethod
    def deselect_all(self):
        """Deselect all the cues"""

    @abstractmethod
    def finalize(self):
        """Destroy all the layout elements"""

    def edit_cue(self, cue):
        edit_ui = CueSettings(cue, parent=MainWindow())

        def on_apply(settings):
            action = ConfigureAction(settings, cue)
            MainActionsHandler().do_action(action)

        edit_ui.on_apply.connect(on_apply)
        edit_ui.exec_()

    def edit_selected_cues(self):
        cues = self.get_selected_cues()

        if cues:
            # Use the greatest common superclass between the selected cues
            edit_ui = CueSettings(cue_class=greatest_common_superclass(cues))

            def on_apply(settings):
                action = MultiConfigureAction(settings, cues)
                MainActionsHandler().do_action(action)

            edit_ui.on_apply.connect(on_apply)
            edit_ui.exec_()

    @abstractmethod
    def get_context_cue(self):
        """Return the last cue in the context-menu scope, or None"""
        return None

    @abstractmethod
    def get_selected_cues(self, cue_class=Cue):
        """Return an "ordered" list of all selected cues"""
        return []

    @abstractmethod
    def invert_selection(self):
        """Invert selection"""

    @abstractmethod
    def select_all(self):
        """Select all the cues"""

    def show_context_menu(self, position):
        menu = QMenu(self)

        cue_class = self.get_context_cue().__class__
        for item in self.cm_registry.filter(cue_class):
            if isinstance(item, QAction):
                menu.addAction(item)
            elif isinstance(item, QMenu):
                menu.addMenu(item)

        menu.move(position)
        menu.show()

        # Adjust the menu position
        desktop = qApp.desktop().availableGeometry()
        menu_rect = menu.geometry()

        if menu_rect.bottom() > desktop.bottom():
            menu.move(menu.x(), menu.y() - menu.height())
        if menu_rect.right() > desktop.right():
            menu.move(menu.x() - menu.width(), menu.y())
