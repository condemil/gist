import sublime
import sys

PY3 = sys.version >= '3'

if PY3:
    from .request import *
else:
    from request import *


loaded_settings = None
get = None
set = None

GISTS_URL          = 'https://api.github.com/gists'
USER_GISTS_URL     = 'https://api.github.com/users/%s/gists'
STARRED_GISTS_URL  = 'https://api.github.com/gists/starred'
ORGS_URL           = 'https://api.github.com/user/orgs'
ORG_MEMBERS_URL    = 'https://api.github.com/orgs/%s/members'


def load():
    global GISTS_URL
    global USER_GISTS_URL
    global STARRED_GISTS_URL
    global ORGS_URL
    global ORG_MEMBERS_URL
    global loaded_settings
    global get
    global set

    loaded_settings = sublime.load_settings('Gist.sublime-settings')
    get = loaded_settings.get
    set = loaded_settings.set

    # Enterprise support
    if loaded_settings.get('enterprise'):
        GISTS_URL = loaded_settings.get('url')
        if not GISTS_URL:
            raise MissingCredentialsException()
        GISTS_URL += '/api/v3/gists'

    # Per page support (max 100)
    if loaded_settings.get('max_gists'):
        if loaded_settings.get('max_gists') <= 100:
            MAX_GISTS         = '?per_page=%d' % loaded_settings.get('max_gists')
            GISTS_URL         += MAX_GISTS
            USER_GISTS_URL    += MAX_GISTS
            STARRED_GISTS_URL += MAX_GISTS
        else:
            loaded_settings.set('max_gists', 100)
            sublime.status_message("Gist: GitHub API does not support a value of higher than 100")

