"""Unit tests for prune_static_versions management command."""

import os
import tempfile
from unittest import TestCase

from core.management.commands.prune_static_versions import prune


class TestPruneStaticVersions(TestCase):
    """Tests for prune function."""

    def setUp(self):
        """Set up a temporary directory for testing."""
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up the temporary directory after testing."""
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_versions(self, *versions):
        for v in versions:
            os.makedirs(os.path.join(self.tmp, v))

    def _existing(self):
        return set(os.listdir(self.tmp))

    def test_deletes_oldest_versions(self):
        """Test that the oldest versions are deleted when count exceeds."""
        self._make_versions("0.0.1", "0.0.2", "0.0.3", "0.0.4")
        prune(self.tmp, keep=3)
        self.assertEqual(self._existing(), {"0.0.2", "0.0.3", "0.0.4"})

    def test_keeps_all_when_count_below_keep(self):
        """Test that no versions are deleted when count is below keep."""
        self._make_versions("0.0.1", "0.0.2")
        prune(self.tmp, keep=3)
        self.assertEqual(self._existing(), {"0.0.1", "0.0.2"})

    def test_keeps_exact_count(self):
        """Test that no versions are deleted when count equals keep."""
        self._make_versions("0.0.1", "0.0.2", "0.0.3")
        prune(self.tmp, keep=3)
        self.assertEqual(self._existing(), {"0.0.1", "0.0.2", "0.0.3"})

    def test_version_sort_order(self):
        """Test that versions are sorted correctly."""
        # Lexicographic sort would wrongly place 0.0.9 after 0.0.78
        self._make_versions("0.0.9", "0.0.10", "0.0.78", "0.0.79")
        prune(self.tmp, keep=3)
        self.assertEqual(self._existing(), {"0.0.10", "0.0.78", "0.0.79"})

    def test_keep_one(self):
        """Test that only the most recent version is kept when keep=1."""
        self._make_versions("0.0.1", "0.0.2", "0.0.3")
        prune(self.tmp, keep=1)
        self.assertEqual(self._existing(), {"0.0.3"})

    def test_empty_directory(self):
        """Test that prune does not fail on an empty directory."""
        prune(self.tmp, keep=3)
        self.assertEqual(self._existing(), set())
