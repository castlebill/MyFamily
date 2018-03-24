#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2009       Gary Burton
# Copyright (C) 2011       Tim G L Lyons
# Copyright (C) 2017       Alois Poettker
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext

from .displaytabs import (CitationEmbedList, NoteTab, GalleryTab,
                          EventBackRefList, EventAttrEmbedList)
from .editprimary import EditPrimary
from .objectentries import PlaceEntry

from ..dialog import ErrorDialog
from ..display import display_help
from ..glade import Glade
from ..widgets import (MonitoredEntry, PrivacyButton, MonitoredDataType,
                       MonitoredDate, MonitoredTagList)

from gramps.gen.const import URL_MANUAL_SECT2
from gramps.gen.db import DbTxn
from gramps.gen.lib import Event, EventRef, NoteType
from gramps.gen.utils.db import get_participant_from_event

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------

WIKI_HELP_PAGE = URL_MANUAL_SECT2
WIKI_HELP_SEC = _('manual|New_Event_dialog')

#-------------------------------------------------------------------------
#
# EditEvent class
#
#-------------------------------------------------------------------------
class EditEvent(EditPrimary):
    """
    Class to edit events
    """
    def __init__(self, dbstate, uistate, track, event, callback=None):
        """"""
        self.dbase = dbstate.db
        self.callback = callback
        self.action = uistate.action.split('-')[1]

        EditPrimary.__init__(self, dbstate, uistate, track, event,
                             self.dbase.get_event_from_handle,
                             self.dbase.get_event_from_gramps_id)
        self._init_event()

    def _init_event(self):
        if not self.dbase.readonly:
            self.commit_event = self.dbase.commit_event

    def empty_object(self):
        return Event()

    def get_menu_title(self):
        """ compile menu title out of different actions """
        handle = self.obj.get_handle()

        event_action, event_name = '', ''
        if handle:
            if self.action == 'clone':
                event_action = _('Clone')

            who = get_participant_from_event(self.dbase, handle)
            desc = self.obj.get_description()
            event_name = self.obj.get_type()
            if desc:
                event_name = ': %s - %s' % (event_name, desc)
            if who:
                event_name = ': %s - %s' % (event_name, who)
        else:
            event_action = _('New')

        dialog_title = _('%s Event%s') % (event_action, event_name)
        return dialog_title

    def get_custom_events(self):
        return sorted(self.dbase.get_event_types(),
                      key=lambda s: s.lower())

    def _local_init(self):
        self.top = Glade()
        self.set_window(self.top.toplevel, None,
                        self.get_menu_title())
        self.setup_configs('interface.event', 600, 450)

        self.place = self.top.get_object('place')
        self.share_btn = self.top.get_object('select_place')
        self.add_del_btn = self.top.get_object('add_del_place')

    def _connect_signals(self):
        self.top.get_object('button111').connect('clicked', self.close)
        self.top.get_object('button126').connect('clicked', self.help_clicked)

        self.ok_button = self.top.get_object('ok')
        self.ok_button.set_sensitive(not self.dbase.readonly)
        self.ok_button.connect('clicked', self.save)

    def _connect_db_signals(self):
        """
        Connect any signals that need to be connected.
        Called by the init routine of the base class (_EditPrimary).
        """
        self._add_db_signal('event-rebuild', self._do_close)
        self._add_db_signal('event-delete', self.check_for_close)

    def _setup_fields(self):

        self.place_field = PlaceEntry(self.dbstate, self.uistate, self.track,
                                      self.top.get_object("place"),
                                      self.top.get_object("place_event_box"),
                                      self.obj.set_place_handle,
                                      self.obj.get_place_handle,
                                      self.add_del_btn, self.share_btn)

        self.descr_field = MonitoredEntry(self.top.get_object("event_description"),
                                          self.obj.set_description,
                                          self.obj.get_description,
                                          self.dbase.readonly)

        self.gid = MonitoredEntry(self.top.get_object("gid"),
                                  self.obj.set_gramps_id,
                                  self.obj.get_gramps_id, self.dbase.readonly)

        self.tags = MonitoredTagList(self.top.get_object("tag_label"),
                                     self.top.get_object("tag_button"),
                                     self.obj.set_tag_list,
                                     self.obj.get_tag_list,
                                     self.dbase,
                                     self.uistate, self.track,
                                     self.dbase.readonly)

        self.priv = PrivacyButton(self.top.get_object("private"),
                                  self.obj, self.dbase.readonly)

        self.event_menu = MonitoredDataType(self.top.get_object("personal_events"),
                                        self.obj.set_type,
                                        self.obj.get_type,
                                        custom_values=self.get_custom_events())

        self.date_field = MonitoredDate(self.top.get_object("date_entry"),
                                        self.top.get_object("date_stat"),
                                        self.obj.get_date_object(),
                                        self.uistate, self.track,
                                        self.dbase.readonly)

    def _create_tabbed_pages(self):
        """
        Create the notebook tabs and inserts them into the main window.
        """
        notebook = Gtk.Notebook()

        self.citation_list = CitationEmbedList(self.dbstate,
                                               self.uistate,
                                               self.track,
                                               self.obj.get_citation_list(),
                                               self.get_menu_title())
        self._add_tab(notebook, self.citation_list)

        self.note_list = NoteTab(self.dbstate,
                                 self.uistate,
                                 self.track,
                                 self.obj.get_note_list(),
                                 notetype=NoteType.EVENT)
        self._add_tab(notebook, self.note_list)


        self.gallery_list = GalleryTab(self.dbstate,
                                       self.uistate,
                                       self.track,
                                       self.obj.get_media_list())
        self._add_tab(notebook, self.gallery_list)

        self.attr_list = EventAttrEmbedList(self.dbstate,
                                            self.uistate,
                                            self.track,
                                            self.obj.get_attribute_list())
        self._add_tab(notebook, self.attr_list)

        handle_list = self.dbase.find_backlink_handles(self.obj.handle)
        self.reference_list = list(self.dbase.find_backlink_handles(self.obj.handle))
        # Necessary variables in 'EventBackRefList' transported via 'option'
        ref_option = {}
        ref_option['del_btn'] = self.action == 'clone'
        ref_option['ref_call'] = self.reference_callback
        self.backref_list = EventBackRefList(self.dbstate,
                                             self.uistate,
                                             self.track,
                                             handle_list,
                                             option=ref_option)
        self._add_tab(notebook, self.backref_list)

        self._setup_notebook_tabs(notebook)

        notebook.show_all()
        self.top.get_object('vbox').pack_start(notebook, True, True, 0)

        self.track_ref_for_deletion("citation_list")
        self.track_ref_for_deletion("note_list")
        self.track_ref_for_deletion("gallery_list")
        self.track_ref_for_deletion("attr_list")
        self.track_ref_for_deletion("backref_list")

    def build_menu_names(self, event):
        return (_('Edit Event'), self.get_menu_title())

    def help_clicked(self, obj):
        """ display the relevant portion of Gramps manual """
        display_help(webpage=WIKI_HELP_PAGE, section=WIKI_HELP_SEC)

    def reference_callback(self, ref=None):
        """ create actual reference list """
        if ref:
            self.reference_list = \
                [(obj, handle) for obj, handle in self.reference_list if handle != ref]

        return self.reference_list

    def save(self, *obj):
        """ after failure checking saves event through different criteria """

        self.ok_button.set_sensitive(False)
        if self.object_is_empty():
            ErrorDialog(_("Cannot save event"),
                        _("No data exists for this event. Please "
                          "enter data or cancel the edit."),
                        parent=self.window)
            self.ok_button.set_sensitive(True)
            return

        (uses_dupe_id, ident) = self._uses_duplicate_id()
        if uses_dupe_id:
            prim_object = self.get_from_gramps_id(ident)
            name = prim_object.get_description()
            msg1 = _("Cannot save event. ID already exists.")
            msg2 = _("You have attempted to use the existing Gramps ID with "
                         "value %(ident)s. This value is already used by '"
                         "%(prim_object)s'. Please enter a different ID or leave "
                         "blank to get the next available ID value.") % \
                        {'ident' : ident, 'prim_object' : name}
            ErrorDialog(msg1, msg2, parent=self.window)
            self.ok_button.set_sensitive(True)
            return

        obj_type = self.obj.get_type()
        if obj_type.is_custom() and str(obj_type) == '':
            ErrorDialog(
                _("Cannot save event"),
                _("The event type cannot be empty"),
                parent=self.window)
            self.ok_button.set_sensitive(True)
            return

        if not self.obj.handle:
            with DbTxn(_("Add Event (%s)") % self.obj.get_gramps_id(),
                       self.db) as trans:
                self.dbase.add_event(self.obj, trans)
        else:
            if self.action == 'clone':
                self.save_clone()
            if self.data_has_changed():
                with DbTxn(_("Edit Event (%s)") % self.obj.get_gramps_id(),
                           self.db) as trans:
                    if not self.obj.get_gramps_id():
                        self.obj.set_gramps_id(self.dbase.find_next_event_gramps_id())
                    self.dbase.commit_event(self.obj, trans)

        if self.callback:
            self.callback(self.obj)
        self._do_close()

    def save_clone(self):
        """ saves a cloned event """

        person_list, family_list = [], []
        for item in self.reference_list:
            if item[0] == 'Person':
                person_list.append(item[1])
            if item[0] == 'Family':
                family_list.append(item[1])

        with DbTxn(_("Clone Event"), self.dbase) as trans:
            # add a new (gramps_id & handle == None) event to database
            self.obj.handle = None
            self.dbase.add_event(self.obj, trans)

            # create the reference list and add to ...
            event_ref = EventRef()
            event_ref.set_reference_handle(self.obj.handle)

            # persons
            for handle in person_list:
                person = self.dbase.get_person_from_handle(handle)
                person.add_event_ref(event_ref)
                self.dbase.commit_person(person, trans)

            # families
            for handle in family_list:
                family = self.dbase.get_family_from_handle(handle)
                family.add_event_ref(event_ref)
                self.dbase.commit_family(family, trans)

        pass

    def data_has_changed(self):
        """
        A date comparison can fail incorrectly because we have made the
        decision to store entered text in the date. However, there is no
        entered date when importing from a XML file, so we can get an
        incorrect fail.
        """
        if self.dbase.readonly:
            return False
        elif self.obj.handle:
            orig = self.get_from_handle(self.obj.handle)
            if orig:
                cmp_obj = orig
            else:
                cmp_obj = self.empty_object()
            return cmp_obj.serialize(True)[1:] != self.obj.serialize(True)[1:]
        else:
            cmp_obj = self.empty_object()
            return cmp_obj.serialize(True)[1:] != self.obj.serialize()[1:]

#-------------------------------------------------------------------------
#
# Delete Query class
#
#-------------------------------------------------------------------------
class DeleteEventQuery(object):
    """
    Class to delete event and references to this
    """
    def __init__(self, dbstate, uistate, event, person_list, family_list):
        """"""
        self.event = event
        self.dbase = dbstate.db
        self.uistate = uistate
        self.person_list = person_list
        self.family_list = family_list

    def query_response(self):
        with DbTxn(_("Delete Event (%s)") % self.event.get_gramps_id(),
                   self.dbase) as trans:
            self.dbase.disable_signals()

            ev_handle_list = [self.event.get_handle()]

            for handle in self.person_list:
                person = self.dbase.get_person_from_handle(handle)
                person.remove_handle_references('Event', ev_handle_list)
                self.dbase.commit_person(person, trans)

            for handle in self.family_list:
                family = self.dbase.get_family_from_handle(handle)
                family.remove_handle_references('Event', ev_handle_list)
                self.dbase.commit_family(family, trans)

            self.dbase.enable_signals()
            self.dbase.remove_event(self.event.get_handle(), trans)
