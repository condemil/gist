import json
import re
from os import path
from unittest.mock import Mock

settings_storage = {}
_windows = {}

json_comments_regex = re.compile(r'^\s*//.*', re.MULTILINE)


status_message = Mock()
error_message = Mock()
set_clipboard = Mock()


def packages_path():
    return ''


def active_window():
    if 0 not in _windows:
        _windows[0] = Window(0)
    return _windows[0]


def windows():
    return _windows.values()


def load_settings(settings_filename):
    if settings_filename not in settings_storage:
        settings_data = _get_settings_from_file(settings_filename)
        settings_storage[settings_filename] = Settings(settings_data)
    return settings_storage[settings_filename]


def _reload_settings(settings_filename):
    if settings_filename not in settings_storage:
        return

    settings_data = _get_settings_from_file(settings_filename)
    # noinspection PyProtectedMember
    settings_storage[settings_filename]._settings = settings_data

    for callback in settings_storage[settings_filename].reload_methods:
        callback()


def _get_settings_from_file(settings_filename):
    current_directory = path.dirname(__file__)
    settings_filepath = path.abspath(path.join(current_directory, '..', '..', settings_filename))
    with open(settings_filepath) as f:
        file_content = f.read()
        file_content = json_comments_regex.sub('', file_content)
        return json.loads(file_content)


class Region(object):
    def __init__(self, a, b=None, x_pos=-1):
        if b is None:
            b = a
        self.a = a
        self.b = b
        self.x_pos = x_pos

    def empty(self):
        return self.a == self.b


class Settings:
    def __init__(self, settings):
        self._settings = settings
        self.reload_methods = []

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings[key] = value

    def erase(self, key):
        try:
            del self._settings[key]
        except KeyError:
            pass

    def add_on_change(self, tag, callback):
        if tag == 'reload':
            self.reload_methods.append(callback)


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class View:
    def __init__(self):
        self._settings = Settings({})
        self._window = Mock()
        self._file_name = None
        self._status = {}
        self._run_command = Mock()
        self.selection = Mock()
        self.selection.return_value = []

    def settings(self):
        return self._settings

    def window(self):
        return self._window

    def size(self):
        return 0

    def file_name(self):
        return self._file_name

    def set_name(self, name):
        self._file_name = name

    def substr(self, x):
        return ''

    def set_status(self, key, value):
        self._status[key] = value

    def erase_status(self, key):
        try:
            del self._status[key]
        except KeyError:
            pass

    def run_command(self, cmd, args=None):
        self._run_command(cmd, args=args)

    def set_scratch(self, scratch):
        """
        Sets the scratch flag on the text buffer. When a modified scratch buffer
        is closed, it will be closed without prompting to save.
        """
        return scratch

    def retarget(self, new_fname):
        pass

    def sel(self):
        return self.selection()


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class Window:
    def __init__(self, window_id):
        self.window_id = window_id
        self._view = View()

    def open_file(self, fname, flags=0, group=-1):
        """
        valid bits for flags are:
        ENCODED_POSITION: fname name may have :row:col or :row suffix
        TRASIENT: don't add the file to the list of open buffers
        FORCE_GROUP: don't select the file if it's opened in a different group
        """
        return View()

    def new_file(self):
        return View()

    def show_input_panel(self, caption, initial_text, on_done, on_change, on_cancel):
        """ on_done and on_change should accept a string argument, on_cancel should have no arguments """
        return View()

    def show_quick_panel(self, items, on_select, flags=0, selected_index=-1, on_highlight=None):
        """
        on_select is called when the the quick panel is finished, and should
        accept a single integer, specifying which item was selected, or -1 for none

        on_highlight is called when the quick panel is still active, and
        indicates the current highlighted index

        flags is a bitwise OR of MONOSPACE_FONT, and KEEP_OPEN_ON_FOCUS_LOST
        """
        pass

    def active_view(self):
        return View()

    def views(self):
        return [self._view]
