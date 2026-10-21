from datetime import datetime
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from dropbox import files, sharing, users
from dropbox.exceptions import ApiError

NOW = datetime(2026, 10, 21, 12, 0)


def file_md(path, size=10):
    return files.FileMetadata(
        name=path.rsplit('/', 1)[-1], id='id:f', path_lower=path.lower(), path_display=path,
        client_modified=NOW, server_modified=NOW, rev='0123456789abcdef', size=size,
        content_hash='a' * 64, is_downloadable=True,
    )


def folder_md(path):
    return files.FolderMetadata(name=path.rsplit('/', 1)[-1], id='id:d', path_lower=path.lower(), path_display=path)


def api_error(error):
    return ApiError('req', error, None, None)


class DropboxViewsTest(TestCase):
    def setUp(self):
        patcher = mock.patch('cloud_storage.views.get_client')
        self.get_client = patcher.start()
        self.addCleanup(patcher.stop)
        self.dbx = self.get_client.return_value

        account = mock.Mock(email='user@example.com', email_verified=True, country='RU', locale='ru',
                            account_id='dbid:1', referral_link='https://db.tt/x', profile_photo_url=None,
                            is_paired=False, disabled=False, team=None)
        account.name.display_name = 'Иван Петров'
        account.account_type._tag = 'basic'
        self.dbx.users_get_current_account.return_value = account
        self.dbx.users_get_space_usage.return_value = users.SpaceUsage(
            used=512, allocation=users.SpaceAllocation.individual(users.IndividualSpaceAllocation(allocated=2048)))
        self.dbx.files_list_folder.return_value = files.ListFolderResult(
            entries=[file_md('/Docs/b.txt'), folder_md('/Docs/A')], cursor='c', has_more=False)

    def test_redirects_to_connect_without_account(self):
        self.get_client.return_value = None
        response = self.client.get(reverse('cloud_storage:browse'))
        self.assertRedirects(response, reverse('cloud_storage:connect'), fetch_redirect_response=False)

    def test_browse_lists_folders_first_and_space(self):
        response = self.client.get(reverse('cloud_storage:browse'), {'path': '/Docs'})
        self.assertEqual(response.status_code, 200)
        self.dbx.files_list_folder.assert_called_with('/Docs')
        names = [e['name'] for e in response.context['entries']]
        self.assertEqual(names, ['A', 'b.txt'])
        self.assertEqual(response.context['space'], {'used': 512, 'allocated': 2048, 'free': 1536, 'percent': 25.0})
        self.assertContains(response, 'Иван Петров')

    def test_account_page(self):
        response = self.client.get(reverse('cloud_storage:account'))
        self.assertContains(response, 'dbid:1')
        self.assertContains(response, 'user@example.com')

    def test_metadata_of_file(self):
        self.dbx.files_get_metadata.return_value = file_md('/Docs/b.txt', size=1234)
        self.dbx.sharing_list_shared_links.return_value = sharing.ListSharedLinksResult(links=[], has_more=False)
        response = self.client.get(reverse('cloud_storage:metadata'), {'path': '/Docs/b.txt'})
        self.assertContains(response, '0123456789abcdef')
        self.assertContains(response, '1234')

    def test_create_folder(self):
        self.client.post(reverse('cloud_storage:create_folder'), {'path': '/Docs', 'name': 'New'})
        self.dbx.files_create_folder_v2.assert_called_once_with('/Docs/New')

    def test_upload_conflict_without_replace_shows_error(self):
        conflict = files.UploadError.path(files.UploadWriteFailed(
            reason=files.WriteError.conflict(files.WriteConflictError.file), upload_session_id='s'))
        self.dbx.files_upload.side_effect = api_error(conflict)
        response = self.client.post(reverse('cloud_storage:upload'), {
            'path': '/Docs', 'file': self._file('b.txt')}, follow=True)
        self.assertContains(response, 'уже существует')
        self.assertEqual(self.dbx.files_upload.call_args.kwargs['mode'], files.WriteMode.add)

    def test_upload_with_replace_overwrites(self):
        self.client.post(reverse('cloud_storage:upload'), {
            'path': '/Docs', 'file': self._file('b.txt'), 'replace': 'on'})
        args, kwargs = self.dbx.files_upload.call_args
        self.assertEqual(args, (b'hello', '/Docs/b.txt'))
        self.assertEqual(kwargs['mode'], files.WriteMode.overwrite)

    def test_move_and_copy(self):
        self.dbx.files_move_v2.return_value = files.RelocationResult(metadata=file_md('/A/c.txt'))
        self.dbx.files_copy_v2.return_value = files.RelocationResult(metadata=file_md('/A/b.txt'))
        self.client.post(reverse('cloud_storage:move'), {'path': '/Docs/b.txt', 'to_folder': '/A', 'new_name': 'c.txt'})
        self.client.post(reverse('cloud_storage:copy'), {'path': '/Docs/b.txt', 'to_folder': '/A', 'new_name': ''})
        self.dbx.files_move_v2.assert_called_once_with('/Docs/b.txt', '/A/c.txt', autorename=False)
        self.dbx.files_copy_v2.assert_called_once_with('/Docs/b.txt', '/A/b.txt', autorename=False)

    def test_delete(self):
        self.dbx.files_delete_v2.return_value = files.DeleteResult(metadata=file_md('/Docs/b.txt'))
        response = self.client.post(reverse('cloud_storage:delete'), {'path': '/Docs/b.txt'})
        self.dbx.files_delete_v2.assert_called_once_with('/Docs/b.txt')
        self.assertEqual(response.url, reverse('cloud_storage:browse') + '?path=%2FDocs')

    def test_share_returns_existing_link(self):
        self.dbx.sharing_create_shared_link_with_settings.side_effect = api_error(
            sharing.CreateSharedLinkWithSettingsError('shared_link_already_exists', None))
        self.dbx.sharing_list_shared_links.return_value = mock.Mock(links=[mock.Mock(url='https://dropbox.com/s/x')])
        response = self.client.post(reverse('cloud_storage:share'), {'path': '/Docs/b.txt'}, follow=True)
        self.assertContains(response, 'https://dropbox.com/s/x')

    def test_shared_list(self):
        link = mock.Mock(url='https://dropbox.com/s/y', path_lower='/docs/b.txt', expires=None)
        link.name = 'b.txt'
        link.link_permissions.resolved_visibility._tag = 'public'
        self.dbx.sharing_list_shared_links.return_value = mock.Mock(links=[link], has_more=False)
        response = self.client.get(reverse('cloud_storage:shared'))
        self.assertContains(response, 'https://dropbox.com/s/y')
        self.assertContains(response, 'public')

    def test_search_by_content(self):
        match = files.SearchMatchV2(metadata=files.MetadataV2.metadata(file_md('/Docs/report.txt')))
        self.dbx.files_search_v2.return_value = files.SearchV2Result(matches=[match], has_more=False)
        response = self.client.get(reverse('cloud_storage:search'), {'q': 'отчёт', 'content': 'on'})
        options = self.dbx.files_search_v2.call_args.kwargs['options']
        self.assertFalse(options.filename_only)
        self.assertContains(response, 'report.txt')

    def test_download_file(self):
        self.dbx.files_get_metadata.return_value = file_md('/Docs/b.txt', size=5)
        self.dbx.files_download.return_value = (None, mock.Mock(iter_content=lambda size: iter([b'hello'])))
        response = self.client.get(reverse('cloud_storage:download'), {'path': '/Docs/b.txt'})
        self.assertEqual(b''.join(response.streaming_content), b'hello')
        self.assertIn('attachment; filename="b.txt"', response['Content-Disposition'])

    def test_api_error_on_page_shows_message(self):
        self.dbx.files_list_folder.side_effect = api_error(
            files.ListFolderError.path(files.LookupError.not_found))
        response = self.client.get(reverse('cloud_storage:browse'), {'path': '/nope'})
        self.assertContains(response, 'не найдены')

    @staticmethod
    def _file(name):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, b'hello')


class ConnectViewTest(TestCase):
    @mock.patch.dict('os.environ', {'DROPBOX_APP_KEY': 'appkey123'})
    def test_connect_page_has_authorize_link(self):
        response = self.client.get(reverse('cloud_storage:connect'))
        self.assertContains(response, 'https://www.dropbox.com/oauth2/authorize')
        self.assertContains(response, 'appkey123')
        self.assertTrue(self.client.session['dropbox_code_verifier'])

    @mock.patch.dict('os.environ', {'DROPBOX_APP_KEY': ''})
    def test_connect_page_without_app_key(self):
        response = self.client.get(reverse('cloud_storage:connect'))
        self.assertContains(response, 'DROPBOX_APP_KEY')
