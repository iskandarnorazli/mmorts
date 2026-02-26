from __future__ import annotations

import json

from server.domain import ActionRequest
from server.persistence import InMemoryRepository
from server.service import GameService


def run_offline_demo() -> None:
    service = GameService(repository=InMemoryRepository())
    scripted_actions = [
        ActionRequest("demo", "p-1", 1, "create_group", group_id="alpha"),
        ActionRequest("demo", "p-1", 2, "assign_group", group_id="alpha", unit_ids=["u-1"]),
        ActionRequest("demo", "p-1", 3, "move", unit_id="u-1", target_x=5, target_y=4),
        ActionRequest("demo", "p-1", 4, "mine", unit_id="u-1", resource_type="metal"),
        ActionRequest("demo", "p-1", 5, "fire", unit_id="u-1", target_x=7, target_y=4),
        ActionRequest("demo", "p-2", 1, "spawn_unit", unit_type="air_bomber", target_x=13, target_y=13),
    ]

    for action in scripted_actions:
        print(json.dumps(service.submit_action(action), indent=2))

    print(json.dumps({"bots": service.tick_bots("demo", tick=5)}, indent=2))
    print(json.dumps(service.get_state("demo"), indent=2))


if __name__ == "__main__":
    run_offline_demo()
