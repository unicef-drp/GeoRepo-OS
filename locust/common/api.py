# coding=utf-8
"""
GeoRepo.

.. note:: API Class for Locust Load Testing
"""

import time
import random
from json import JSONDecodeError


class ApiTaskTag:
    """Represent the tag for a task."""

    pass


class ApiPageResult:
    """Represent Api response with pagination."""

    def __init__(self, json_dict):
        """Initialize the class."""
        self.page = json_dict['page']
        self.total_page = json_dict['total_page']
        self.page_size = json_dict['page_size']
        self.results = json_dict['results']

    def random_item(self):
        """Get random item from results list."""
        if self.results is None or len(self.results) == 0:
            return {}
        
        return random.choice(self.results)

class Api:
    """Provides api call to GeoRepo."""

    DEFAULT_MODULE = 'Admin Boundaries'

    DEFAULT_HEADERS = {
        'user-agent': (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ' +
            '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        )
    }

    def __init__(self, client, user):
        """Initialize the class."""
        self.client = client
        self.user = user

    def _get_headers(self):
        """Get headers for API Call."""
        headers = {
            'Authorization': 'Token ' + self.user['api_key'],
            'GeoRepo-User-Key': self.user['username'],
        }
        headers.update(self.DEFAULT_HEADERS)
        return headers

    def _build_api_endpoint_pagination(self, endpoint, page, page_size):
        """Build url to api endpoint with pagination request."""
        url = endpoint
        if '?' in url:
            url += f'&page{page}&page_size={page_size}'
        else:
            url += f'?page{page}&page_size={page_size}'

        return url

    def wait(self):
        """Wait for another API call."""
        time.sleep(self.user['wait_time'](self))

    def _api_get_list(self, api_endpoint, request_name):
        """Call GET API that returns page result."""
        result = None
        with (
            self.client.get(
                api_endpoint,
                catch_response=True,
                headers=self._get_headers(),
                name=request_name
            )
        ) as response:
            try:
                result = ApiPageResult(response.json())
            except JSONDecodeError:
                response.failure(
                    "Response could not be decoded as JSON"
                )
            except KeyError:
                response.failure(
                    "Response did not contain expected key"
                )
        return result

    def _api_get_detail(self, api_endpoint, request_name):
        """Call GET API that returns dictionary."""
        result = None
        with (
            self.client.get(
                api_endpoint,
                catch_response=True,
                headers=self._get_headers(),
                name=request_name
            )
        ) as response:
            try:
                result = response.json()
            except JSONDecodeError:
                response.failure(
                    "Response could not be decoded as JSON"
                )
            except KeyError:
                response.failure(
                    "Response did not contain expected key"
                )
        return result

    def _api_get_page(
            self, api_endpoint, request_name, page=None, page_size=50):
        """Fetch GET API for given page.
        
        if page is None, then it will randomize a page.
        """
        url = self._build_api_endpoint_pagination(
            api_endpoint,
            page if page else 1,
            page_size
        )
        result = self._api_get_list(url, request_name)

        if result and page is None and result.total_page > 1:
            # check if need to fetch random page
            rand_page = random.randint(1, result.total_page)
            if rand_page != 1:
                self.wait()
                url = self._build_api_endpoint_pagination(
                    api_endpoint,
                    rand_page,
                    page_size
                )
                result = self._api_get_list(url, request_name)
        return result

    def module_list(self):
        """Call module list API."""
        result = self._api_get_list(
            '/api/v1/search/module/list/',
            'module_list'
        )

        if result is None:
            return None

        # parse the admin boundaries uuid
        module_uuid = None
        for module in result.results:
            if (
                module.get('name', '') == self.DEFAULT_MODULE
            ):
                module_uuid = module.get('uuid', None)
                break
        return module_uuid

    def dataset_list(self, module_uuid):
        """Call dataset list API."""
        if module_uuid is None:
            return None
        return self._api_get_page(
            f'/api/v1/search/module/{module_uuid}/dataset/list/',
            'dataset_list'
        )

    def dataset_detail(self, dataset_uuid):
        """Call dataset detail API."""
        self.client.get(
            f'/api/v1/search/dataset/{dataset_uuid}/',
            headers=self._get_headers(),
            name='dataset_detail'
        )

    def view_list(self, dataset_uuid):
        """Call view list API."""
        if dataset_uuid is None:
            return None
        return self._api_get_page(
            f'/api/v1/search/dataset/{dataset_uuid}/view/list/',
            'view_list'
        )

    def view_detail(self, view_uuid):
        """Call view detail API."""
        if view_uuid is None:
            return None
        return self._api_get_detail(
            f'/api/v1/search/view/{view_uuid}/',
            'view_detail'
        )

    def view_list_by_user(self):
        """Call view list by user API."""
        pass

    def view_centroid(self):
        """Call view centroid API."""
        pass

    def find_entity_by_level(self, view_uuid, admin_level):
        """Call entity list by admin level API."""
        if view_uuid is None:
            return None
        return self._api_get_page(
            f'/api/v1/search/view/{view_uuid}/entity/level/{admin_level}/',
            f'entity_by_level_{admin_level}'
        )

    def find_entity_by_ucode(self):
        """Call find entity by ucode API."""
        pass

    def find_entity_by_concept_ucode(self):
        """Call find entity by concept ucode API."""
        pass

    def find_entity_by_id(self):
        """Call find entity by id API."""
        pass

    def find_entity_by_level_and_parent_ucode(self):
        """Call find entity by level and parent_ucode API."""
        pass

    def find_entity_by_level_and_parent_cucode(self):
        """Call find entity by level and parent cucode API."""
        pass

    def find_entity_list_by_level0(self):
        """Call entity list by level 0 API."""
        pass
