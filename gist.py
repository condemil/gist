import sublime
import sublime_plugin
import os
import sys
import json
import base64
import urllib2
import subprocess

DEFAULT_CREATE_PUBLIC_VALUE = 'false'
DEFAULT_USE_PROXY_VALUE = 'false'
_selectedText = ''
_fileName = ''
_gistsUrls = []
settings = sublime.load_settings('Gist.sublime-settings')
url = 'https://api.github.com/gists'

def check_settings():
    if not settings.get('username') or not settings.get('password'):
        sublime.status_message('GitHub username or password doesn\'t provided in Gist.sublime-settings file')
        return False

    return True

def create_gist(description, public):
    data = json.dumps({ 'description': description, 'public': public, 'files': { _fileName: {'content': _selectedText} }})

    result = api_request(url, data)

    sublime.set_clipboard(result['html_url'])

def get_gist(url_gist):
    gists = api_request(url_gist)

    for gist in gists['files']:
        sublime.set_clipboard(gists['files'][gist]['content'])

def get_gists():
    gists = api_request(url)

    gistsNames = []

    for gist in gists:
        if(gist['description'] != ''):
            gistsNames.append([gist['description']])
        else:
            gistsNames.append([u'[No Name]'])

        _gistsUrls.append([gist['url']])

    return gistsNames

def api_request(url_api, data = ''):
    if not 'ssl' in sys.modules and not os.name == 'nt':
        return api_request_wget(url_api, data)

    request = urllib2.Request(url_api)
    request.add_header('Authorization', 'Basic ' + base64.urlsafe_b64encode("%s:%s" % (settings.get('username'), settings.get('password'))))
    request.add_header('Accept', 'application/json')
    request.add_header('Content-Type', 'application/json')

    if len(data) > 0:
        request.add_data(data)

    if settings.get('https_proxy'):
        opener = urllib2.build_opener(urllib2.HTTPHandler(), urllib2.HTTPSHandler(),
                                      urllib2.ProxyHandler({'https': settings.get('https_proxy')}))

        urllib2.install_opener(opener)

    response = urllib2.urlopen(request)

    return json.loads(response.read())

def api_request_wget(url_api, data = ''):
    dirs = ['/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin', '/sbin', '/bin']

    for dir in dirs:
        path = os.path.join(dir, 'wget')

        if os.path.exists(path):
            wget = path
            break

    if (not wget):
        return False

    authorization_string = "%s:%s" % (settings.get('username'), settings.get('password'))

    command = [wget, '-O', '-', '-q']
    command.append('--header=Authorization: Basic ' + base64.urlsafe_b64encode(authorization_string))
    command.append('--header=Accept: application/json')
    command.append('--header=Content-Type: application/json')

    if len(data) > 0:
        command.append('--post-data=' + data)

    command.append(url_api)

    if settings.get('https_proxy'):
        os.putenv('https_proxy', settings.get('https_proxy'))

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    response = process.stdout.read()

    returncode = process.wait()

    if returncode != 0:
        error = BaseException('Wget exits with code %s' % returncode)
        raise error

    return json.loads(response)

class PromptPublicGistCommand(sublime_plugin.WindowCommand):
    def run(self):
        fileName = os.path.basename(self.window.active_view().file_name()) if self.window.active_view().file_name() else ''
        self.window.show_input_panel('Public Gist File Name: (optional):', fileName, self.on_done_input_file_name, None, None)

    def on_done_input_file_name(self, fileName):
        global _fileName
        _fileName = fileName
        self.window.show_input_panel('Public Gist Description (optional):', '', self.on_done_input_description, None, None)

    def on_done_input_description(self, description):
        create_gist(description, "true")

class PromptPrivateGistCommand(sublime_plugin.WindowCommand):
    def run(self):
        fileName = os.path.basename(self.window.active_view().file_name()) if self.window.active_view().file_name() else ''
        self.window.show_input_panel('Private Gist File Name: (optional):', fileName, self.on_done_input_file_name, None, None)

    def on_done_input_file_name(self, fileName):
        global _fileName
        _fileName = fileName
        self.window.show_input_panel('Private Gist Description (optional):', '', self.on_done_input_description, None, None)

    def on_done_input_description(self, description):
        create_gist(description, "false")

class GistCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(check_settings()):
            for selectedRegion in self.view.sel():
                if not selectedRegion.empty():
                    global _selectedText
                    _selectedText = self.view.substr(selectedRegion)
                    self.view.window().run_command('prompt_public_gist')
                else:
                    _selectedText = self.view.substr(sublime.Region(0, self.view.size()))
                    self.view.window().run_command('prompt_public_gist')

class GistPrivateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(check_settings()):
            for selectedRegion in self.view.sel():
                if not selectedRegion.empty():
                    global _selectedText
                    _selectedText = self.view.substr(selectedRegion)
                    self.view.window().run_command('prompt_private_gist')
                else:
                    _selectedText = self.view.substr(sublime.Region(0, self.view.size()))
                    self.view.window().run_command('prompt_private_gist')

class GistListCommand(sublime_plugin.WindowCommand):
    def run(self):
        if(check_settings()):
            gists = get_gists()
            self.window.show_quick_panel(gists, self.on_done)

    def on_done(self, num):
        get_gist(_gistsUrls[num][0])
