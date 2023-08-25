import mock
from django.test import TestCase
from georepo.utils.azure_blob_storage import DirectoryClient


def mocked_delete_blobs(self, *args, **kwargs):
    pass


def mocked_list_files():
    return ['file1', 'file2']


def mocked_list_files_2():
    res = []
    for i in range(256):
        res.append(f'file-{i}')
    return res


def mocked_list_files_3():
    res = []
    for i in range(300):
        res.append(f'file-{i}')
    return res


class TestAzureBlobStorage(TestCase):

    @mock.patch('azure.storage.blob.ContainerClient.delete_blobs')
    @mock.patch(
        'georepo.utils.azure_blob_storage.DirectoryClient.ls_files')
    def test_rmdir(self, mockedList, mockedDelete):
        mockedDelete.side_effect = mocked_delete_blobs
        conn_string = (
            'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;'
            'AccountKey=test;BlobEndpoint=http://test:10000/devstoreaccount1;'
        )
        client = DirectoryClient(conn_string, 'test')
        mockedList.return_value = mocked_list_files()
        client.rmdir('/test/path')
        self.assertEqual(mockedDelete.call_count, 1)
        mockedDelete.reset_mock()
        mockedList.return_value = mocked_list_files_2()
        client.rmdir('/test/path')
        self.assertEqual(mockedDelete.call_count, 1)
        mockedDelete.reset_mock()
        mockedList.return_value = mocked_list_files_3()
        client.rmdir('/test/path')
        self.assertEqual(mockedDelete.call_count, 2)
