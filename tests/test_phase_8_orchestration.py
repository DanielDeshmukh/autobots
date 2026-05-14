"""Tests for Phase 8 orchestration improvements."""

import os
import unittest
from unittest.mock import patch

from autobots.catalog import ClusterCatalog
from autobots.router.models import PhaseRecord, MergeStrategy
from autobots.router.planning import ClusterPlanner


class Phase8RoutingTests(unittest.TestCase):
    def test_route_with_reasoning_prefers_frontend_cluster_for_tsx_and_css_signals(self) -> None:
        catalog = ClusterCatalog(refresh_live=False)

        decision = catalog.route_with_reasoning(
            "P4 | Refresh dashboard UI\nRelevant paths: app/dashboard.tsx, app/styles.css"
        )

        self.assertEqual(decision.cluster_name, "Jazz")
        self.assertGreater(decision.score, 0)
        self.assertTrue(any("artifact signal" in reason or "keyword hits" in reason for reason in decision.reasons))

    def test_speed_profile_prefers_fast_model_variants_when_scores_are_close(self) -> None:
        with patch.dict(os.environ, {"AUTOBOTS_MODEL_SELECTION_PROFILE": "speed"}):
            catalog = ClusterCatalog(
                available_model_ids=[
                    "nvidia/nemotron-4-340b-instruct",
                    "nvidia/step-3.5-flash",
                ],
                refresh_live=False,
            )

        lead, reviewer, _ = catalog.select_models("Optimus", "plan roadmap phase")
        self.assertEqual(lead.model_id, "nvidia/step-3.5-flash")
        self.assertEqual(reviewer.model_id, "nvidia/nemotron-4-340b-instruct")


class Phase8PlanningTests(unittest.TestCase):
    def test_cluster_plan_exposes_explicit_roles_and_routing_rationale(self) -> None:
        catalog = ClusterCatalog(refresh_live=False)
        planner = ClusterPlanner(catalog=catalog)
        phase = PhaseRecord(
            line_index=0,
            raw_line="- [ ] P5 | Harden API auth",
            title="P5 | Harden API auth",
            status="PENDING",
        )
        roadmap = (
            "## P5 | Harden API auth\n"
            "Goal: tighten auth\n"
            "Relevant paths: src/auth.py, tests/test_auth.py\n"
            "Validation: python -m pytest -q\n"
            "Acceptance: auth checks pass\n"
        )

        plan = planner.build_cluster_plan(phase, roadmap)

        self.assertEqual(plan.primary_cluster, "UltraMagnus")
        self.assertTrue(plan.routing_rationale)
        self.assertEqual([assignment.role_name for assignment in plan.role_assignments], ["planner", "implementer", "reviewer", "repair"])

    def test_parallel_planning_groups_independent_roots_when_enabled(self) -> None:
        catalog = ClusterCatalog(refresh_live=False)
        with patch.dict(os.environ, {"AUTOBOTS_ENABLE_PARALLEL_PLANNING": "1"}):
            planner = ClusterPlanner(catalog=catalog)

        phase = PhaseRecord(
            line_index=0,
            raw_line="- [ ] P6 | Cross-stack changes",
            title="P6 | Cross-stack changes",
            status="PENDING",
        )
        roadmap = (
            "## P6 | Cross-stack changes\n"
            "Goal: update UI and API\n"
            "Relevant paths: app/dashboard.tsx, src/service.py, tests/test_service.py\n"
            "Validation: python -m pytest -q\n"
            "Acceptance: dashboard and API both work\n"
        )

        plan = planner.build_cluster_plan(phase, roadmap)

        self.assertGreaterEqual(len(plan.parallel_workstreams), 2)
        self.assertEqual(plan.merge_strategy, "sequential_apply")
        self.assertTrue(any(stream.assigned_cluster == "Jazz" for stream in plan.parallel_workstreams))


class Phase8MergeStrategyTests(unittest.TestCase):
    def test_sequential_merge_keeps_last_file_override(self) -> None:
        merger = MergeStrategy("sequential_apply")
        branches = [
            {"files": [{"root": "src", "path": "a.ts", "content": "first"}]},
            {"files": [{"root": "src", "path": "b.ts", "content": "second"}]},
            {"files": [{"root": "src", "path": "a.ts", "content": "third"}]},
        ]
        result = merger.merge_file_sets(branches)
        self.assertEqual(len(result), 2)
        a_file = next(f for f in result if f["path"] == "a.ts")
        self.assertEqual(a_file["content"], "third")

    def test_union_merge_keeps_unique_files(self) -> None:
        merger = MergeStrategy("union_files")
        branches = [
            {"files": [{"root": "src", "path": "a.ts", "content": "first"}]},
            {"files": [{"root": "src", "path": "b.ts", "content": "second"}]},
        ]
        result = merger.merge_file_sets(branches)
        self.assertEqual(len(result), 2)
        paths = {f["path"] for f in result}
        self.assertEqual(paths, {"a.ts", "b.ts"})

    def test_consensus_only_keeps_agreed_files(self) -> None:
        merger = MergeStrategy("consensus")
        branches = [
            {"files": [{"root": "src", "path": "a.ts", "content": "same"}]},
            {"files": [{"root": "src", "path": "a.ts", "content": "same"}]},
            {"files": [{"root": "src", "path": "a.ts", "content": "same"}]},
        ]
        result = merger.merge_file_sets(branches)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], "same")

    def test_consensus_drops_disputed_files(self) -> None:
        merger = MergeStrategy("consensus")
        branches = [
            {"files": [{"root": "src", "path": "a.ts", "content": "same"}]},
            {"files": [{"root": "src", "path": "a.ts", "content": "same"}]},
            {"files": [{"root": "src", "path": "a.ts", "content": "diff"}]},
        ]
        result = merger.merge_file_sets(branches)
        self.assertEqual(len(result), 0)

    def test_plan_provides_merger_property(self) -> None:
        catalog = ClusterCatalog(refresh_live=False)
        planner = ClusterPlanner(catalog=catalog)
        phase = PhaseRecord(
            line_index=0,
            raw_line="- [ ] P7 | Test merge",
            title="P7 | Test merge",
            status="PENDING",
        )
        plan = planner.build_cluster_plan(phase, "## P7 | Test merge")
        self.assertIsInstance(plan.merger, MergeStrategy)
        self.assertIn(plan.merge_strategy, ("sequential_apply", "single_branch"))

    def test_plan_with_parallel_streams_uses_sequential_apply(self) -> None:
        catalog = ClusterCatalog(refresh_live=False)
        with patch.dict(os.environ, {"AUTOBOTS_ENABLE_PARALLEL_PLANNING": "1"}):
            planner = ClusterPlanner(catalog=catalog)
        phase = PhaseRecord(
            line_index=0,
            raw_line="- [ ] P8 | Multi-root",
            title="P8 | Multi-root",
            status="PENDING",
        )
        roadmap = "## P8 | Multi-root\nRelevant paths: app/a.ts, src/b.ts, tests/c.ts"
        plan = planner.build_cluster_plan(phase, roadmap)
        self.assertGreaterEqual(len(plan.parallel_workstreams), 2)
        self.assertEqual(plan.merge_strategy, "sequential_apply")
        self.assertEqual(plan.merge_strategy, plan.merger.mode)


if __name__ == "__main__":
    unittest.main()
