# coding=utf-8
"""
GeoRepo-OS.

.. note:: API Class for Locust Load Testing
"""


class ApiTaskTag:
    """Represent the tag for a task."""

    pass


class Api:
    """Provides api call to GeoRepo."""

    def __init__(self, client, user):
        """Initialize the class."""
        self.client = client
        self.user = user

    def module_list(self):
        """Call module list API."""
        pass

    def dataset_list(self):
        """Call dataset list API."""
        pass

    def dataset_detail(self):
        """Call dataset detail API."""
        pass

    def view_list(self):
        """Call view list API."""
        pass

    def view_detail(self):
        """Call view detail API."""
        pass

    def view_list_by_user(self):
        """Call view list by user API."""
        pass

    def view_centroid(self):
        """Call view centroid API."""
        pass

    def find_entity_by_level(self):
        """Call entity list by admin level API."""
        pass

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
