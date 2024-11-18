# coding=utf-8
"""
GeoRepo-OS.

.. note:: Class for Testing Search Entity
"""

import random
from locust import HttpUser, task

from common.auth import auth_config
from common.api import Api


class SearchEntityUserScenario(HttpUser):
    """Search entity scenario for testing API."""

    def on_start(self):
        """Set the test."""
        self.api = Api(self.client, auth_config.get_user())

    def wait_time(self):
        """Get wait_time in second."""
        return self.api.user['wait_time'](self)

    @task
    def search_entity_workflow(self):
        """Workflow to search entity."""
        # get module list
        module_uuid = self.api.module_list()
        self.api.wait()

        # get dataset
        dataset_list = self.api.dataset_list(module_uuid)
        if not dataset_list:
            return
        self.api.wait()

        # get view list
        dataset = dataset_list.random_item()
        view_list = self.api.view_list(dataset.get('uuid', None))
        if not view_list:
            return
        self.api.wait()

        # get view detail
        view = view_list.random_item()
        view_detail = self.api.view_detail(view.get('uuid', None))
        if not view_detail or len(view_detail.get('dataset_levels', [])) == 0:
            return
        self.api.wait()

        admin_level = random.choice(view_detail.get('dataset_levels', []))
        self.api.find_entity_by_level(
            view.get('uuid', None),
            admin_level.get('level', 0)
        )
