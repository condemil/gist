from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import gitio
from test.stubs import sublime

GITIO_TEST_URL = 'https://some_url.test/'
GITIO_TEST_DATA = b'url=https%3A%2F%2Fsome_url.test%2F'

TEST_GITHUB_URL = 'https://github.test/some/url'
TEST_GITIO_SHORT_URL = 'https://git.io.test/some/short/url'


class TestGist(TestCase):
    def test_gitio_command(self):
        gist_gitio = gitio.GitioCommand()
        gist_gitio.run(edit=None)
        gist_gitio.view.window().show_input_panel.assert_called_with('GitHub URL:', '', gist_gitio.on_done, None, None)

        with patch('gitio.gitio', return_value=(None, TEST_GITIO_SHORT_URL)) as mocked_git_io:
            gist_gitio.on_done(TEST_GITHUB_URL)
            mocked_git_io.assert_called_with(TEST_GITHUB_URL)
            sublime.set_clipboard.assert_called_with(TEST_GITIO_SHORT_URL)
            sublime.status_message.assert_called_with('Gist: Copied to Clipboard! ' + TEST_GITIO_SHORT_URL)

        with patch('gitio.gitio', return_value=('Some error', None)) as mocked_git_io:
            gist_gitio.on_done(TEST_GITHUB_URL)
            mocked_git_io.assert_called_with(TEST_GITHUB_URL)
            sublime.error_message.assert_called_with('Some error')
            gist_gitio.view.window().show_input_panel.assert_called_with(
                'GitHub URL:', TEST_GITHUB_URL, gist_gitio.on_done, None, None)

    def test_git_io(self):
        response = Mock()
        response.status = 200
        response.read.return_value = b'some_data'
        with patch('gitio.urlopen', return_value=response) as mocked_urlopen:
            result = gitio.gitio(GITIO_TEST_URL)
            mocked_urlopen.assert_called_with(gitio.gitio_url, GITIO_TEST_DATA)
            self.assertEqual(result, (None, 'https://git.io/some_data'))

    def test_git_io_error_status_response(self):
        error_status_response = Mock()
        error_status_response.status = 500
        error_status_response.read.return_value = b'some_error'
        with patch('gitio.urlopen', return_value=error_status_response) as mocked_urlopen:
            result = gitio.gitio(GITIO_TEST_URL)
            mocked_urlopen.assert_called_with(gitio.gitio_url, GITIO_TEST_DATA)
            self.assertEqual(result, ('some_error', None))

    def test_git_io_http_error_response(self):
        with patch('gitio.urlopen') as mocked_urlopen:
            http_error_response = Mock()
            http_error_response.read.return_value = b'some_http_error'
            mocked_urlopen.side_effect = HTTPError(None, None, None, None, http_error_response)
            result = gitio.gitio(GITIO_TEST_URL)
            mocked_urlopen.assert_called_with(gitio.gitio_url, GITIO_TEST_DATA)
            self.assertEqual(result, ('some_http_error', None))

    def test_git_io_url_error_response(self):
        with patch('gitio.urlopen') as mocked_urlopen:
            url_error_response = Mock()
            mocked_urlopen.side_effect = URLError(None, url_error_response)
            result = gitio.gitio(GITIO_TEST_URL)
            mocked_urlopen.assert_called_with(gitio.gitio_url, GITIO_TEST_DATA)
            self.assertEqual(result, ('Gist: Error contacting git.io', None))
