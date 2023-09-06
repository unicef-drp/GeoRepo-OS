import re
import subprocess


def parse_ogrinfo_output(output: str):
    feature_count = 0
    attributes = []
    match_feature_count = re.search(r'Feature Count: ([\d]+)', output)
    if match_feature_count:
        feature_count = int(match_feature_count.group(1))
    match_crs = re.search(r'ID\["EPSG",4326\]', output)
    is_crs_4326 = match_crs is not None
    match_attribs = re.search(
        r'Data axis to CRS axis mapping:.+\n([\S\s]+)',
        output,
        re.IGNORECASE
    )
    if match_attribs:
        attribs_str = match_attribs.group(1).splitlines()
        for attr in attribs_str:
            attr_keys = attr.split(':')
            if len(attr_keys) == 2:
                attributes.append(attr_keys[0])
    return feature_count, is_crs_4326, attributes


def read_metadata_file(file_path: str, type):
    if type == 'SHAPEFILE':
        if not file_path.startswith('/vsizip/'):
            file_path = f'/vsizip/{file_path}'
    cmd = f'ogrinfo -ro -al -so {file_path}'
    res = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        check=True,
        text=True,
        executable='/bin/bash',
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr.decode())
    return parse_ogrinfo_output(res.stdout)
