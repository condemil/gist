import sublime

global settings
global DEFAULT_CREATE_PUBLIC_VALUE
global DEFAULT_USE_PROXY_VALUE
global GISTS_URL
global USER_GISTS_URL
global ORGS_URL
global ORG_MEMBERS_URL
global STARRED


def initialize_globals():
    '''
    Initialize globals. In Sublime Text 3 this can no longer me done in
    the module scope.

    See "Restricted API Usage at Startup" in the following document.
    http://www.sublimetext.com/docs/3/porting_guide.html
    '''
    global settings
    global DEFAULT_CREATE_PUBLIC_VALUE
    global DEFAULT_USE_PROXY_VALUE
    global GISTS_URL
    global USER_GISTS_URL
    global ORGS_URL
    global ORG_MEMBERS_URL
    global STARRED

    settings = sublime.load_settings('Gist.sublime-settings')
    DEFAULT_CREATE_PUBLIC_VALUE = 'false'
    DEFAULT_USE_PROXY_VALUE = 'false'
    GISTS_URL = 'https://api.github.com/gists'
    USER_GISTS_URL = 'https://api.github.com/users/%s/gists'
    ORGS_URL = 'https://api.github.com/user/orgs'
    ORG_MEMBERS_URL = 'https://api.github.com/orgs/%s/members'
    STARRED = '/starred'

    #Enterprise support:
    if settings.get('enterprise'):
        GISTS_URL = settings.get('url')
        if not GISTS_URL:
            raise MissingCredentialsException()
        GISTS_URL += '/api/v3/gists'

    #Per page support (max 100)
    if settings.get('max_gists'):
        if settings.get('max_gists') <= 100:
            MAX_GISTS = '?per_page=%d' % settings.get('max_gists')
            GISTS_URL += MAX_GISTS
            USER_GISTS_URL += MAX_GISTS
        else:
            settings.set('max_gists', 100)
            sublime.status_message("Gist: GitHub API does not support a value of higher than 100")
