from __future__ import annotations

import random
from typing import Dict, List

from server.domain import ActionRequest, GameSession, PlayerState, Unit
from server.maps import get_map
from server.persistence import Repository
from server.snapshot import save_snapshot


class GameService:
    def __init__(self, repository: Repository, sessions: Dict[str, GameSession] | None = None, seed: int = 7) -> None:
        self.repository = repository
        self.sessions = sessions or default_sessions()
        self._rng = random.Random(seed)

    def submit_action(self, action: ActionRequest) -> dict:
        session = self.sessions.get(action.session_id)
        if session is None:
            reason = "session does not exist"
            self.repository.persist_action(action, accepted=False, reason=reason)
            return {
                "accepted": False,
                "reason": reason,
                "state": None,
                "analytics": self.repository.analytics_snapshot(action.session_id),
            }

        validation = session.apply_action(action)
        self.repository.persist_action(action, validation.accepted, validation.reason)
        return {
            "accepted": validation.accepted,
            "reason": validation.reason,
            "state": session.state_payload() if validation.accepted else None,
            "analytics": self.repository.analytics_snapshot(action.session_id),
        }

    def tick_bots(self, session_id: str, tick: int) -> List[dict]:
        session = self.sessions.get(session_id)
        if session is None:
            return []

        bot_results = []
        for player in session.players.values():
            if not player.is_bot:
                continue
            action = self._choose_bot_action(session, player.player_id, tick)
            if action is None:
                continue
            bot_results.append(self.submit_action(action))
        return bot_results

    def get_state(self, session_id: str) -> dict:
        session = self.sessions.get(session_id)
        if session is None:
            return {"error": "session not found"}
        return {
            "state": session.state_payload(),
            "analytics": self.repository.analytics_snapshot(session_id),
        }

    def get_metrics(self, session_id: str) -> dict:
        session = self.sessions.get(session_id)
        if session is None:
            return {"error": "session not found"}

        units_by_domain = {"land": 0, "air": 0, "water": 0}
        for unit in session.units.values():
            units_by_domain[unit.domain] = units_by_domain.get(unit.domain, 0) + 1

        return {
            "session_id": session_id,
            "tick": session.tick,
            "unit_counts": session.unit_counts(),
            "units_by_domain": units_by_domain,
            "players": len(session.players),
            "bots": len([p for p in session.players.values() if p.is_bot]),
            "analytics": self.repository.analytics_snapshot(session_id),
        }

    def create_snapshot(self, session_id: str, target_path: str | None = None) -> dict:
        state = self.get_state(session_id)
        if "error" in state:
            return state
        location = save_snapshot(state, session_id=session_id, target_path=target_path)
        return {"snapshot_path": location, "session_id": session_id}

    def list_sessions(self) -> dict:
        summaries = []
        for session in self.sessions.values():
            summaries.append(
                {
                    "session_id": session.session_id,
                    "map": session.game_map.name,
                    "tick": session.tick,
                    "players": len(session.players),
                    "bots": len([p for p in session.players.values() if p.is_bot]),
                    "units": len(session.units),
                }
            )
        summaries.sort(key=lambda x: x["session_id"])
        return {"sessions": summaries, "total_sessions": len(summaries)}

    def _choose_bot_action(self, session: GameSession, player_id: str, tick: int) -> ActionRequest | None:
        units = [u for u in session.units.values() if u.owner_player_id == player_id]
        if not units:
            return None
        unit = self._rng.choice(units)
        candidates = [
            (unit.x + 1, unit.y),
            (unit.x - 1, unit.y),
            (unit.x, unit.y + 1),
            (unit.x, unit.y - 1),
        ]
        self._rng.shuffle(candidates)
        for tx, ty in candidates:
            if session.game_map.in_bounds(tx, ty):
                return ActionRequest(
                    session_id=session.session_id,
                    player_id=player_id,
                    tick=tick,
                    action_type="move",
                    unit_id=unit.unit_id,
                    target_x=tx,
                    target_y=ty,
                )
        return None


def _build_player(player_id: str, is_bot: bool = False) -> PlayerState:
    return PlayerState(player_id=player_id, is_bot=is_bot)


def default_sessions() -> Dict[str, GameSession]:
    islands = get_map("islands")
    desert = get_map("desert")
    archipelago = get_map("archipelago")

    return {
        "demo": GameSession(
            session_id="demo",
            tick=0,
            game_map=islands,
            players={
                "p-1": _build_player("p-1"),
                "p-2": _build_player("p-2"),
                "bot-1": _build_player("bot-1", is_bot=True),
            },
            units={
                "u-1": Unit("u-1", "p-1", "land_infantry", "land", 4, 4, 55),
                "u-2": Unit("u-2", "p-2", "land_tank", "land", 13, 13, 180),
                "u-3": Unit("u-3", "bot-1", "air_scout", "air", 9, 9, 65),
                "u-4": Unit("u-4", "p-1", "water_destroyer", "water", 0, 0, 210),
            },
        ),
        "desert-war": GameSession(
            session_id="desert-war",
            tick=0,
            game_map=desert,
            players={
                "p-a": _build_player("p-a"),
                "p-b": _build_player("p-b"),
                "bot-desert": _build_player("bot-desert", is_bot=True),
            },
            units={
                "u-10": Unit("u-10", "p-a", "land_artillery", "land", 2, 2, 130),
                "u-11": Unit("u-11", "p-b", "land_sniper", "land", 17, 17, 70),
                "u-12": Unit("u-12", "bot-desert", "air_fighter", "air", 8, 8, 100),
            },
        ),
        "blue-front": GameSession(
            session_id="blue-front",
            tick=0,
            game_map=archipelago,
            players={
                "admiral": _build_player("admiral"),
                "raider": _build_player("raider"),
                "bot-fleet": _build_player("bot-fleet", is_bot=True),
            },
            units={
                "u-20": Unit("u-20", "admiral", "water_submarine", "water", 1, 1, 140),
                "u-21": Unit("u-21", "raider", "water_battleship", "water", 23, 23, 320),
                "u-22": Unit("u-22", "bot-fleet", "water_destroyer", "water", 12, 12, 210),
            },
        ),
    }
