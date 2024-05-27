import os
import io
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
    ContainerClient,
    ContentSettings,
    CorsRule
)
from django.conf import settings
from datetime import datetime, timedelta, timezone
import zipfile
from zipfly import ZipFly


class DirectoryClient:
    def __init__(self, connection_string, container_name,
                 add_source_base_name = False):
        self.container_name = container_name
        self.service_client = (
            BlobServiceClient.from_connection_string(connection_string)
        )
        self.client = self.service_client.get_container_client(container_name)
        self.add_source_base_name = add_source_base_name

    def upload(self, source, dest):
        """
        Upload a file or directory to a path inside the container
        """
        if (os.path.isdir(source)):
            self.upload_dir(source, dest)
        else:
            self.upload_file(source, dest)

    def upload_file(self, source, dest):
        """
        Upload a single file to a path inside the container
        """
        with open(source, 'rb') as data:
            self.client.upload_blob(name=dest, data=data)

    def upload_gzip_file(self, source, dest, cache_control=None):
        """
        Upload a gzipped file
        """
        with open(source, 'rb') as data:
            self.client.upload_blob(
                name=dest,
                data=data,
                content_settings=ContentSettings(
                    content_encoding='gzip',
                    cache_control=cache_control
                )
            )

    def upload_dir(self, source, dest):
        """
        Upload a directory to a path inside the container
        """
        prefix = '' if dest == '' else dest + '/'
        if self.add_source_base_name:
            prefix += os.path.basename(source) + '/'
        for root, dirs, files in os.walk(source):
            for name in files:
                dir_part = os.path.relpath(root, source)
                dir_part = '' if dir_part == '.' else dir_part + '/'
                file_path = os.path.join(root, name)
                blob_path = prefix + dir_part + name
                self.upload_file(file_path, blob_path)

    def download(self, source, dest):
        """
        Download a file or directory to a path on the local filesystem
        """
        if not dest:
            raise Exception('A destination must be provided')

        blobs = self.ls_files(source, recursive=True)
        if blobs:
            # if source is a directory, dest must also be a directory
            if not source == '' and not source.endswith('/'):
                source += '/'
            if not dest.endswith('/'):
                dest += '/'
            # append the directory name from source to the destination
            dest += os.path.basename(os.path.normpath(source)) + '/'

            blobs = [source + blob for blob in blobs]
            for blob in blobs:
                blob_dest = dest + os.path.relpath(blob, source)
                self.download_file(blob, blob_dest)
        else:
            self.download_file(source, dest)

    def download_file(self, source, dest):
        """
        Download a single file to a path on the local filesystem
        """
        # dest is a directory if ending with '/' or '.', otherwise it's a file
        if dest.endswith('.'):
            dest += '/'
        blob_dest = (
            dest + os.path.basename(source) if dest.endswith('/') else dest
        )

        os.makedirs(os.path.dirname(blob_dest), exist_ok=True)
        bc = self.client.get_blob_client(blob=source)
        if not dest.endswith('/'):
            with open(blob_dest, 'wb') as file:
                data = bc.download_blob()
                file.write(data.readall())

    def ls_files(self, path, recursive=False):
        """
        List files under a path, optionally recursively
        """
        if not path == '' and not path.endswith('/'):
            path += '/'

        blob_iter = self.client.list_blobs(name_starts_with=path)
        files = []
        for blob in blob_iter:
            relative_path = os.path.relpath(blob.name, path)
            if recursive or '/' not in relative_path:
                files.append(relative_path)
        return files

    def ls_dirs(self, path, recursive=False):
        """
        List directories under a path, optionally recursively
        """
        if not path == '' and not path.endswith('/'):
            path += '/'

        blob_iter = self.client.list_blobs(name_starts_with=path)
        dirs = []
        for blob in blob_iter:
            relative_dir = os.path.dirname(os.path.relpath(blob.name, path))
            if (
                relative_dir and (recursive or '/' not in relative_dir) and
                relative_dir not in dirs
            ):
                dirs.append(relative_dir)

        return dirs

    def rm(self, path, recursive=False):
        """
        Remove a single file, or remove a path recursively
        """
        if recursive:
            self.rmdir(path)
        else:
            self.client.delete_blob(path)

    def rmdir(self, path):
        """
        Remove a directory and its contents recursively
        """
        blobs = self.ls_files(path, recursive=True)
        if not blobs:
            return

        if not path == '' and not path.endswith('/'):
            path += '/'
        # if client is using azurite, cannot delete using batch
        # https://github.com/Azure/Azurite/issues/1809
        if 'azurite' in self.client.url:
            for blob in blobs:
                blob = path + blob
                self.client.delete_blob(blob)
        else:
            blobs_length = len(blobs)
            blobs = [path + blob for blob in blobs]
            if blobs_length <= 256:
                self.client.delete_blobs(*blobs)
            else:
                start = 0
                end = 256
                while end <= blobs_length:
                    # each time, delete 256 blobs at most
                    self.client.delete_blobs(*blobs[start:end])
                    start = start + 256
                    end = end + 256
                    if start < blobs_length and end > blobs_length:
                        self.client.delete_blobs(*blobs[start:blobs_length])

    def movedir(self, source_path, dest_path, is_copy=False):
        blobs = self.ls_files(source_path, recursive=True)
        if not blobs:
            return

        if not source_path == '' and not source_path.endswith('/'):
            source_path += '/'
        if not dest_path == '' and not dest_path.endswith('/'):
            dest_path += '/'
        for blob in blobs:
            source_blob = self.service_client.get_blob_client(
                self.container_name,
                source_path + blob
            )
            # Create sas token for blob
            sas_token = generate_blob_sas(
                blob_name=source_path + blob,
                account_name=self.client.credential.account_name,
                container_name=self.container_name,
                account_key=self.client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                start=datetime.now(),
                expiry=datetime.utcnow() + timedelta(hours=1)
            )
            dest_blob = self.service_client.get_blob_client(
                self.container_name,
                dest_path + blob
            )
            sas_url = f"{source_blob.url}?{sas_token}"
            dest_blob.start_copy_from_url(sas_url, requires_sync=True)
            copy_properties = dest_blob.get_blob_properties().copy

            if copy_properties.status != "success":
                dest_blob.abort_copy(copy_properties.id)
                raise Exception(
                    "Unable to copy blob %s with status %s"
                    % (source_path + blob, copy_properties.status)
                )
            if not is_copy:
                source_blob.delete_blob()

    def dir_size(self, path):
        if not path == '' and not path.endswith('/'):
            path += '/'
        total_size = 0
        blob_iter = self.client.list_blobs(name_starts_with=path)
        for blob in blob_iter:
            total_size += blob.size
        return total_size

    def dir_info(self, path):
        if not path == '' and not path.endswith('/'):
            path += '/'
        total_size = 0
        total_files = 0
        blob_iter = self.client.list_blobs(name_starts_with=path)
        for blob in blob_iter:
            total_size += blob.size
            total_files += 1
        return total_size, total_files

    def generate_url_for_file(self, path, expiry_in_hours=48):
        """
        Generate temporary URL for file download that has expiry in hours.
        """
        start_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        expiry_time = start_time + timedelta(hours=expiry_in_hours)
        sas_token = generate_blob_sas(
            blob_name=path,
            account_name=self.client.credential.account_name,
            container_name=self.container_name,
            account_key=self.client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            start=start_time,
            expiry=expiry_time
        )
        bc = self.client.get_blob_client(blob=path)
        return f"{bc.url}?{sas_token}"


def get_tegola_cache_config(connection_string, container_name):
    service_client = (
        BlobServiceClient.from_connection_string(connection_string)
    )
    client = service_client.get_container_client(container_name)
    return {
        'container_url': client.url,
        'az_account_name': client.credential.account_name,
        'az_shared_key': client.credential.account_key
    }


class CustomZipflyStream(io.RawIOBase):

    """
    The RawIOBase ABC extends IOBase. It deals with
    the reading and writing of bytes to a stream. FileIO subclasses
    RawIOBase to provide an interface to files in the machine’s file system.
    """

    def __init__(self):
        self._buffer = b''
        self._size = 0

    def writable(self):
        return True

    def write(self, b):
        if self.closed:
            raise RuntimeError("ZipFly stream was closed!")
        self._buffer += b
        return len(b)

    def get(self):
        chunk = self._buffer
        self._buffer = b''
        self._size += len(chunk)
        return chunk

    def size(self):
        return self._size


class AzureStorageZipfly(ZipFly):
    """Extension of Zipfly that read streams from azure blob storage."""

    def __init__(self,
                 mode = 'w',
                 paths = [],
                 chunksize = 0x8000,
                 compression = zipfile.ZIP_STORED,
                 allowZip64 = True,
                 compresslevel = None,
                 storesize = 0,
                 filesystem = 'fs',
                 arcname = 'n',
                 encode = 'utf-8',
                 storage_container_client: ContainerClient = None):
        """storage_container_client is container client to download blob."""
        super(AzureStorageZipfly, self).__init__(
            mode, paths, chunksize, compression, allowZip64, compresslevel,
            storesize, filesystem, arcname, encode
        )
        self.storage_container_client = storage_container_client

    def generator(self):
        stream = CustomZipflyStream()
        with zipfile.ZipFile(
            stream,
            mode = self.mode,
            compression = self.compression,
            allowZip64 = self.allowZip64,) as zf:
            for path in self.paths:
                if self.filesystem not in path:
                    raise RuntimeError(f"'{self.filesystem}' key is required")
                """
                filesystem should be the path to blob storage
                """
                if self.arcname not in path:
                    # arcname will be default path
                    path[self.arcname] = path[self.filesystem]
                bc = self.storage_container_client.get_blob_client(
                    blob=path[self.filesystem])
                properties = bc.get_blob_properties()
                current_dt = datetime.now()
                blob_date_time = (
                    current_dt.year, current_dt.month, current_dt.day,
                    current_dt.hour, current_dt.minute, current_dt.second
                )
                if properties.creation_time:
                    blob_date_time = (
                        properties.creation_time.year,
                        properties.creation_time.month,
                        properties.creation_time.day,
                        properties.creation_time.hour,
                        properties.creation_time.minute,
                        properties.creation_time.second
                    )
                z_info = zipfile.ZipInfo(path[self.arcname], blob_date_time)
                z_info.file_size = properties.size
                # read blob as stream
                bc_stream = bc.download_blob()
                with zf.open(z_info, mode=self.mode) as d:
                    for chunk in bc_stream.chunks():
                        d.write(chunk)
                        yield stream.get()
            self.set_comment(self.comment)
            zf.comment = self.comment
        yield stream.get()
        self._buffer_size = stream.size()
        # Flush and close this stream.
        stream.close()


def set_azure_cors_rule(service_client, allowed_origins,
                        allowed_methods=['GET']):
    # Create CORS rules
    cors_rule = CorsRule(
        allowed_origins, allowed_methods, max_age_in_seconds=3600,
        allowed_headers=['*'], exposed_headers=['*'])
    cors = [cors_rule]
    service_client.set_service_properties(cors=cors)


StorageServiceClient = None
StorageContainerClient = None
if (
    settings.USE_AZURE and settings.AZURE_STORAGE and
    settings.AZURE_STORAGE_CONTAINER
):
    StorageServiceClient = BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE
    )
    StorageContainerClient = StorageServiceClient.get_container_client(
        settings.AZURE_STORAGE_CONTAINER
    )
