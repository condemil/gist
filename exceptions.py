class MissingCredentialsException(Exception):
    pass


class SimpleHTTPError(Exception):
    def __init__(self, code, response):
        self.code = code
        self.response = response
