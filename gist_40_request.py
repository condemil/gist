import contextlib
import json
import os
import tempfile
import urllib.request as urllib

try:
    import sublime
except ImportError:
    from test.stubs import sublime

from gist_20_exceptions import MissingCredentialsException


def token_auth_string():
    settings = sublime.load_settings('Gist.sublime-settings')
    token = settings.get('token')

    if not token:
        raise MissingCredentialsException()

    return token


def cache_request(etag, content):
    target = os.path.join(tempfile.gettempdir(), "{}.json".format(etag.strip('"')))
    with tempfile.NamedTemporaryFile(mode='wb',delete=False) as temp_file:
        os.rename(temp_file.name, target)
        temp_file.write(str.encode(content))
        temp_file.flush()

def api_request(url, data=None, token=None, https_proxy=None, method=None, since_date=False):
    settings = sublime.load_settings('Gist.sublime-settings')
    request = urllib.Request(url)

    if method:
        request.get_method = lambda: method
    token = token if token is not None else token_auth_string()
    request.add_header('Authorization', 'token ' + token)
    request.add_header('Accept', 'application/json')
    request.add_header('Content-Type', 'application/json')
    if since_date:
        request.add_header('If-Modified-Since', since_date)

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

            etag = response.headers['ETag']
            content = response.read().decode('utf8', 'ignore')
            if etag:
                cache_request(etag, content)

            return json.loads(content)

    except Exception as e:
        try:
            # Make sure we can iterate this error.
            iter(e)
            httpcode = str(e.code)

            # If 304 is status code, let's see if we have a cached version, or refetch.
            if (httpcode == '304') and ("ETag" in e.headers):

                # Get path to cached version.
                cached = os.path.join(tempfile.gettempdir(), "{}.json".format(e.headers['ETag'].strip('"')))
                try:
                    # Attempt to open and return cached data.
                    with open(cached, 'r') as result:
                        data = json.load(result)
                        data['cached'] = True
                        return data
                except:

                    # Re-fetch gist, but get around rate-limit features:
                    # http://docs2.lfe.io/v3/#conditional-requests
                    return api_request(url, data, token, https_proxy, method, 'Thu, 05 Jul 2010 15:31:30 GMT')
        except:
            pass

        with contextlib.closing(e):
            raise e
