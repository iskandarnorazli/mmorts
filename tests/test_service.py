import unittest

from server.domain import ActionRequest
from server.persistence import InMemoryRepository
from server.service import GameService


class GameServiceTests(unittest.TestCase):
    def test_persists_validated_action_and_returns_htap_snapshot(self):
        repo = InMemoryRepository()
        service = GameService(repository=repo)

        result = service.submit_action(
            ActionRequest(
                session_id="demo",
                player_id="p-1",
                tick=1,
                action_type="move",
                unit_id="u-1",
                target_x=5,
                target_y=4,
            )
        )

        self.assertTrue(result["accepted"])
        self.assertEqual(1, result["analytics"]["accepted_actions"])
        self.assertGreater(result["analytics"]["network_bytes"], 0)

    def test_bot_tick_returns_results(self):
        repo = InMemoryRepository()
        service = GameService(repository=repo)

        results = service.tick_bots("demo", tick=3)

        self.assertGreaterEqual(len(results), 1)

    def test_metrics_include_domain_counts_and_player_counts(self):
        repo = InMemoryRepository()
        service = GameService(repository=repo)

        metrics = service.get_metrics("demo")

        self.assertEqual("demo", metrics["session_id"])
        self.assertIn("units_by_domain", metrics)
        self.assertEqual(3, metrics["players"])
        self.assertEqual(1, metrics["bots"])

    def test_list_sessions_returns_expected_catalog(self):
        repo = InMemoryRepository()
        service = GameService(repository=repo)

        payload = service.list_sessions()

        self.assertGreaterEqual(payload["total_sessions"], 3)
        ids = [entry["session_id"] for entry in payload["sessions"]]
        self.assertIn("demo", ids)

    def test_create_snapshot_returns_path(self):
        repo = InMemoryRepository()
        service = GameService(repository=repo)

        result = service.create_snapshot("demo", target_path="snapshots/service_snapshot.json")

        self.assertIn("snapshot_path", result)
        self.assertEqual("demo", result["session_id"])


if __name__ == "__main__":
    unittest.main()
