import sublime
import sublime_plugin
import os
import sys
import json
import base64
import urllib2
import subprocess
import functools
import webbrowser

DEFAULT_CREATE_PUBLIC_VALUE = 'false'
DEFAULT_USE_PROXY_VALUE = 'false'
_selectedText = ''
_fileName = ''
_gistsUrls = []
settings = sublime.load_settings('Gist.sublime-settings')
url = 'https://api.github.com/gists'

class GistMissingCredentialsException(Exception):
    pass

def get_credentials():
    username = settings.get('username')
    password = settings.get('password')
    if not username or not password:
        raise GistMissingCredentialsException()
    return (username, password)

if sublime.platform() == 'osx':
    # Keychain support
    # Instead of Gist.sublime-settings, fetch username and password from the user's github.com keychain entry
    SERVER = 'github.com'

    def create_keychain_accessor():
        from ctypes import cdll, util, c_uint32, c_int, c_char_p, c_void_p, POINTER, pointer, byref, Structure, string_at
        lib_security = cdll.LoadLibrary(util.find_library('Security'))

        class SecKeychainAttributeInfo(Structure):
            _fields_ = [("count", c_uint32), ("tag", POINTER(c_uint32)), ("format", POINTER(c_uint32))]

        class SecKeychainAttribute(Structure):
            _fields_ = [("tag", c_uint32), ("length", c_uint32), ("data", c_void_p)]

        class SecKeychainAttributeList(Structure):
            _fields_ = [("count", c_uint32), ("attr", POINTER(SecKeychainAttribute))]

        def keychain_get_credentials():
            username = settings.get('username')
            password = settings.get('password')
            if username and password:
                return (username, password)

            password_buflen = c_uint32()
            password_buf = c_void_p()
            item = c_void_p()

            error = lib_security.SecKeychainFindInternetPassword(
               None, # keychain, NULL = default
               c_uint32(len(SERVER)), # server name length
               c_char_p(SERVER),      # server name
               c_uint32(0), # security domain - unused
               None,        # security domain - unused
               c_uint32(0 if not username else len(username)), # account name length
               None if not username else c_char_p(username),   # account name
               c_uint32(0), # path name length - unused
               None,        # path name
               c_uint32(0), # port, 0 = any
               c_int(0), # kSecProtocolTypeAny
               c_int(0), # kSecAuthenticationTypeAny
               None, # returned password length - unused
               None, # returned password data - unused
               byref(item)) # returned keychain item reference
            if not error:
                info = SecKeychainAttributeInfo(
                    1, # attribute count
                    pointer(c_uint32(1633903476)), # kSecAccountItemAttr
                    pointer(c_uint32(6))) # CSSM_DB_ATTRIBUTE_FORMAT_BLOB

                attrlist_ptr = pointer(SecKeychainAttributeList())
                error = lib_security.SecKeychainItemCopyAttributesAndData(
                    item, # keychain item reference
                    byref(info), # list of attributes to retrieve
                    None, # returned item class - unused
                    byref(attrlist_ptr), # returned attribute data
                    byref(password_buflen), # returned password length
                    byref(password_buf)) # returned password data

                if not error:
                    try:
                        if attrlist_ptr.contents.count == 1:
                            attr = attrlist_ptr.contents.attr.contents
                            username = string_at(attr.data, attr.length)
                            password = string_at(password_buf.value, password_buflen.value)
                    finally:
                        lib_security.SecKeychainItemFreeContent(attrlist_ptr, password_buf)

            if not username or not password:
                raise GistMissingCredentialsException()
            else:
                return (username, password)

        return keychain_get_credentials
    get_credentials = create_keychain_accessor()

def catching_credential_errors(fn):
    @functools.wraps(fn)
    def _fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except GistMissingCredentialsException:
            sublime.error_message("GitHub username or password isn't provided in Gist.sublime-settings file")
    return _fn

def create_gist(description, public):
    data = json.dumps({ 'description': description, 'public': public, 'files': { _fileName: {'content': _selectedText} }})
    result = api_request(url, data)
    sublime.set_clipboard(result['html_url'])
    if settings.get("open_in_browser"):
        webbrowser.open(result['html_url'])
    sublime.status_message("Gist: " + result['html_url'])

def get_gist(url_gist):
    gists = api_request(url_gist)
    for gist in gists['files']:
        sublime.set_clipboard(gists['files'][gist]['content'])

def get_gists():
    gists = api_request(url)

    gistsNames = []

    for gist in gists:
        if gist['description']:
            gistsNames.append(gist['description'])
        else:
            gistsNames.append(u'[No Name]')

        _gistsUrls.append(gist['url'])

    return gistsNames

def api_request(url_api, data = ''):
    if not 'ssl' in sys.modules and not os.name == 'nt':
        return api_request_wget(url_api, data)

    request = urllib2.Request(url_api)
    request.add_header('Authorization', 'Basic ' + base64.urlsafe_b64encode("%s:%s" % get_credentials()))
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

    authorization_string = "%s:%s" % get_credentials()

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
    @catching_credential_errors
    def run(self):
        get_credentials()
        fileName = os.path.basename(self.window.active_view().file_name()) if self.window.active_view().file_name() else ''
        self.window.show_input_panel('Public Gist File Name: (optional):', fileName, self.on_done_input_file_name, None, None)

    def on_done_input_file_name(self, fileName):
        global _fileName
        _fileName = fileName
        self.window.show_input_panel('Public Gist Description (optional):', '', self.on_done_input_description, None, None)

    @catching_credential_errors
    def on_done_input_description(self, description):
        create_gist(description, "true")

class PromptPrivateGistCommand(sublime_plugin.WindowCommand):
    @catching_credential_errors
    def run(self):
        get_credentials()
        fileName = os.path.basename(self.window.active_view().file_name()) if self.window.active_view().file_name() else ''
        self.window.show_input_panel('Private Gist File Name: (optional):', fileName, self.on_done_input_file_name, None, None)

    def on_done_input_file_name(self, fileName):
        global _fileName
        _fileName = fileName
        self.window.show_input_panel('Private Gist Description (optional):', '', self.on_done_input_description, None, None)

    @catching_credential_errors
    def on_done_input_description(self, description):
        create_gist(description, "false")

class GistCommand(sublime_plugin.TextCommand):
    def run(self, edit):
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
        for selectedRegion in self.view.sel():
            if not selectedRegion.empty():
                global _selectedText
                _selectedText = self.view.substr(selectedRegion)
                self.view.window().run_command('prompt_private_gist')
            else:
                _selectedText = self.view.substr(sublime.Region(0, self.view.size()))
                self.view.window().run_command('prompt_private_gist')

class GistListCommand(sublime_plugin.WindowCommand):
    @catching_credential_errors
    def run(self):
        gists = get_gists()
        self.window.show_quick_panel(gists, self.on_done)

    @catching_credential_errors
    def on_done(self, num):
        get_gist(_gistsUrls[num])
