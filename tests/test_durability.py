import tracemalloc
import unittest

from server.domain import ActionRequest
from server.persistence import InMemoryRepository
from server.service import GameService


class DurabilityTests(unittest.TestCase):
    def test_multiplayer_load_and_memory_metrics(self):
        repo = InMemoryRepository()
        service = GameService(repository=repo)

        tracemalloc.start()
        tick = 1
        players = ["p-1", "p-2"]

        for i in range(120):
            player = players[i % len(players)]
            unit_id = "u-1" if player == "p-1" else "u-2"
            x = 5 if player == "p-1" else 12
            y = 4 if player == "p-1" else 13
            service.submit_action(
                ActionRequest(
                    session_id="demo",
                    player_id=player,
                    tick=tick,
                    action_type="move",
                    unit_id=unit_id,
                    target_x=x,
                    target_y=y,
                )
            )
            tick += 1

        # add bot ticks too
        for t in range(tick, tick + 50):
            service.tick_bots("demo", t)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        state = service.get_state("demo")
        analytics = state["analytics"]
        unit_counts = state["state"]["unit_counts"]

        self.assertGreaterEqual(analytics["total_actions"], 170)
        self.assertGreater(analytics["network_bytes"], 1000)
        self.assertLess(peak, 20 * 1024 * 1024)  # should stay below 20MB for this test
        self.assertGreaterEqual(sum(unit_counts.values()), 4)


if __name__ == "__main__":
    unittest.main()
