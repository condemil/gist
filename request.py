import contextlib
import json

import sublime
import urllib.request as urllib


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


def api_request(url, data=None, token=None, https_proxy=None, method=None):
    settings = sublime.load_settings('Gist.sublime-settings')
    request = urllib.Request(url)
    # print('API request url:', request.get_full_url())
    if method:
        request.get_method = lambda: method
    token = token if token is not None else token_auth_string()
    request.add_header('Authorization', 'token ' + token)
    request.add_header('Accept', 'application/json')
    request.add_header('Content-Type', 'application/json')

    if data is not None:
        request.add_data(bytes(data.encode('utf8')))

    # print('API request data:', request.get_data())
    # print('API request header:', request.header_items())
    https_proxy = https_proxy if https_proxy is not None else settings.get('https_proxy')
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
