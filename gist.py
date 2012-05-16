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
import contextlib
import shutil

DEFAULT_CREATE_PUBLIC_VALUE = 'false'
DEFAULT_USE_PROXY_VALUE = 'false'
settings = sublime.load_settings('Gist.sublime-settings')
GISTS_URL = 'https://api.github.com/gists'

class MissingCredentialsException(Exception):
    pass

class CurlNotFoundException(Exception):
    pass

class SimpleHTTPError(Exception):
    def __init__(self, code, response):
        self.code = code
        self.response = response

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

        PtrSecKeychainAttributeList = POINTER(SecKeychainAttributeList)

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

                attrlist_ptr = PtrSecKeychainAttributeList()
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
                        lib_security.SecKeychainItemFreeAttributesAndData(attrlist_ptr, password_buf)

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
            user_settings_path = os.path.join(sublime.packages_path(), 'User', 'Gist.sublime-settings')
            if not os.path.exists(user_settings_path):
                default_settings_path = os.path.join(sublime.packages_path(), 'Gist', 'Gist.sublime-settings')
                shutil.copy(default_settings_path, user_settings_path)
            sublime.active_window().run_command("open_file", {"file": user_settings_path})
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
        except SimpleHTTPError as err:
            msg = "Gist: GitHub returned error %d" % err.code
            try:
                response_json = json.loads(err.response)
                response_msg = response_json.get('message')
                if response_msg:
                    msg += ": " + response_msg
            except ValueError:
                pass
            sublime.error_message(msg)
        except:
            traceback.print_exc()
            sublime.error_message("Gist: unknown error (please, report a bug!)")
    return _fn

def create_gist(public, description, files):
    file_data = dict((filename, {'content': text}) for filename, text in files.items())
    data = json.dumps({'description': description, 'public': public, 'files': file_data})
    gist = api_request(GISTS_URL, data)
    return gist

def update_gist(gist_url, file_changes, new_description=None):
    request = {'files': file_changes}
    if new_description is not None:
        request['description'] = new_description
    data = json.dumps(request)
    result = api_request(gist_url, data, method="PATCH")
    return result

def gistify_view(view, gist, gist_filename):
    statusline_string = "Gist: " + gist_title(gist)

    if not view.file_name():
        view.set_name(gist_filename)
    elif os.path.basename(view.file_name()) != gist_filename:
        statusline_string = "%s (%s)" % (statusline_string, gist_filename)

    view.settings().set('gist_html_url', gist["html_url"])
    view.settings().set('gist_description', gist['description'])
    view.settings().set('gist_url', gist["url"])
    view.settings().set('gist_filename', gist_filename)
    view.set_status("Gist", statusline_string)

def ungistify_view(view):
    view.settings().erase('gist_html_url')
    view.settings().erase('gist_description')
    view.settings().erase('gist_url')
    view.settings().erase('gist_filename')
    view.erase_status("Gist")

def open_gist(gist_url):
    gist = api_request(gist_url)
    files = sorted(gist['files'].keys())
    for gist_filename in files:
        view = sublime.active_window().new_file()

        gistify_view(view, gist, gist_filename)

        edit = view.begin_edit()
        view.insert(edit, 0, gist['files'][gist_filename]['content'])
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

    try:
        with contextlib.closing(urllib2.urlopen(request)) as response:
            if response.code == 204: # No Content
                return None
            else:
                return json.loads(response.read())
    except urllib2.HTTPError as err:
        with contextlib.closing(err):
            raise SimpleHTTPError(err.code, err.read())

@contextlib.contextmanager
def named_tempfile():
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    try:
        yield tmpfile
    finally:
        tmpfile.close()
        os.unlink(tmpfile.name)

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

    with named_tempfile() as header_output_file:
        config.append('--dump-header "%s"' % header_output_file.name)
        header_output_file.close()
        with named_tempfile() as data_file:
            if data is not None:
                data_file.write(data)
                data_file.close()
                config.append('--data-binary "@%s"' % data_file.name)

            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            response, _ = process.communicate('\n'.join(config))
            returncode = process.returncode

            if returncode != 0:
                raise subprocess.CalledProcessError(returncode, 'curl')

            with open(header_output_file.name, "r") as headers:
                _, responsecode, message = headers.readline().split(None, 2)
                responsecode = int(responsecode)

                if responsecode == 204: # No Content
                    return None
                elif 200 <= responsecode < 300:
                    return json.loads(response)
                else:
                    raise SimpleHTTPError(responsecode, response)

api_request = api_request_curl if ('ssl' not in sys.modules and os.name != 'nt') else api_request_native

class GistCommand(sublime_plugin.TextCommand):
    public = True

    def mode(self):
        return "Public" if self.public else "Private"

    @catch_errors
    def run(self, edit):
        get_credentials()
        regions = [region for region in self.view.sel() if not region.empty()]

        if len(regions) == 0:
            regions = [sublime.Region(0, self.view.size())]
            gistify = True
        else:
            gistify = False

        region_data = [self.view.substr(region) for region in regions]

        window = self.view.window()

        def on_gist_description(description):
            filename = os.path.basename(self.view.file_name() if self.view.file_name() else '')

            @catch_errors
            def on_gist_filename(filename):
                # We need to figure out the filenames. Right now, the following logic is used:
                #   If there's only 1 selection, just pass whatever the user typed to Github. It'll rename empty files for us.
                #   If there are multiple selections and user entered a filename, rename the files from foo.js to
                #       foo (1).js, foo (2).js, etc.
                #   If there are multiple selections and user didn't enter anything, post the files as
                #       $SyntaxName 1, $SyntaxName 2, etc.
                if len(region_data) == 1:
                    gist_data = {filename: region_data[0]}
                else:
                    if filename:
                        (namepart, extpart) = os.path.splitext(filename)
                        make_filename = lambda num: "%s (%d)%s" % (namepart, num, extpart)
                    else:
                        syntax_name, _ = os.path.splitext(os.path.basename(self.view.settings().get('syntax')))
                        make_filename = lambda num: "%s %d" % (syntax_name, num)
                    gist_data = dict((make_filename(idx), data) for idx, data in enumerate(region_data, 1))

                gist = create_gist(self.public, description, gist_data)

                gist_html_url = gist['html_url']
                sublime.set_clipboard(gist_html_url)
                sublime.status_message("%s Gist: %s" % (self.mode(), gist_html_url))

                if gistify:
                    gistify_view(self.view, gist, gist['files'].keys()[0])
                else:
                    open_gist(gist['url'])

            window.show_input_panel('Gist File Name: (optional):', filename, on_gist_filename, None, None)

        window.show_input_panel("Gist Description (optional):", '', on_gist_description, None, None)

class GistViewCommand(object):
    """A base class for commands operating on a gistified view"""
    def is_enabled(self):
        return self.gist_url() is not None

    def gist_url(self):
        return self.view.settings().get("gist_url")

    def gist_html_url(self):
        return self.view.settings().get("gist_html_url")

    def gist_filename(self):
        return self.view.settings().get("gist_filename")

    def gist_description(self):
        return self.view.settings().get("gist_description")

class GistCopyUrl(GistViewCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        sublime.set_clipboard(self.gist_html_url())

class GistOpenBrowser(GistViewCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open(self.gist_html_url())

class GistRenameFileCommand(GistViewCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        old_filename = self.gist_filename()

        @catch_errors
        def on_filename(filename):
            if filename and filename != old_filename:
                text = self.view.substr(sublime.Region(0, self.view.size()))
                file_changes = {old_filename: {'filename': filename, 'content': text}}
                new_gist = update_gist(self.gist_url(), file_changes)
                gistify_view(self.view, new_gist, filename)
                sublime.status_message('Gist file renamed')

        self.view.window().show_input_panel('New File Name:', old_filename, on_filename, None, None)

class GistChangeDescriptionCommand(GistViewCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        @catch_errors
        def on_gist_description(description):
            if description and description != self.gist_description():
                gist_url = self.gist_url()
                new_gist = update_gist(gist_url, {}, description)
                for window in sublime.windows():
                    for view in window.views():
                        if view.settings().get('gist_url') == gist_url:
                            gistify_view(view, new_gist, view.settings().get('gist_filename'))
                sublime.status_message('Gist description changed')

        self.view.window().show_input_panel('New Description:', self.gist_description() or '', on_gist_description, None, None)

class GistUpdateFileCommand(GistViewCommand, sublime_plugin.TextCommand):
    @catch_errors
    def run(self, edit):
        text = self.view.substr(sublime.Region(0, self.view.size()))
        changes = {self.gist_filename(): {'content': text}}
        update_gist(self.gist_url(), changes)
        sublime.status_message("Gist updated")

class GistDeleteFileCommand(GistViewCommand, sublime_plugin.TextCommand):
    @catch_errors
    def run(self, edit):
        changes = {self.gist_filename(): None}
        update_gist(self.gist_url(), changes)
        ungistify_view(self.view)
        sublime.status_message("Gist file deleted")

class GistDeleteCommand(GistViewCommand, sublime_plugin.TextCommand):
    @catch_errors
    def run(self, edit):
        gist_url = self.gist_url()
        api_request(gist_url, method='DELETE')
        for window in sublime.windows():
            for view in window.views():
                if view.settings().get("gist_url") == gist_url:
                    ungistify_view(view)
        sublime.status_message("Gist deleted")

class GistPrivateCommand(GistCommand):
    public = False

class GistListCommandBase(object):
    @catch_errors
    def run(self, *args):
        gists = get_gists()
        gist_names = [gist_title(gist) for gist in gists]

        def on_gist_num(num):
            if num != -1:
                self.handle_gist(gists[num])

        self.get_window().show_quick_panel(gist_names, on_gist_num)

class GistListCommand(GistListCommandBase, sublime_plugin.WindowCommand):
    @catch_errors
    def handle_gist(self, gist):
        open_gist(gist['url'])

    def get_window(self):
        return self.window

class GistAddFileCommand(GistListCommandBase, sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.settings().get('gist_url') is None

    def handle_gist(self, gist):
        @catch_errors
        def on_filename(filename):
            if filename:
                text = self.view.substr(sublime.Region(0, self.view.size()))
                changes = {filename: {'content': text}}
                new_gist = update_gist(gist['url'], changes)
                gistify_view(self.view, new_gist, filename)
                sublime.status_message("File added to Gist")

        filename = os.path.basename(self.view.file_name() if self.view.file_name() else '')
        self.view.window().show_input_panel('File Name:', filename, on_filename, None, None)

    def get_window(self):
        return self.view.window()
