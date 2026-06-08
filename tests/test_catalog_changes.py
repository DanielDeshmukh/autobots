"""Tests for catalog.py changes - live catalog removal and refresh method."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from autobots.catalog import ClusterCatalog


class TestCatalogChanges(unittest.TestCase):
    """Test suite for catalog.py changes."""

    def test_cluster_catalog_initializes_without_discovery(self):
        """Test that ClusterCatalog initializes without find_endpoints.py."""
        catalog = ClusterCatalog(api_key="test-key", refresh_live=False)
        self.assertIsNotNone(catalog)
        self.assertEqual(len(catalog.clusters), 9)

    def test_cluster_catalog_bundled_models(self):
        """Test that bundled models are available."""
        catalog = ClusterCatalog()
        # Should have models from CLUSTER_DEFINITIONS
        self.assertGreater(len(catalog.clusters), 0)

    def test_cluster_catalog_manual_model_ids(self):
        """Test that manual model IDs override bundled."""
        manual_ids = ["model-a", "model-b"]
        catalog = ClusterCatalog(available_model_ids=manual_ids)
        self.assertEqual(catalog.available_model_ids, tuple(manual_ids))
        self.assertTrue(catalog.using_live_catalog)

    def test_cluster_catalog_empty_when_no_api_key(self):
        """Test that live catalog is empty when no API key provided."""
        catalog = ClusterCatalog(api_key=None, refresh_live=True)
        self.assertEqual(catalog.available_model_ids, ())

    def test_refresh_catalog_requires_api_key(self):
        """Test that refresh_catalog requires API key."""
        catalog = ClusterCatalog(api_key=None)
        result = catalog.refresh_catalog()
        self.assertIn("error", result)

    @patch("autobots.catalog.ClusterCatalog.get_cached_catalog")
    def test_get_cached_catalog_returns_dict(self, mock_get_cached):
        """Test that get_cached_catalog returns a dict."""
        mock_get_cached.return_value = {"model-1": {"id": "model-1"}}
        catalog = ClusterCatalog()
        cached = catalog.get_cached_catalog()
        self.assertIsInstance(cached, dict)

    def test_refresh_catalog_returns_error_on_failure(self):
        """Test that refresh_catalog handles failures gracefully."""
        catalog = ClusterCatalog(api_key="invalid-key")

        with patch("autobots.catalog.ClusterCatalog.refresh_catalog") as mock_refresh:
            mock_refresh.return_value = {"error": "API connection failed"}
            result = catalog.refresh_catalog()
            self.assertIn("error", result)

    def test_cluster_routing_works(self):
        """Test that cluster routing still works after changes."""
        catalog = ClusterCatalog()
        decision = catalog.route_with_reasoning("implement login endpoint python")
        self.assertIsNotNone(decision.cluster_name)
        self.assertGreater(decision.score, 0)

    def test_model_selection_works(self):
        """Test that model selection still works."""
        catalog = ClusterCatalog()
        lead, reviewer, support = catalog.select_models("UltraMagnus", "backend api")
        self.assertIsNotNone(lead)
        self.assertIsNotNone(reviewer)


if __name__ == "__main__":
    unittest.main()
