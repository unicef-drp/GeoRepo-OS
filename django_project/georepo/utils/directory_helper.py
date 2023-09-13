import math
import os


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def get_folder_size(directory_path):
    if not os.path.exists(directory_path):
        return 0
    folder_size = 0
    # get size
    for path, dirs, files in os.walk(directory_path):
        for f in files:
            fp = os.path.join(path, f)
            folder_size += os.stat(fp).st_size
    return folder_size
