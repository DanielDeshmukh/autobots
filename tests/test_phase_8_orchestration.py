"""Tests for initial Phase 8 orchestration improvements."""

import os
import unittest
from unittest.mock import patch

from autobots.catalog import ClusterCatalog
from autobots.router.models import PhaseRecord
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


if __name__ == "__main__":
    unittest.main()
