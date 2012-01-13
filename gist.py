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
import tempfile
import traceback

DEFAULT_CREATE_PUBLIC_VALUE = 'false'
DEFAULT_USE_PROXY_VALUE = 'false'
settings = sublime.load_settings('Gist.sublime-settings')
GISTS_URL = 'https://api.github.com/gists'

class MissingCredentialsException(Exception):
    pass

class CurlNotFoundException(Exception):
    pass

def get_credentials():
    username = settings.get('username')
    password = settings.get('password')
    if not username or not password:
        raise MissingCredentialsException()
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
                raise MissingCredentialsException()
            else:
                return (username, password)

        return keychain_get_credentials
    get_credentials = create_keychain_accessor()

def catch_errors(fn):
    @functools.wraps(fn)
    def _fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except MissingCredentialsException:
            sublime.error_message("Gist: GitHub username or password isn't provided in Gist.sublime-settings file")
        except subprocess.CalledProcessError as err:
            sublime.error_message("Gist: Error while contacting GitHub: cURL returned %d" % err.returncode)
        except EnvironmentError as err:
            traceback.print_exc()
            if type(err) == OSError and err.errno == 2 and api_request == api_request_curl:
                sublime.error_message("Gist: Unable to find Python SSL module or cURL")
            else:
                msg = "Gist: Error while contacting GitHub"
                if err.strerror:
                    msg += err.strerror
                sublime.error_message(msg)
        except:
            traceback.print_exc()
            sublime.error_message("Gist: unknown error (please, report a bug!)")
    return _fn

def create_gist(public, text, filename, description):
    data = json.dumps({'description': description, 'public': public, 'files': {filename: {'content': text}}})
    gist = api_request(GISTS_URL, data)
    gist_html_url = gist['html_url']
    sublime.set_clipboard(gist_html_url)
    sublime.status_message("Gist: " + gist_html_url)
    return gist

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

def api_request_native(url, data=None, method=None):
    request = urllib2.Request(url)
    if method:
        request.get_method = lambda: method
    request.add_header('Authorization', 'Basic ' + base64.urlsafe_b64encode("%s:%s" % get_credentials()))
    request.add_header('Accept', 'application/json')
    request.add_header('Content-Type', 'application/json')

    if data is not None:
        request.add_data(data)

    if settings.get('https_proxy'):
        opener = urllib2.build_opener(urllib2.HTTPHandler(), urllib2.HTTPSHandler(),
                                      urllib2.ProxyHandler({'https': settings.get('https_proxy')}))

        urllib2.install_opener(opener)

    response = urllib2.urlopen(request)

    return json.loads(response.read())

def api_request_curl(url, data=None, method=None):
    command = ["curl", '-K', '-', url]

    authorization_string = '-u "%s:%s"' % get_credentials()

    config = [authorization_string,
              '--header "Accept: application/json"',
              '--header "Content-Type: application/json"',
              "--silent"]

    if method:
        config.append('--request "%s"' % method)

    if settings.get('https_proxy'):
        config.append(settings.get('https_proxy'))

    data_file = None
    try:
        if data is not None:
            data_file = tempfile.NamedTemporaryFile(delete=False)
            data_file.write(data)
            data_file.close()
            config.append('--data-binary "@%s"' % data_file.name)

        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, _ = process.communicate('\n'.join(config))
        returncode = process.returncode

        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, 'curl')

        return json.loads(response)
    finally:
        if data_file:
            os.unlink(data_file.name)
            data_file.close()

api_request = api_request_curl if ('ssl' not in sys.modules and os.name != 'nt') else api_request_native

class GistCommand(sublime_plugin.TextCommand):
    public = True

    def mode(self):
        return "Public" if self.public else "Private"

    @catch_errors
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
                @catch_errors
                def on_gist_description(description):
                    gist = create_gist(self.public, text, filename, description)
                    print gist
                    if gistify:
                        gistify_view(self.view, gist, filename)

                window.show_input_panel('%s Gist Description (optional):' % self.mode(), '', on_gist_description, None, None)

            window.show_input_panel('%s Gist File Name: (optional):' % self.mode(), filename, on_gist_filename, None, None)

        for region in selections:
            create_gist_with_text(self.view.substr(region))

class GistViewCommand(object):
    """A base class for commands operating on a gistified view"""
    def is_enabled(self):
        return self.view.settings().get("gist_url") is not None

class GistCopyUrl(GistViewCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        sublime.set_clipboard(self.view.settings().get("gist_html_url"))

class GistOpenBrowser(GistViewCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open(self.view.settings().get("gist_html_url"))

class GistUpdateCommand(GistViewCommand, sublime_plugin.TextCommand):
    @catch_errors
    def run(self, edit):
        text = self.view.substr(sublime.Region(0, self.view.size()))
        update_gist(self.view.settings().get("gist_url"), self.view.settings().get("gist_filename"), text)

class GistPrivateCommand(GistCommand):
    public = False

class GistListCommand(sublime_plugin.WindowCommand):
    @catch_errors
    def run(self):
        gists = get_gists()

        gist_names = [gist_title(gist) for gist in gists]
        gist_urls = [gist['url'] for gist in gists]

        @catch_errors
        def open_gist(num):
            if num != -1:
                get_gist(gist_urls[num])

        self.window.show_quick_panel(gist_names, open_gist)
