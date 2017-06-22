from abc import abstractmethod

from test.stubs.sublime import View


class TextCommand:
    def __init__(self):
        self.view = View()

    @abstractmethod
    def run(self, edit):
        raise NotImplementedError


class EventListener:
    pass


class WindowCommand:
    def __init__(self, window):
        self.window = window

    def get_window(self):
        pass
