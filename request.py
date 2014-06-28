# -*- coding: utf-8 -*-

import sublime
import os
import sys
import json
import contextlib
import traceback
import subprocess
import tempfile

PY3 = sys.version > '3'

if PY3:
    import urllib.request as urllib
    from .settings import *
else:
    import urllib2 as urllib
    from settings import *


class SimpleHTTPError(Exception):
    def __init__(self, code, response):
        self.code = code
        self.response = response


class MissingCredentialsException(Exception):
    pass


def token_auth_string():
    settings = sublime.load_settings('Gist.sublime-settings')
    token = settings.get('token')

    if not token:
        raise MissingCredentialsException()

    return token


def api_request_native(url, data=None, token=None, https_proxy=None, method=None):
    request = urllib.Request(url)
    # print('API request url:', request.get_full_url())
    if method:
        request.get_method = lambda: method
    token = token if token != None else token_auth_string()
    request.add_header('Authorization', 'token ' + token)
    request.add_header('Accept', 'application/json')
    request.add_header('Content-Type', 'application/json')

    if data is not None:
        request.add_data(bytes(data.encode('utf8')))

    # print('API request data:', request.get_data())
    # print('API request header:', request.header_items())
    https_proxy = https_proxy if https_proxy != None else settings.get('https_proxy')
    if https_proxy:
        opener = urllib.build_opener(urllib.HTTPHandler(), urllib.HTTPSHandler(),
                                     urllib.ProxyHandler({'https': https_proxy}))

        urllib.install_opener(opener)

    try:
        with contextlib.closing(urllib.urlopen(request)) as response:
            if response.code == 204:  # No Content
                return None
            else:
                return json.loads(response.read().decode('utf8', 'ignore'))

    except urllib.HTTPError as err:
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


def api_request_curl(url, data=None, token=None, https_proxy=None, method=None):
    command = ["curl", '-K', '-', url]
    token = token if token != None else token_auth_string()
    config = ['--header "Authorization: token ' + token + '"',
              '--header "Accept: application/json"',
              '--header "Content-Type: application/json"',
              "--silent"]

    if method:
        config.append('--request "%s"' % method)

    https_proxy = https_proxy if https_proxy != None else settings.get('https_proxy')
    if https_proxy:
        config.append(https_proxy)

    with named_tempfile() as header_output_file:
        config.append('--dump-header "%s"' % header_output_file.name)
        header_output_file.close()
        with named_tempfile() as data_file:
            if data is not None:
                data_file.write(bytes(data.encode('utf8')))
                data_file.close()
                config.append('--data-binary "@%s"' % data_file.name)

            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            response, _ = process.communicate(bytes('\n'.join(config).encode('utf8')))
            returncode = process.returncode

            if returncode != 0:
                raise subprocess.CalledProcessError(returncode, 'curl')

            with open(header_output_file.name, "r") as headers:
                _, responsecode, message = headers.readline().split(None, 2)
                responsecode = int(responsecode)

                if responsecode == 204:  # No Content
                    return None
                elif 200 <= responsecode < 300 or responsecode == 100:  # Continue
                    return json.loads(response.decode('utf8', 'ignore'))
                else:
                    raise SimpleHTTPError(responsecode, response)



def api_request(url, data=None, token=None, https_proxy=None, method=None):
    try:
        if ('ssl' not in sys.modules and os.name != 'nt'):
            return api_request_curl(url, data, token, https_proxy, method)
        else:
            return api_request_native(url, data, token, https_proxy, method)
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
            response_json = json.loads(err.response.decode('utf8'))
            response_msg = response_json.get('message')
            if response_msg:
                msg += ": " + response_msg
        except ValueError:
            pass
        sublime.error_message(msg)
