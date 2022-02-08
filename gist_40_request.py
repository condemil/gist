import contextlib
import json
import urllib.request as urllib

try:
    import sublime
except ImportError:
    from test.stubs import sublime

from gist_20_exceptions import MissingCredentialsException, SimpleHTTPError


def token_auth_string():
    settings = sublime.load_settings('Gist.sublime-settings')
    token = settings.get('token')

    if not token:
        raise MissingCredentialsException()

    return token


def api_request(url, data=None, token=None, https_proxy=None, method=None):
    settings = sublime.load_settings('Gist.sublime-settings')
    request = urllib.Request(url)

    if method:
        request.get_method = lambda: method
    token = token if token is not None else token_auth_string()
    request.add_header('Authorization', 'token ' + token)
    request.add_header('Accept', 'application/json')
    request.add_header('Content-Type', 'application/json')
    # Get around rate-limit features: http://docs2.lfe.io/v3/#conditional-requests
    request.add_header('If-Modified-Since', 'Thu, 05 Jul 2010 15:31:30 GMT')

    if data is not None:
        request.add_data(bytes(data.encode('utf8')))

    https_proxy = (
        https_proxy if https_proxy is not None else settings.get('https_proxy')
    )
    if https_proxy:
        opener = urllib.build_opener(
            urllib.HTTPHandler(),
            urllib.HTTPSHandler(),
            urllib.ProxyHandler({'https': https_proxy}),
        )

        urllib.install_opener(opener)

    try:
        with contextlib.closing(urllib.urlopen(request)) as response:
            if response.code == 204:  # no content
                return None

            return json.loads(response.read().decode('utf8', 'ignore'))

    except urllib.HTTPError as e:
        sublime.error_message("Gist api_request Exception:\n  Method: {};\n  URL: {};\n  Headers: {};\n  Exception: {}".format(str(method), str(url), str(request.headers), str(e)))

        with contextlib.closing(e):
            raise e
