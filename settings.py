import sublime

from .exceptions import MissingCredentialsException


class Settings(object):
    def __init__(self):
        self.loaded_settings = sublime.load_settings('Gist.sublime-settings')

        self.GISTS_URL = 'https://api.github.com/gists'
        self.USER_GISTS_URL = 'https://api.github.com/users/%s/gists'
        self.STARRED_GISTS_URL = 'https://api.github.com/gists/starred'
        self.ORGS_URL = 'https://api.github.com/user/orgs'
        self.ORG_MEMBERS_URL = 'https://api.github.com/orgs/%s/members'

        self.get = self.loaded_settings.get
        self.set = self.loaded_settings.set
        self.loaded_settings.add_on_change('reload', lambda: self.load())
        self.load()

    def load(self):
        # Enterprise support
        if self.get('enterprise'):
            self.GISTS_URL = self.get('url')
            if not self.GISTS_URL:
                raise MissingCredentialsException()
            self.GISTS_URL += '/api/v3/gists'

        # Per page support (max 100)
        if self.get('max_gists'):
            if self.get('max_gists') <= 100:
                max_gists = '?per_page=%d' % self.get('max_gists')
                self.GISTS_URL += max_gists
                self.USER_GISTS_URL += max_gists
                self.STARRED_GISTS_URL += max_gists
            else:
                self.set('max_gists', 100)
                sublime.status_message("Gist: GitHub API does not support a value of higher than 100")

settings = Settings()
