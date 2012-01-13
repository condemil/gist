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
settings = sublime.load_settings('Gist.sublime-settings')
GISTS_URL = 'https://api.github.com/gists'

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

def create_gist(public, text, filename, description):
    data = json.dumps({'description': description, 'public': public, 'files': {filename: {'content': text}}})
    gist = api_request(GISTS_URL, data)
    gist_html_url = gist['html_url']
    sublime.set_clipboard(gist_html_url)
    sublime.status_message("Gist: " + gist_html_url)
    return gist

@catching_credential_errors
def update_gist(gist_url, gist_filename, text):
    data = json.dumps({'files': {gist_filename: {'content': text}}})
    result = api_request(gist_url, data, method="PATCH")
    sublime.status_message("Gist updated")

def gistify_view(view, gist, gist_filename):
    if not view.name():
        view.set_name(gist_filename)

    view.settings().set('gist_html_url', gist["html_url"])
    view.settings().set('gist_url', gist["url"])
    view.settings().set('gist_filename', gist_filename)
    view.set_status("Gist", "Gist %s" % gist_title(gist))

def get_gist(url_gist):
    gist = api_request(url_gist)
    for gist_filename, file_data in gist['files'].items():
        view = sublime.active_window().new_file()

        gistify_view(view, gist, gist_filename)

        edit = view.begin_edit()
        view.insert(edit, 0, file_data['content'])
        view.end_edit(edit)

def get_gists():
    return api_request(GISTS_URL)

def gist_title(gist):
    return gist.get('description') or gist.get('id')

def api_request_native(url_api, data = '', method = None):
    request = urllib2.Request(url_api)
    if method:
        request.get_method = lambda: method
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

def api_request_wget(url_api, data = '', method = None):
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
        error = Exception('Wget exits with code %s' % returncode)
        raise error

    return json.loads(response)

api_request = api_request_wget if ('ssl' not in sys.modules and os.name != 'nt') else api_request_native

class GistCommand(sublime_plugin.TextCommand):
    public = True

    def mode(self):
        return "Public" if self.public else "Private"

    @catching_credential_errors
    def run(self, edit):
        get_credentials()
        selections = [region for region in self.view.sel() if not region.empty()]

        if len(selections) == 0:
            selections = [sublime.Region(0, self.view.size())]
            gistify = True
        else:
            gistify = False

        window = self.view.window()

        def create_gist_with_text(text):
            filename = os.path.basename(self.view.file_name()) if self.view.file_name() else ''

            def on_gist_filename(filename):
                @catching_credential_errors
                def on_gist_description(description):
                    gist = create_gist(self.public, text, filename, description)
                    print gist
                    if gistify:
                        gistify_view(self.view, gist, filename)

                window.show_input_panel('%s Gist Description (optional):' % self.mode(), '', on_gist_description, None, None)

            window.show_input_panel('%s Gist File Name: (optional):' % self.mode(), filename, on_gist_filename, None, None)

        for region in selections:
            create_gist_with_text(self.view.substr(region))

class GistCopyUrl(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.settings().get("gist_html_url") is not None

    def run(self, edit):
        sublime.set_clipboard(self.view.settings().get("gist_html_url"))

class GistOpenBrowser(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.settings().get("gist_html_url") is not None

    def run(self, edit):
        webbrowser.open(self.view.settings().get("gist_html_url"))

class GistUpdateCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.settings().get("gist_url") is not None

    def is_visible(self):
        # wget doesn't support changing HTTP method
        return api_request != api_request_wget

    @catching_credential_errors
    def run(self, edit):
        text = self.view.substr(sublime.Region(0, self.view.size()))
        update_gist(self.view.settings().get("gist_url"), self.view.settings().get("gist_filename"), text)

class GistPrivateCommand(GistCommand):
    public = False

class GistListCommand(sublime_plugin.WindowCommand):
    @catching_credential_errors
    def run(self):
        gists = get_gists()

        gist_names = [gist_title(gist) for gist in gists]
        gist_urls = [gist['url'] for gist in gists]


        self.window.show_quick_panel(
            gist_names,
            lambda num: get_gist(gist_urls[num]))
