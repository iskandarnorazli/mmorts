from __future__ import annotations

import argparse
import json
from urllib import request


def _post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def post_action(server_url: str, payload: dict) -> dict:
    return _post_json(f"{server_url.rstrip('/')}/actions", payload)


def tick_bots(server_url: str, session_id: str, tick: int) -> dict:
    return _post_json(f"{server_url.rstrip('/')}/bots/tick", {"session_id": session_id, "tick": tick})


def get_state(server_url: str, session_id: str) -> dict:
    url = f"{server_url.rstrip('/')}/state?session_id={session_id}"
    with request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="MMORTS client")
    parser.add_argument("--server-url", default="http://localhost:8080")
    parser.add_argument("--session-id", default="demo")
    parser.add_argument("--player-id", default="p-1")
    parser.add_argument("--unit-id", default="u-1")
    parser.add_argument("--tick", type=int, default=1)
    parser.add_argument("--action", default="move", choices=["move", "fire", "spawn_unit", "create_group", "assign_group", "mine"])
    parser.add_argument("--x", type=int, default=5)
    parser.add_argument("--y", type=int, default=4)
    parser.add_argument("--group-id", default="alpha")
    parser.add_argument("--unit-ids", default="u-1")
    parser.add_argument("--unit-type", default="land_infantry")
    parser.add_argument("--resource-type", default="metal")
    parser.add_argument("--tick-bots", action="store_true")
    args = parser.parse_args()

    action = {
        "session_id": args.session_id,
        "player_id": args.player_id,
        "tick": args.tick,
        "action_type": args.action,
        "unit_id": args.unit_id,
        "target_x": args.x,
        "target_y": args.y,
        "group_id": args.group_id,
        "unit_ids": [u.strip() for u in args.unit_ids.split(",") if u.strip()],
        "unit_type": args.unit_type,
        "resource_type": args.resource_type,
    }
    print(json.dumps(post_action(args.server_url, action), indent=2))
    if args.tick_bots:
        print(json.dumps(tick_bots(args.server_url, args.session_id, args.tick), indent=2))
    print(json.dumps(get_state(args.server_url, args.session_id), indent=2))


if __name__ == "__main__":
    main()
