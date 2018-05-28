# -*- coding: utf-8 -*-
#
# This file is part of Linux Show Player
#
# Copyright 2012-2017 Francesco Ceruti <ceppofrancy@gmail.com>
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

from PyQt5.QtCore import Qt, QT_TRANSLATE_NOOP
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction

from lisp.core.configuration import DummyConfiguration
from lisp.core.signal import Connection
from lisp.cues.cue import Cue, CueAction
from lisp.cues.cue_memento_model import CueMementoAdapter
from lisp.layout.cue_layout import CueLayout
from lisp.layout.cue_menu import SimpleMenuAction, MENU_PRIORITY_CUE, MenuActionsGroup
from lisp.plugins.list_layout.list_view import CueListView
from lisp.plugins.list_layout.models import CueListModel, RunningCueModel
from lisp.plugins.list_layout.view import ListLayoutView
from lisp.ui.ui_utils import translate


class ListLayout(CueLayout):
    NAME = 'List Layout'
    DESCRIPTION = QT_TRANSLATE_NOOP(
        'LayoutDescription', 'Organize the cues in a list')
    DETAILS = [
        QT_TRANSLATE_NOOP(
            'LayoutDetails', 'SHIFT + Space or Double-Click to edit a cue'),
        QT_TRANSLATE_NOOP(
            'LayoutDetails', 'To copy cues drag them while pressing CTRL'),
        QT_TRANSLATE_NOOP(
            'LayoutDetails', 'To move cues drag them')
    ]
    Config = DummyConfiguration()

    def __init__(self, application):
        super().__init__(application)
        self._list_model = CueListModel(self.cue_model)
        self._list_model.item_added.connect(self.__cue_added)
        self._memento_model = CueMementoAdapter(self._list_model)
        self._running_model = RunningCueModel(self.cue_model)

        self._auto_continue = ListLayout.Config['autoContinue']
        self._go_key_sequence = QKeySequence(
            ListLayout.Config['goKey'], QKeySequence.NativeText)

        self._view = ListLayoutView(self._list_model, self._running_model)
        # GO button
        self._view.goButton.clicked.connect(self.__go_slot)
        # Global actions
        self._view.controlButtons.stopButton.clicked.connect(self.stop_all)
        self._view.controlButtons.pauseButton.clicked.connect(self.pause_all)
        self._view.controlButtons.fadeInButton.clicked.connect(self.fadein_all)
        self._view.controlButtons.fadeOutButton.clicked.connect(self.fadeout_all)
        self._view.controlButtons.resumeButton.clicked.connect(self.resume_all)
        self._view.controlButtons.interruptButton.clicked.connect(self.interrupt_all)
        # Cue list
        self._view.listView.itemDoubleClicked.connect(self._double_clicked)
        self._view.listView.contextMenuInvoked.connect(self._context_invoked)
        self._view.listView.keyPressed.connect(self._key_pressed)

        # TODO: session values
        self._set_running_visible(ListLayout.Config['show.playingCues'])
        self._set_dbmeters_visible(ListLayout.Config['show.dBMeters'])
        self._set_seeksliders_visible(ListLayout.Config['show.seekSliders'])
        self._set_accurate_time(ListLayout.Config['show.accurateTime'])
        self._set_selection_mode(False)

        # Layout menu
        menuLayout = self.app.window.menuLayout

        self.showPlayingAction = QAction(parent=menuLayout)
        self.showPlayingAction.setCheckable(True)
        self.showPlayingAction.setChecked(self._show_playing)
        self.showPlayingAction.triggered.connect(self._set_running_visible)
        menuLayout.addAction(self.showPlayingAction)

        self.showDbMeterAction = QAction(parent=menuLayout)
        self.showDbMeterAction.setCheckable(True)
        self.showDbMeterAction.setChecked(self._show_dbmeter)
        self.showDbMeterAction.triggered.connect(self._set_dbmeters_visible)
        menuLayout.addAction(self.showDbMeterAction)

        self.showSeekAction = QAction(parent=menuLayout)
        self.showSeekAction.setCheckable(True)
        self.showSeekAction.setChecked(self._seeksliders_visible)
        self.showSeekAction.triggered.connect(self._set_seeksliders_visible)
        menuLayout.addAction(self.showSeekAction)

        self.accurateTimingAction = QAction(parent=menuLayout)
        self.accurateTimingAction.setCheckable(True)
        self.accurateTimingAction.setChecked(self._accurate_time)
        self.accurateTimingAction.triggered.connect(self._set_accurate_time)
        menuLayout.addAction(self.accurateTimingAction)

        self.autoNextAction = QAction(parent=menuLayout)
        self.autoNextAction.setCheckable(True)
        self.autoNextAction.setChecked(self._auto_continue)
        self.autoNextAction.triggered.connect(self._set_auto_next)
        menuLayout.addAction(self.autoNextAction)

        self.selectionModeAction = QAction(parent=menuLayout)
        self.selectionModeAction.setCheckable(True)
        self.selectionModeAction.setChecked(False)
        self.selectionModeAction.triggered.connect(self._set_selection_mode)
        menuLayout.addAction(self.selectionModeAction)

        # Context menu actions
        self._edit_actions_group = MenuActionsGroup(priority=MENU_PRIORITY_CUE)
        self._edit_actions_group.add(
            SimpleMenuAction(
                translate('ListLayout', 'Edit cue'),
                self.edit_cue,
                translate('ListLayout', 'Edit selected cues'),
                self.edit_cues,
            ),
            SimpleMenuAction(
                translate('ListLayout', 'Remove cue'),
                self.cue_model.remove,
                translate('ListLayout', 'Remove selected cues'),
                self._remove_cues
            ),
        )

        self.CuesMenu.add(self._edit_actions_group)

        self.retranslate()

    def retranslate(self):
        self.showPlayingAction.setText(
            translate('ListLayout', 'Show playing cues'))
        self.showDbMeterAction.setText(
            translate('ListLayout', 'Show dB-meters'))
        self.showSeekAction.setText(translate('ListLayout', 'Show seek-bars'))
        self.accurateTimingAction.setText(
            translate('ListLayout', 'Show accurate time'))
        self.autoNextAction.setText(
            translate('ListLayout', 'Auto-select next cue'))
        self.selectionModeAction.setText(
            translate('ListLayout', 'Selection mode'))

    def cues(self, cue_type=Cue):
        yield from self._list_model

    def view(self):
        return self._view

    def standby_index(self):
        return self._view.listView.standbyIndex()

    def set_standby_index(self, index):
        self._view.listView.setStandbyIndex(index)

    def go(self, action=CueAction.Default, advance=1):
        standby_cue = self.standby_cue()
        if standby_cue is not None:
            standby_cue.execute(action)
            self.cue_executed.emit(standby_cue)

            if self._auto_continue:
                self.set_standby_index(self.standby_index() + advance)

    def cue_at(self, index):
        return self._list_model.item(index)

    def selected_cues(self, cue_type=Cue):
        for item in self._view.listView.selectedItems():
            yield self._list_model.item(
                self._view.listView.indexOfTopLevelItem(item))

    def finalize(self):
        # Clean layout menu
        self.app.window.menuLayout.clear()
        # Clean context-menu
        self.CuesMenu.remove(self._edit_actions_group)
        # Remove reference cycle
        del self._edit_actions_group

    def select_all(self, cue_type=Cue):
        for index in range(self._view.listView.topLevelItemCount()):
            if isinstance(self._list_model.item(index), cue_type):
                self._view.listView.topLevelItem(index).setSelected(True)

    def deselect_all(self, cue_type=Cue):
        for index in range(self._view.listView.topLevelItemCount()):
            if isinstance(self._list_model.item(index), cue_type):
                self._view.listView.topLevelItem(index).setSelected(False)

    def invert_selection(self):
        for index in range(self._view.listView.topLevelItemCount()):
            item = self._view.listView.topLevelItem(index)
            item.setSelected(not item.isSelected())

    def _key_pressed(self, event):
        event.ignore()

        if not event.isAutoRepeat():
            keys = event.key()
            modifiers = event.modifiers()

            if modifiers & Qt.ShiftModifier:
                keys += Qt.SHIFT
            if modifiers & Qt.ControlModifier:
                keys += Qt.CTRL
            if modifiers & Qt.AltModifier:
                keys += Qt.ALT
            if modifiers & Qt.MetaModifier:
                keys += Qt.META

            if QKeySequence(keys) in self._go_key_sequence:
                event.accept()
                self.go()
            elif event.key() == Qt.Key_Space:
                if event.modifiers() == Qt.ShiftModifier:
                    event.accept()

                    cue = self.standby_cue()
                    if cue is not None:
                        self.edit_cue(cue)

    def _set_accurate_time(self, accurate):
        self._accurate_time = accurate
        self._view.runView.accurate_time = accurate

    def _set_auto_next(self, enable):
        self._auto_continue = enable

    def _set_seeksliders_visible(self, visible):
        self._seeksliders_visible = visible
        self._view.runView.seek_visible = visible

    def _set_dbmeters_visible(self, visible):
        self._show_dbmeter = visible
        self._view.runView.dbmeter_visible = visible

    def _set_running_visible(self, visible):
        self._show_playing = visible
        self._view.runView.setVisible(visible)
        self._view.controlButtons.setVisible(visible)

    def _set_selection_mode(self, enable):
        if enable:
            self._view.listView.setSelectionMode(CueListView.ExtendedSelection)
        else:
            self.deselect_all()
            self._view.listView.setSelectionMode(CueListView.NoSelection)

    def _double_clicked(self):
        cue = self.standby_cue()
        if cue is not None:
            self.edit_cue(cue)

    def _context_invoked(self, event):
        # This is called in response to CueListView context-events
        if self._view.listView.itemAt(event.pos()) is not None:
            cues = list(self.selected_cues())
            if not cues:
                context_index = self._view.listView.indexAt(event.pos())
                if context_index.isValid():
                    cues.append(self._list_model.item(context_index.row()))
                else:
                    return

            self.show_cue_context_menu(cues, event.globalPos())
        else:
            self.show_context_menu(event.globalPos())

    def __go_slot(self):
        self.go()

    def __cue_added(self, cue):
        cue.next.connect(self.__cue_next, Connection.QtQueued)

    def __cue_next(self, cue):
        try:
            next_index = cue.index + 1
            if next_index < len(self._list_model):
                next_cue = self._list_model.item(next_index)
                next_cue.cue.execute()

                if self._auto_continue and next_cue is self.standby_cue():
                    self.set_standby_index(next_index + 1)
        except(IndexError, KeyError):
            pass
