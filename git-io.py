import sys
PY3 = sys.version > '3'

git_url = 'http://git.io/'
caption = '[Enter a GitHub.com URL]  ' + b'\xe2\x96\x88'.decode('utf-8')
url_msg = 'Gist: Must be a GitHub.com URL.'
err_msg = 'Gist: Error contacting git.io'

def git_io(req_url):
    if PY3:
        import urllib.request
        urlopen = urllib.request.urlopen
        data = bytes(
            urllib.parse.urlencode(
                {'url': req_url}
            ), encoding='ascii'
        )
        URLError = urllib.error.HTTPError
    else:
        import urllib
        urlopen = urllib.urlopen
        data = urllib.urlencode({'url': req_url})
        URLError = KeyError
    try:
        return urlopen(git_url, data).headers['location']
    except URLError:
        return url_msg
    except:
        return err_msg

import sublime, sublime_plugin

class GistGitioCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().show_input_panel(caption, '', self.on_done, None, None)

    def on_done(self, req_url):
        short_url = git_io(req_url)
        if short_url in (url_msg, err_msg):
            sublime.error_message(short_url)
            self.view.window().show_input_panel(caption, req_url, self.on_done, None, None)
        else:
            sublime.set_clipboard(short_url)
            sublime.status_message('Gist: Copied to Clipboard! ' + short_url)
