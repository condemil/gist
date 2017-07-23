from threading import Lock
from unittest import TestCase
from unittest.mock import Mock, patch

import gist
import git_io
from test.stubs import github_api, sublime

DEFAULT_GISTS_URL = 'https://api.github.com/gists?per_page=100'
DEFAULT_STARRED_GISTS_URL = 'https://api.github.com/gists/starred?per_page=100'
DEFAULT_ORGS_URL = 'https://api.github.com/user/orgs'

TEST_GITHUB_URL = 'https://github.test/some/url'
TEST_GITIO_SHORT_URL = 'https://git.io.test/some/short/url'
TEST_GIST_URL = 'https://api.github.test/gists/45681ac0a18a46b487620c6836e1510c'

TEST_ORG_MEMBERS_URL = 'https://api.github.com/orgs/0/members'
TEST_ORG_GIST_URL = 'https://api.github.com/users/some_organization/gists?per_page=100'
TEST_MEMBERS_URL = 'https://api.github.com/users/0/gists?per_page=100'


class TestGistCommand(TestCase):
    def test_gist_copy_url(self,):
        gist_copy_url = gist.GistCopyUrl()
        gist_copy_url.run(edit=None)
        sublime.set_clipboard.assert_called_with(None)

    @patch('gist.webbrowser')
    def test_gist_open_browser(self, patch_gist_webbrowser):
        gist_open_browser = gist.GistOpenBrowser()
        gist_open_browser.run(edit=None)
        patch_gist_webbrowser.open.assert_called_with(None)

    def test_gist_gitio(self):
        gist_gitio = git_io.GistGitioCommand()
        gist_gitio.run(edit=None)
        gist_gitio.view.window().show_input_panel.assert_called_with('GitHub URL:', '', gist_gitio.on_done, None, None)

        with patch('git_io.git_io', return_value=(None, TEST_GITIO_SHORT_URL)) as mocked_git_io:
            gist_gitio.on_done(TEST_GITHUB_URL)
            mocked_git_io.assert_called_with(TEST_GITHUB_URL)
            sublime.set_clipboard.assert_called_with(TEST_GITIO_SHORT_URL)
            sublime.status_message.assert_called_with('Gist: Copied to Clipboard! ' + TEST_GITIO_SHORT_URL)

        with patch('git_io.git_io', return_value=('Some error', None)) as mocked_git_io:
            gist_gitio.on_done(TEST_GITHUB_URL)
            mocked_git_io.assert_called_with(TEST_GITHUB_URL)
            sublime.error_message.assert_called_with('Some error')
            gist_gitio.view.window().show_input_panel.assert_called_with(
                'GitHub URL:', TEST_GITHUB_URL, gist_gitio.on_done, None, None)

    @patch('gist.api_request')
    def test_gist_list_command_base(self, mocked_api_request):
        gist.plugin_loaded()
        mocked_api_request.side_effect = [github_api.GIST_STARRED_LIST, github_api.GIST_LIST]
        gist.settings.set('include_users', ['some user'])
        gist.settings.set('include_orgs', ['some org'])
        gist_list_base = gist.GistListCommandBase()

        with patch('gist.GistListCommandBase.get_window') as mocked_get_window:
            mocked_window = Mock()
            mocked_get_window.return_value = mocked_window
            gist_list_base.run()
            self.assertEqual(mocked_api_request.call_count, 2)
            self.assertEqual(mocked_api_request.mock_calls[0][1], (DEFAULT_STARRED_GISTS_URL,))
            self.assertEqual(mocked_api_request.mock_calls[1][1], (DEFAULT_GISTS_URL,))
            self.assertEqual(mocked_window.show_quick_panel.call_args[0][0],
                             [['> some org'], ['> some user'], ['some shell gist'], ['some python gist'],
                              ['★ some starred gist']])

            # test include_orgs is True
            mocked_api_request.reset_mock()
            mocked_api_request.side_effect = [github_api.GIST_STARRED_LIST, github_api.GIST_LIST,
                                              [{'login': 'some org login'}]]
            gist.settings.set('include_orgs', True)
            gist_list_base.run()
            self.assertEqual(mocked_api_request.call_count, 3)
            self.assertEqual(mocked_api_request.mock_calls[2][1], (DEFAULT_ORGS_URL,))

            # test run() accepts one argument
            mocked_api_request.reset_mock()
            mocked_api_request.side_effect = [github_api.GIST_STARRED_LIST, github_api.GIST_LIST]
            gist.settings.set('include_users', [])
            gist.settings.set('include_orgs', [])
            gist_list_base = gist.GistListCommandBase()

            self.assertIsNone(gist_list_base.run('accepts one argument'))

            # test on_gist_num
            on_gist_num = mocked_window.show_quick_panel.call_args[0][1]

            # pass flow
            mocked_window.reset_mock()
            mocked_api_request.reset_mock()
            with patch('gist.GistListCommandBase.handle_gist') as mocked_handle_gist:
                on_gist_num(-1)

                self.assertEqual(mocked_api_request.call_count, 0)
                self.assertEqual(mocked_window.show_quick_panel.call_count, 0)
                self.assertEqual(mocked_handle_gist.call_count, 0)

            # personal gists flow
            mocked_window.reset_mock()
            mocked_api_request.reset_mock()
            with patch('gist.GistListCommandBase.handle_gist') as mocked_handle_gist:
                on_gist_num(0)

                self.assertEqual(mocked_api_request.call_count, 0)
                self.assertEqual(mocked_window.show_quick_panel.call_count, 0)
                mocked_handle_gist.assert_called_with(github_api.GIST_LIST[0])

            # organizations flow
            mocked_window.reset_mock()
            mocked_api_request.reset_mock()
            mocked_api_request.side_effect = [[{'login': 'some_organization'}], github_api.GIST_LIST]
            gist_list_base.orgs = [0]  # off_orgs = 1

            on_gist_num(0)

            self.assertEqual(mocked_api_request.call_count, 2)
            self.assertEqual(mocked_api_request.call_args_list[0][0][0], TEST_ORG_MEMBERS_URL)
            self.assertEqual(mocked_api_request.call_args_list[1][0][0], TEST_ORG_GIST_URL)
            mocked_window.show_quick_panel.assert_called_with([['some shell gist'], ['some python gist']], on_gist_num)

            # users flow
            mocked_window.reset_mock()
            mocked_api_request.reset_mock()
            mocked_api_request.side_effect = [github_api.GIST_LIST]
            gist_list_base.users = [0]  # off_users = 1

            on_gist_num(0)

            self.assertEqual(mocked_api_request.call_count, 1)
            self.assertEqual(mocked_api_request.call_args_list[0][0][0], TEST_MEMBERS_URL)
            mocked_window.show_quick_panel.assert_called_with([['some shell gist'], ['some python gist']], on_gist_num)

        self.assertRaises(NotImplementedError, gist_list_base.handle_gist, None)
        self.assertRaises(NotImplementedError, gist_list_base.get_window)

    @patch('gist.open_gist')
    def test_gist_list_command(self, mocked_open_gist):
        mocked_window = Mock()
        gist_list = gist.GistListCommand(mocked_window)
        gist_list.handle_gist({'url': TEST_GIST_URL})
        mocked_open_gist.assert_called_with(TEST_GIST_URL)
        self.assertEqual(gist_list.get_window(), mocked_window)

    @patch('gist.insert_gist')
    def test_insert_gist_list_command(self, mocked_insert_gist):
        mocked_window = Mock()
        insert_gist_list = gist.InsertGistListCommand(mocked_window)
        insert_gist_list.handle_gist({'url': TEST_GIST_URL})
        mocked_insert_gist.assert_called_with(TEST_GIST_URL)
        self.assertEqual(insert_gist_list.get_window(), mocked_window)

    @patch('gist.insert_gist_embed')
    def test_insert_gist_embed_list_command(self, mocked_insert_gist_embed):
        mocked_window = Mock()
        insert_gist_embed_list = gist.InsertGistEmbedListCommand(mocked_window)
        insert_gist_embed_list.handle_gist({'url': TEST_GIST_URL})
        mocked_insert_gist_embed.assert_called_with(TEST_GIST_URL)
        self.assertEqual(insert_gist_embed_list.get_window(), mocked_window)

    @patch('gist.gistify_view')
    @patch('gist.update_gist')
    def test_gist_add_file_command(self, mocked_update_gist, mocked_gistify_view):
        add_file = gist.GistAddFileCommand()
        add_file.handle_gist({'url': TEST_GIST_URL})
        self.assertEqual(add_file.view.window().show_input_panel.call_args[0][0], 'File Name:')
        self.assertEqual(add_file.view.window().show_input_panel.call_args[0][1], '')
        self.assertEqual(add_file.view.window().show_input_panel.call_args[0][3], None)
        self.assertEqual(add_file.view.window().show_input_panel.call_args[0][4], None)
        self.assertEqual(add_file.get_window(), add_file.view.window())

        self.assertTrue(add_file.is_enabled())
        add_file.view.settings().set('gist_url', 'not none')
        self.assertFalse(add_file.is_enabled())

        mocked_update_gist.return_value = 'some new gist'
        on_filename = add_file.view.window().show_input_panel.call_args[0][2]
        on_filename('some file')
        mocked_update_gist.assert_called_with(TEST_GIST_URL, {'some file': {'content': ''}})
        mocked_gistify_view.assert_called_with(add_file.view, 'some new gist', 'some file')
        sublime.status_message.assert_called_with('File added to Gist')

    def test_gist_view_command(self):
        gist_view_command = gist.GistViewCommand()
        gist_view_command.view = sublime.View()

        self.assertFalse(gist_view_command.is_enabled())

        gist_view_command.view.settings().set('gist_url', 'some gist url')
        gist_view_command.view.settings().set('gist_html_url', 'some gist html url')
        gist_view_command.view.settings().set('gist_filename', 'some gist filename')
        gist_view_command.view.settings().set('gist_description', 'some gist description')

        self.assertTrue(gist_view_command.is_enabled())
        self.assertEqual(gist_view_command.gist_url(), 'some gist url')
        self.assertEqual(gist_view_command.gist_html_url(), 'some gist html url')
        self.assertEqual(gist_view_command.gist_filename(), 'some gist filename')
        self.assertEqual(gist_view_command.gist_description(), 'some gist description')

    @patch('gist.gistify_view')
    @patch('test.stubs.sublime.Region')
    @patch('gist.create_gist')
    def test_gist_command(self, mocked_create_gist, mocked_region, mocked_gistify_view):
        gist_command = gist.GistCommand()
        gist_command.view = sublime.View()
        window = gist_command.view._window

        mocked_create_gist.return_value = {'html_url': 'some html url', 'files': {'test.txt': None}}

        self.assertEqual(gist_command.mode(), 'Public')

        gist_command.run(edit=None)

        self.assertEqual(window.show_input_panel.call_args_list[0][0][0], 'Gist Description (optional):')
        self.assertEqual(window.show_input_panel.call_args_list[0][0][1], '')

        on_gist_description = window.show_input_panel.call_args_list[0][0][2]

        on_gist_description('some description')

        self.assertEqual(window.show_input_panel.call_args_list[1][0][0], 'Gist File Name: (optional):')
        self.assertEqual(window.show_input_panel.call_args_list[1][0][1], '')

        on_gist_filename = window.show_input_panel.call_args_list[1][0][2]

        on_gist_filename('some filename')
        mocked_create_gist.assert_called_with(True, 'some description', {'some filename': ''})
        sublime.set_clipboard.assert_called_with('some html url')
        sublime.status_message.assert_called_with('Public Gist: some html url')
        self.assertEqual(mocked_gistify_view.call_count, 1)

        # TODO: test more than 2 regions selected

        # test 1 region selected and create_gist = None flows:
        mocked_region.empty.return_value = False
        mocked_create_gist.return_value = None
        gist_command.view.sel = lambda: [mocked_region]
        gist_command.view.settings().set('syntax', 'some_syntax.sublime-syntax')

        gist_command.run(edit=None)

        on_gist_description = window.show_input_panel.call_args_list[0][0][2]
        on_gist_description('some description')

        on_gist_filename = window.show_input_panel.call_args_list[1][0][2]
        on_gist_filename(None)

        mocked_region.assert_called_with(0, 0)
        self.assertEqual(mocked_gistify_view.call_count, 1)

    def test_gist_private_command(self):
        gist_private_command = gist.GistPrivateCommand()
        self.assertEqual(gist_private_command.mode(), 'Private')

    @patch('gist.gistify_view')
    @patch('gist.update_gist')
    def test_gist_rename_file_command(self, mocked_update_gist, mocked_gistify_view):
        gist_rename_file = gist.GistRenameFileCommand()
        mocked_update_gist.return_value = 'some updated gist'

        gist_rename_file.run(edit=False)

        self.assertEqual(gist_rename_file.view.window().show_input_panel.call_args_list[0][0][0], 'New File Name:')
        self.assertEqual(gist_rename_file.view.window().show_input_panel.call_args_list[0][0][1], None)
        self.assertEqual(gist_rename_file.view.window().show_input_panel.call_args_list[0][0][3], None)
        self.assertEqual(gist_rename_file.view.window().show_input_panel.call_args_list[0][0][4], None)

        on_filename = gist_rename_file.view.window().show_input_panel.call_args_list[0][0][2]

        on_filename('some new filename')
        mocked_update_gist.assert_called_with(None, {None: {'filename': 'some new filename', 'content': ''}})
        mocked_gistify_view.assert_called_with(gist_rename_file.view, 'some updated gist', 'some new filename')
        sublime.status_message.assert_called_with('Gist file renamed')

    @patch('gist.gistify_view')
    @patch('gist.update_gist')
    def test_change_description_command(self, mocked_update_gist, mocked_gistify_view):
        sublime._windows[0] = sublime.Window(0)
        mocked_update_gist.return_value = 'some updated gist'
        change_description = gist.GistChangeDescriptionCommand()
        change_description.run(edit=False)

        self.assertEqual(change_description.view.window().show_input_panel.call_args_list[0][0][0], 'New Description:')
        self.assertEqual(change_description.view.window().show_input_panel.call_args_list[0][0][1], '')
        self.assertEqual(change_description.view.window().show_input_panel.call_args_list[0][0][3], None)
        self.assertEqual(change_description.view.window().show_input_panel.call_args_list[0][0][4], None)

        on_gist_description = change_description.view.window().show_input_panel.call_args_list[0][0][2]
        on_gist_description('some description')

        mocked_update_gist.assert_called_with(None, {}, new_description='some description')
        mocked_gistify_view.assert_called_with(sublime._windows[0]._view, 'some updated gist', None)
        sublime.status_message.assert_called_with('Gist description changed')

    @patch('gist.update_gist')
    def test_gist_update_file_command(self, mocked_update_gist):
        gist_update_file = gist.GistUpdateFileCommand()
        gist_update_file.run(edit=False)

        mocked_update_gist.assert_called_with(None, {None: {'content': ''}})

        sublime.status_message.assert_called_with('Gist updated')

    @patch('gist.ungistify_view')
    @patch('gist.update_gist')
    def test_gist_delete_file_command(self, mocked_update_gist, mocked_ungistify_view):
        gist_delete_file = gist.GistDeleteFileCommand()
        gist_delete_file.run(edit=False)

        mocked_update_gist.assert_called_with(None, {None: None})
        mocked_ungistify_view.assert_called_with(gist_delete_file.view)

        sublime.status_message.assert_called_with('Gist file deleted')

    @patch('gist.ungistify_view')
    @patch('gist.api_request')
    def test_gist_delete_command(self, mocked_api_request, mocked_ungistify_view):
        gist_delete = gist.GistDeleteCommand()
        gist_delete.run(edit=False)

        mocked_api_request.assert_called_with(None, method='DELETE')
        mocked_ungistify_view.assert_called_with(sublime._windows[0]._view)

        sublime.status_message.assert_called_with('Gist deleted')

    @patch('gist.update_gist')
    def test_gist_listener(self, mocked_update_gist):
        gist_listener = gist.GistListener()
        gist.plugin_loaded()

        lock = Lock()

        self.update_gist_call_count = 0

        # noinspection PyUnusedLocal
        def threaded_call_count(*kwargs):
            with lock:
                self.update_gist_call_count += 1

        threaded_call_count.update_gist_call_count = 0

        mocked_update_gist.side_effect = threaded_call_count

        view = sublime.View()
        gist_listener.on_pre_save(view)
        gist.settings.set('update_on_save', False)
        self.assertEqual(self.update_gist_call_count, 0)
        self.assertIsNone(view.settings().get('do-update'))

        view.settings().set('gist_filename', 'test_gist.txt')
        gist_listener.on_pre_save(view)
        self.assertEqual(self.update_gist_call_count, 0)
        self.assertIsNone(view.settings().get('do-update'))

        gist.settings.set('update_on_save', True)
        gist_listener.on_pre_save(view)
        self.assertEqual(self.update_gist_call_count, 0)
        self.assertTrue(view.settings().get('do-update'))

        gist_listener.on_pre_save(view)
        self.assertEqual(self.update_gist_call_count, 1)
        self.assertTrue(view.settings().get('do-update'))
