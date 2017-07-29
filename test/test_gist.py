import json
from io import StringIO
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import gist_40_request as gist_request
import gist_60_helpers as gist_helpers
import gist_80 as gist
from gist_20_exceptions import MissingCredentialsException, SimpleHTTPError
from test.stubs import sublime
from test.stubs import github_api


class TestGist(TestCase):
    @patch('gist_80.api_request')
    def test_create_gist(self, mocked_api_request):
        gist.plugin_loaded()
        description = 'some description'
        public = 'some public'
        files = {
            'some_file1.txt': 'some content',
            'some_file2.txt': 'another content'
        }
        api_request_data = json.dumps({
            'description': description,
            'public': public,
            'files': {
                'some_file1.txt': {'content': 'some content'},
                'some_file2.txt': {'content': 'another content'}
            }
        })

        gist.create_gist(public, description, files)
        mocked_api_request.assert_called_with(gist.settings.get('GISTS_URL'), api_request_data)

    def test_create_gist_fail(self):
        description = 'some description'
        public = 'some public'
        failed_files = {
            'some_file1.txt': 'some content',
            'some_file2.txt': ''
        }

        gist.create_gist(public, description, failed_files)
        sublime.error_message.assert_called_with('Gist: Unable to create a Gist with empty content')

    @patch('gist_80.api_request')
    def test_update_gist(self, mocked_api_request):
        gist_url = 'some gist url'
        file_changes = 'some file changes'
        auth_token = 'some auth token'
        https_proxy = 'some https proxy'
        new_description = 'some new description'
        http_method = 'PATCH'

        api_request_data = json.dumps({
            'files': file_changes,
            'description': new_description,
        })

        gist.update_gist(gist_url, file_changes, auth_token, https_proxy, new_description)
        mocked_api_request.assert_called_with(gist_url, api_request_data, token=auth_token, https_proxy=https_proxy,
                                              method=http_method)
        sublime.status_message.assert_called_with('Gist updated')

    @patch('gist_80.set_syntax')
    @patch('gist_80.gistify_view')
    @patch('test.stubs.sublime.Window.new_file')
    @patch('gist_80.api_request')
    def test_open_gist(self, mocked_api_request, mocked_new_file, mocked_gistify_view, mocked_set_syntax):
        gist_url = 'some gist url'
        mocked_api_request.return_value = github_api.GIST_WITH_FILE_CONTENT_AND_TYPE
        view = Mock()
        mocked_new_file.return_value = view

        gist.open_gist(gist_url)
        mocked_api_request.assert_called_with(gist_url)
        self.assertEqual(mocked_new_file.call_count, 2)

        self.assertEqual(mocked_gistify_view.call_count, 2)
        self.assertEqual(mocked_gistify_view.call_args_list[0][0][0], view)
        self.assertEqual(mocked_gistify_view.call_args_list[0][0][1], github_api.GIST_WITH_FILE_CONTENT_AND_TYPE)
        self.assertEqual(mocked_gistify_view.call_args_list[0][0][2], 'some_file1.txt')

        self.assertEqual(view.run_command.call_count, 4)
        self.assertEqual(len(view.run_command.call_args_list[0][0]), 2)
        self.assertEqual(view.run_command.call_args_list[0][0][0], 'append')
        self.assertEqual(view.run_command.call_args_list[0][0][1], {'characters': 'some content'})

        self.assertEqual(len(view.run_command.call_args_list[1][0]), 1)
        self.assertEqual(view.run_command.call_args_list[1][0][0], 'save')

        self.assertEqual(view.set_scratch.call_count, 2)
        view.set_scratch.assert_called_with(True)

        self.assertEqual(view.retarget.call_count, 2)

        self.assertEqual(view.settings.return_value.set.call_count, 2)
        view.settings.return_value.set.assert_called_with('do-update', False)

        self.assertEqual(mocked_set_syntax.call_count, 2)
        self.assertEqual(mocked_set_syntax.call_args_list[0][0][0], view)
        self.assertEqual(mocked_set_syntax.call_args_list[0][0][1],
                         github_api.GIST_WITH_FILE_CONTENT_AND_TYPE['files']['some_file1.txt'])

    @patch('test.stubs.sublime.Window.active_view')
    @patch('gist_80.api_request')
    def test_insert_gist(self, mocked_api_request, mocked_active_view):
        gist_url = 'some gist url'
        mocked_api_request.return_value = github_api.GIST_WITH_FILE_CONTENT_AND_TYPE
        view = Mock()
        mocked_active_view.return_value = view

        view.settings.return_value.get.return_value = False  # auto_indent is False
        gist.insert_gist(gist_url)
        self.assertEqual(view.settings.return_value.set.call_count, 0)
        self.assertEqual(view.run_command.call_count, 3)
        self.assertEqual(view.run_command.call_args_list[0][0][0], 'insert')
        self.assertEqual(
            view.run_command.call_args_list[0][0][1],
            {'characters': github_api.GIST_WITH_FILE_CONTENT_AND_TYPE['files']['some_file1.txt']['content']}
        )

        view.settings.return_value.get.return_value = True  # auto_indent is True
        gist.insert_gist(gist_url)
        self.assertEqual(view.settings.return_value.set.call_count, 6)

    @patch('test.stubs.sublime.Window.active_view')
    @patch('gist_80.api_request')
    def test_insert_gist_embed(self, mocked_api_request, mocked_active_view):
        gist_url = 'some gist url'
        mocked_api_request.return_value = github_api.GIST_WITH_RAW_URL
        view = Mock()
        mocked_active_view.return_value = view

        gist.insert_gist_embed(gist_url)
        self.assertEqual(view.run_command.call_count, 2)
        self.assertEqual(view.run_command.call_args_list[0][0][0], 'insert')
        self.assertEqual(view.run_command.call_args_list[0][0][1],
                         {'characters': '<script src="some raw url"></script>'})
        self.assertEqual(view.run_command.call_args_list[1][0][0], 'insert')
        self.assertEqual(view.run_command.call_args_list[1][0][1],
                         {'characters': '<script src="some another raw url"></script>'})

    @patch('test.stubs.sublime.Window.open_file')
    @patch('gist_80.shutil.copy')
    @patch('gist_80.traceback.print_exc')
    def test_catch_errors(self, mocked_print_exc, mocked_copy, mocked_open_file):
        gist.catch_errors(lambda: exec('raise(Exception())'))()
        self.assertEqual(mocked_print_exc.call_count, 1)
        sublime.error_message.assert_called_with('Gist: unknown error (please, report a bug!)')

        sublime.error_message.reset_mock()
        gist.catch_errors(lambda: exec('raise(gist.MissingCredentialsException())'))()
        sublime.error_message.assert_called_with('Gist: GitHub token isn\'t provided in Gist.sublime-settings file. '
                                                 'All other authorization methods are deprecated.')
        mocked_copy.assert_called_with('Gist/Gist.sublime-settings', 'User/Gist.sublime-settings')
        mocked_open_file.assert_called_with('User/Gist.sublime-settings')

    @patch('gist_60_helpers.gist_title')
    def test_gistify_view(self, mocked_gist_title):
        mocked_gist_title.return_value = ['some gist title']
        view = sublime.View()
        gist_filename = 'some filename'
        gist = {
            'html_url': 'some html url',
            'description': 'some description',
            'url': 'some url'
        }

        gist_helpers.gistify_view(view, gist, gist_filename)

        self.assertEqual(view.file_name(), 'some filename')
        self.assertEqual(view.settings().get('gist_html_url'), 'some html url')
        self.assertEqual(view.settings().get('gist_description'), 'some description')
        self.assertEqual(view.settings().get('gist_url'), 'some url')
        self.assertEqual(view.settings().get('gist_filename'), 'some filename')
        self.assertEqual(view._status.get('Gist'), 'Gist: some gist title')

        view = sublime.View()
        gist_filename = 'some another filename'
        view.set_name('some view filename')

        gist_helpers.gistify_view(view, gist, gist_filename)

        self.assertEqual(view._status.get('Gist'), 'Gist: some gist title (some another filename)')

    def test_ungistify_view(self):
        view = sublime.View()

        view.settings().set('gist_html_url', 'some html url')
        view.settings().set('gist_description', 'some description')
        view.settings().set('gist_url', 'some url')
        view.settings().set('gist_filename', 'some filename')
        view.set_status('Gist', 'some status')

        gist_helpers.ungistify_view(view)

        self.assertIsNone(view.settings().get('gist_html_url'))
        self.assertIsNone(view.settings().get('gist_description'))
        self.assertIsNone(view.settings().get('gist_url'))
        self.assertIsNone(view.settings().get('gist_filename'))
        self.assertTrue('Gist' not in view._status)

    def test_gists_filter(self):
        gist.plugin_loaded()
        sublime.settings_storage['Gist.sublime-settings'].set('gist_prefix', 'some_prefix:')
        sublime.settings_storage['Gist.sublime-settings'].set('gist_tag', 'some_tag')

        all_gists = [
            {'description': 'some gist 1', 'files': {}},
            {'description': 'some_prefix:some gist 2', 'files': {'some_test.sh': {}}},
            {'description': 'some_prefix:some gist 3 #some_tag', 'files': {'some_test2.sh': {}}},
        ]

        gists, gists_names = gist_helpers.gists_filter(all_gists)

        self.assertEqual(gists, [{'files': {'some_test2.sh': {}}, 'description': 'some_prefix:some gist 3 #some_tag'}])
        self.assertEqual(gists_names, [['some gist 3']])

    @patch('gist_80.os.name', 'nt')
    def test_set_syntax(self):
        view = Mock()

        gist_helpers.set_syntax(view, {})
        self.assertEqual(view.set_syntax_file.call_count, 0)

        gist_helpers.set_syntax(view, {'language': None})
        self.assertEqual(view.set_syntax_file.call_count, 0)

        gist_helpers.set_syntax(view, {'language': 'C'})
        view.set_syntax_file.assert_called_with('Packages/C++/C.tmLanguage')

        gist_helpers.set_syntax(view, {'language': 'Something'})
        view.set_syntax_file.assert_called_with('Packages/Something/Something.tmLanguage')

    def test_token_auth_string(self):
        self.assertRaises(MissingCredentialsException, gist_request.token_auth_string)

        gist.plugin_loaded()
        sublime.settings_storage['Gist.sublime-settings'].set('token', 'some token')

        self.assertEqual(gist_request.token_auth_string(), 'some token')

    @patch('gist_40_request.urllib')
    def test_api_request(self, mocked_urllib):
        url = 'https://url.test'
        data = 'some data'
        token = 'some token'
        https_proxy = 'some https proxy'
        method = 'some method'

        mocked_urllib.urlopen().read.return_value = b'{"some": "response"}'

        result = gist_request.api_request(url, data, token, https_proxy, method)

        mocked_urllib.Request.assert_called_with(url)

        self.assertEqual(mocked_urllib.Request().add_header.call_count, 3)
        self.assertEqual(mocked_urllib.Request().add_header.call_args_list[0][0][0], 'Authorization')
        self.assertEqual(mocked_urllib.Request().add_header.call_args_list[0][0][1], 'token some token')
        self.assertEqual(mocked_urllib.Request().add_header.call_args_list[1][0][0], 'Accept')
        self.assertEqual(mocked_urllib.Request().add_header.call_args_list[1][0][1], 'application/json')
        self.assertEqual(mocked_urllib.Request().add_header.call_args_list[2][0][0], 'Content-Type')
        self.assertEqual(mocked_urllib.Request().add_header.call_args_list[2][0][1], 'application/json')

        mocked_urllib.Request().add_data.assert_called_with(b'some data')

        mocked_urllib.build_opener.assert_called_with(mocked_urllib.HTTPHandler(), mocked_urllib.HTTPSHandler(),
                                                      mocked_urllib.ProxyHandler())

        mocked_urllib.install_opener.assert_called_with(mocked_urllib.build_opener())

        self.assertEqual(result, {'some': 'response'})

        # no content flow, do nothing
        mocked_urllib.urlopen().code = 204

        result = gist_request.api_request(url, data, token, https_proxy, method)

        self.assertIsNone(result)

        # HTTPException flow
        mocked_urllib.HTTPError = HTTPError
        mocked_urllib.urlopen.side_effect = HTTPError(url, 'some code', 'some msg', 'some headers',
                                                      StringIO('some error data'))

        self.assertRaises(SimpleHTTPError, gist_request.api_request, url, data, token)
