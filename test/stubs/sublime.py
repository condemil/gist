import json
import re
from os import path

settings_storage = {}
_windows = []

json_comments_regex = re.compile(r'^\s*//.*', re.MULTILINE)


def status_message(message):
    print(message)


def error_message(message):
    print(message)


def packages_path():
    return ''


def set_clipboard(data):
    pass


def active_window():
    return Window(0)


def windows():
    return [Window(window_id) for window_id in _windows]


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


class Settings:
    def __init__(self, settings):
        self._settings = settings
        self.reload_methods = []

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings[key] = value

    def add_on_change(self, tag, callback):
        if tag == 'reload':
            self.reload_methods.append(callback)


class View:
    def __init__(self):
        self._settings = Settings({})
        self._window = Window(0)

    def settings(self):
        return self._settings

    def window(self):
        return self._window

    def size(self):
        return 0

    def file_name(self):
        return ''

    def substr(self, x):
        return ''


class Window:
    def __init__(self, window_id):
        self.window_id = window_id

    def new_file(self):
        pass

    def show_input_panel(self, caption, initial_text, on_done, on_change, on_cancel):
        """ on_done and on_change should accept a string argument, on_cancel should have no arguments """
        return View()
