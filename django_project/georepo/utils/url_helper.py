from core.models.preferences import SitePreferences


def get_ucode_from_url_path(url_path: str, slice_idx: int):
    """
    Parse ucode from url path
    e.g.
    - url_path = /ZAK/NC_0003_V1/2014-12-05/
      ucode = ZAK/NC_0003_V1
      slice_idx = -1
      data = [2014-12-05]
    - url_path = /ZAK/NC_0003_V1/level/0/
      ucode = ZAK/NC_0003_V1
      slice_idx = -2
      data = [level, 0]
    """
    if slice_idx >= 0:
        raise ValueError('slice_idx parameter must be negative index')
    data = []
    ucode = None
    splits = url_path.split('/')
    splits = [x for x in splits if x]
    if len(splits) > 1:
        ucode = '/'.join(splits[:slice_idx])
        idx = slice_idx
        while idx < 0:
            data.append(splits[idx])
            idx += 1
    else:
        ucode = splits[0]
    return ucode, data


def get_page_size(request):
    """
    Get page size from request if exists
    if it does not exist in request, then get default from SitePreferences
    if over the maximum allowed size, then returns the maximum
    """
    config = SitePreferences.preferences().api_config
    page_size = request.GET.get('page_size', None)
    if page_size is None:
        page_size = (
            config['default_page_size'] if 'default_page_size' in config
            else 50
        )
    else:
        page_size = int(page_size)
    max_size = config['max_page_size'] if 'max_page_size' in config else 50
    if page_size > max_size:
        page_size = max_size
    return page_size
