#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015        Nick Hall
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

__all__ = ["PlaceTypeSelector"]

from gi.repository import Gtk
#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger(".widgets.placetypeselector")

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import PlaceType
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext


#-------------------------------------------------------------------------
#
# PlaceTypeSelector class
#
#-------------------------------------------------------------------------
class PlaceTypeSelector():
    """ Class that sets up a comboentry for the place types """

    def __init__(self, dbstate, combo, ptype, changed=None, sidebar=False):
        """
        Constructor for the PlaceTypeSelector class.

        :param combo: Existing ComboBox widget to use with has_entry=True.
        :type combo: Gtk.ComboBox
        :param ptyperef: The object to fill/modify
        :type ptype: PlaceType object
        :param db: the database
        :type db: based on DbReadBase, DbWriteBase
        :param changed: To update an external element when we change value
        :type callback: method
        """
        self.ptype = ptype
        self.changed = changed
        self.combo = combo
        self.dbstate = dbstate
        self.sidebar = sidebar
        # fill out completion
        self.e_completion = Gtk.EntryCompletion()
        self.e_completion.set_minimum_key_length(1)
        self.e_completion.set_text_column(1)
        self.e_completion.connect('match-selected', self.on_entry_change)
        # following is used to indicate if an e_completion was selected
        self.entry_valid = False
        entry = combo.get_child()
        entry.set_completion(self.e_completion)
        entry.set_text(ptype.str(expand=True))

        self.fill_models()  # fill out the initial models
        combo.set_entry_text_column(1)

        combo.connect('changed', self.on_combo_change)

    def fill_models(self, *_arg):
        """ fill in the models with the current PlaceType data.  This is used
        at init and also when the user starts editing the sidebar filter.
        """
        # get completion store and menu
        store, menu = get_menu(self.dbstate.db)
        self.e_completion.set_model(store)
        # Create a model and fill it with a two or three-level tree
        # corresponding to the menu.
        # If the active key is in an items list, the group under that parent
        # is expanded.
        # Items not under a parent group are also supported.
        self.store = self.combo.get_model()
        if self.store:
            # for some reason, the combo doesn't like to have its TreeModel
            # replaced, so we need to clear it if it already exists.
            self.store.clear()
        else:
            self.store = Gtk.TreeStore(str, str)
            self.combo.set_model(self.store)
        for (heading, items) in menu:
            if not heading:  # add ptype in items if expand
                parent = None
            else:
                parent = self.store.append(None, row=[None, _(heading)])
            for item in items:
                if not isinstance(item[1], list):
                    self.store.append(parent, row=list(item))
                    continue
                heading_2, items_2 = item
                parent_2 = self.store.append(parent, row=[None, heading_2])
                for item_2 in items_2:
                    self.store.append(parent_2, row=list(item_2))
        if not self.sidebar:
            self.combo.set_sensitive(not self.dbstate.db.readonly)

    def on_combo_change(self, combo):
        """ Deal with changes in the combo or entry; put results in the
        PlaceType
        """
        active_iter = combo.get_active_iter()
        if active_iter:  # selected from menu
            self.ptype.set((self.store.get_value(active_iter, 0),   # pt_id
                            self.store.get_value(active_iter, 1)))  # name
        elif not self.entry_valid:  # custom value entered
            self.ptype.set((PlaceType.CUSTOM,
                            combo.get_child().get_text().strip()))
        else:  # selected an entry completion item, so don't modify here
            return
        if self.changed:
            self.changed()

    def on_entry_change(self, _entrycompletion, model, active_iter):
        """ Deal with changes in the combo or entry; put results in the
        PlaceType
        """
        if active_iter:
            self.ptype.set((model.get_value(active_iter, 0),   # pt_id
                            model.get_value(active_iter, 1)))  # name
            self.entry_valid = True
        if self.changed:
            self.changed()

    def update(self):
        """ An external change to self.ptype needs to be reflected
        into the combo.
        """
        if self.ptype is not None:
            self.combo.get_child().set_text(self.ptype.str(expand=True))


def get_menu(db):
    """ This creates a place type menu structure suitable for
    StandardCustomSelector.
    It processes the DATAMAP and db data into a menu.  Both of these are
    updated from the db as needed when types or groups are changed.
    This is called by the StandardCustomSelector.

    :returns: A menu suitable for StandardCustomSelector.
    :rtype: list
    """
    def prepare(ptype):
        """ prepare to use a ptype and format the name for the menu """
        if ptype != PlaceType.CUSTOM:  # if allowed to show in menu
            cats.update(ptype.countries.split())
            name = str(ptype)
            ptype.name = name
            if ptype.pt_id not in types:
                store.append(row=[ptype.pt_id, name])
            types[ptype.pt_id] = ptype
    menu = []   # the whole menu
    store = Gtk.ListStore(str, str)  # a completion list (pt_id, name)
    items = []  # list if items in a menu heading
    types = []  # list of key=hndl, data=PlaceTypes
    cats = set()  # set of catagories to display
    # created integrated dict of types
    for pt_id in PlaceType.DATAMAP:
        if pt_id != PlaceType.CUSTOM:
            ptype = PlaceType()
            ptype.set(pt_id)
            types.append((pt_id, ptype.str(expand=True),
                          ptype.get_countries()))
            store.append(row=[pt_id, ptype.str(expand=True)])
            cats.update(ptype.get_countries().split())
    for ptype in db.get_place_types():
        # they are all CUSTOM
        types.append((PlaceType.CUSTOM, ptype, '##'))
        store.append(row=[PlaceType.CUSTOM, ptype])
        cats.add('##')
    types = sorted([typ for typ in types], key=lambda typ: typ[1])

    uncommon = False  # used to avoid category sub menu entry when only common
    #                 # items are present
    for cat in sorted(cats):
        categ = (_("Common") if cat == '!!' else
                 _("Custom") if cat == '##' else cat)
        cont = False
        _mt = True
        items = []
        for pt_id, name, category in types:
            # exclude UNKNOWN, hidden items, and CUSTOM
            if cat in category:
                items.append((pt_id, name))
                _mt = False
                if len(items) == 18:    # Add 'cont.' for large groups
                    if cont:
                        # translators: used to add levels to a menu
                        # as in "Items continued" but abbreviated for brevity
                        menu.append((_("%s cont.") % categ, items))
                    else:
                        menu.append((categ, items))
                    cont = True
                    items = []
            elif cat == '!!':
                uncommon = True
        if items and not _mt:
            if cont:
                menu.append((_("%s cont.") % categ, items))
            elif uncommon:
                menu.append((categ, items))
            else:
                menu.append((None, items))
    return store, menu
