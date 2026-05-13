import unittest

from autobots.catalog import ClusterCatalog


class ClusterCatalogTests(unittest.TestCase):
    def test_live_catalog_uses_only_available_model_ids(self) -> None:
        catalog = ClusterCatalog(
            available_model_ids=[
                "nvidia/step-3.5-flash",
                "nvidia/qwen3.5-coder-480b-a35b-instruct",
                "nvidia/whisper-large-v3",
                "nvidia/nemotron-ocr-v1",
            ],
            refresh_live=False,
        )

        self.assertTrue(catalog.using_live_catalog)
        self.assertEqual(catalog.available_model_count, 4)

        optimus_ids = [model.model_id for model in catalog.get_cluster("Optimus").models]
        self.assertIn("nvidia/step-3.5-flash", optimus_ids)
        self.assertNotIn("nvidia/nemotron-3-super-120b-a12b", optimus_ids)

        ratchet_ids = [model.model_id for model in catalog.get_cluster("Ratchet").models]
        self.assertIn("nvidia/qwen3.5-coder-480b-a35b-instruct", ratchet_ids)

        bumblebee_ids = [model.model_id for model in catalog.get_cluster("Bumblebee").models]
        self.assertIn("nvidia/whisper-large-v3", bumblebee_ids)

        perceptor_ids = [model.model_id for model in catalog.get_cluster("Perceptor").models]
        self.assertIn("nvidia/nemotron-ocr-v1", perceptor_ids)

    def test_live_catalog_backfills_empty_clusters_from_available_pool(self) -> None:
        catalog = ClusterCatalog(
            available_model_ids=["nvidia/step-3.5-flash"],
            refresh_live=False,
        )

        for cluster_name in catalog.cluster_names():
            self.assertGreater(len(catalog.get_cluster(cluster_name).models), 0)

    def test_live_catalog_matches_current_provider_prefixes_by_model_name(self) -> None:
        catalog = ClusterCatalog(
            available_model_ids=[
                "stepfun-ai/step-3.5-flash",
                "openai/gpt-oss-120b",
                "z-ai/glm-5.1",
            ],
            refresh_live=False,
        )

        optimus_ids = [model.model_id for model in catalog.get_cluster("Optimus").models]
        self.assertEqual(optimus_ids[:3], ["stepfun-ai/step-3.5-flash", "openai/gpt-oss-120b", "z-ai/glm-5.1"])


if __name__ == "__main__":
    unittest.main()
