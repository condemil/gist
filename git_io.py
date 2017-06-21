from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

try:
    import sublime
    import sublime_plugin
except ImportError:
    from test.stubs import sublime
    from test.stubs import sublime_plugin

git_url = 'https://git.io/create'
caption = '[Enter a GitHub.com URL]  ' + b'\xe2\x96\x88'.decode('utf-8')


def git_io(req_url):
    data = urlencode({'url': req_url}).encode()

    try:
        response = urlopen(git_url, data)
        body = response.read().decode()
        if response.status == 200:
            return None, 'https://git.io/{}'.format(body)

        return body, None
    except HTTPError as ex:
        return ex.read().decode(), None
    except URLError:
        return 'Gist: Error contacting git.io', None


class GistGitioCommand(sublime_plugin.TextCommand):
    def run(self, edit):  # pylint: disable=unused-argument
        self.view.window().show_input_panel(caption, '', self.on_done, None, None)

    def on_done(self, req_url):
        err, short_url = git_io(req_url)
        if err:
            sublime.error_message(err)
            self.view.window().show_input_panel(caption, req_url, self.on_done, None, None)
        else:
            sublime.set_clipboard(short_url)
            sublime.status_message('Gist: Copied to Clipboard! ' + short_url)
