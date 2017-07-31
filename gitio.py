from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

try:
    import sublime
    import sublime_plugin
except ImportError:
    from test.stubs import sublime
    from test.stubs import sublime_plugin

gitio_url = 'https://git.io/create'
caption = 'GitHub URL:'


def gitio(req_url):
    data = urlencode({'url': req_url}).encode()

    try:
        response = urlopen(gitio_url, data)
        body = response.read().decode()
        if response.status == 200:
            return None, 'https://git.io/{}'.format(body)

        return body, None
    except HTTPError as e:
        return e.read().decode(), None
    except URLError:
        return 'Gist: Error contacting git.io', None


class GitioCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().show_input_panel(caption, '', self.on_done, None, None)

    def on_done(self, req_url):
        err, short_url = gitio(req_url)
        if err:
            sublime.error_message(err)
            self.view.window().show_input_panel(caption, req_url, self.on_done, None, None)
        else:
            sublime.set_clipboard(short_url)
            sublime.status_message('Gist: Copied to Clipboard! ' + short_url)
