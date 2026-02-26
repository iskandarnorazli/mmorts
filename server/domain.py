from __future__ import annotations

from dataclasses import dataclass, field
from math import dist
from typing import Dict, List, Tuple

from server.models import MapModel, UNIT_MODELS
from server.pathfinding import astar_path, raytrace_line

Coord = Tuple[int, int]


@dataclass(frozen=True)
class ActionRequest:
    session_id: str
    player_id: str
    tick: int
    action_type: str
    unit_id: str = ""
    target_x: int = 0
    target_y: int = 0
    group_id: str = ""
    unit_ids: List[str] = field(default_factory=list)
    unit_type: str = ""
    resource_type: str = ""


@dataclass
class ValidationResult:
    accepted: bool
    reason: str = ""


@dataclass
class Resources:
    metal: int
    energy: int
    food: int


@dataclass
class PlayerState:
    player_id: str
    is_bot: bool = False
    resources: Resources = field(default_factory=lambda: Resources(500, 500, 500))
    groups: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class Unit:
    unit_id: str
    owner_player_id: str
    unit_type: str
    domain: str
    x: int
    y: int
    hp: int


@dataclass
class GameSession:
    session_id: str
    tick: int
    game_map: MapModel
    players: Dict[str, PlayerState]
    units: Dict[str, Unit]
    latest_tick_by_player: Dict[str, int] = field(default_factory=dict)
    next_unit_index: int = 1000

    def apply_action(self, action: ActionRequest) -> ValidationResult:
        if action.player_id not in self.players:
            return ValidationResult(False, "player does not exist")

        latest_tick = self.latest_tick_by_player.get(action.player_id, -1)
        if action.tick <= latest_tick:
            return ValidationResult(False, "tick must increase per player")

        result = self._dispatch(action)
        if result.accepted:
            self.latest_tick_by_player[action.player_id] = action.tick
            self.tick = max(self.tick, action.tick)
            self._apply_upkeep()
        return result

    def _dispatch(self, action: ActionRequest) -> ValidationResult:
        if action.action_type == "move":
            return self._move(action)
        if action.action_type == "fire":
            return self._fire_projectile(action)
        if action.action_type == "create_group":
            return self._create_group(action)
        if action.action_type == "assign_group":
            return self._assign_group(action)
        if action.action_type == "spawn_unit":
            return self._spawn_unit(action)
        if action.action_type == "mine":
            return self._mine(action)
        return ValidationResult(False, f"unsupported action_type: {action.action_type}")

    def _move(self, action: ActionRequest) -> ValidationResult:
        unit = self.units.get(action.unit_id)
        if unit is None:
            return ValidationResult(False, "unit missing")
        if unit.owner_player_id != action.player_id:
            return ValidationResult(False, "unit does not belong to player")
        if self._unit_at((action.target_x, action.target_y), exclude_unit=action.unit_id) is not None:
            return ValidationResult(False, "target tile occupied (collision)")

        path = astar_path(self.game_map, (unit.x, unit.y), (action.target_x, action.target_y), unit.domain)
        if path is None:
            return ValidationResult(False, "no valid path")

        max_steps = UNIT_MODELS[unit.unit_type].speed
        if len(path) - 1 > max_steps:
            return ValidationResult(False, "path too long for one tick")

        unit.x, unit.y = action.target_x, action.target_y
        return ValidationResult(True, "accepted")

    def _fire_projectile(self, action: ActionRequest) -> ValidationResult:
        shooter = self.units.get(action.unit_id)
        if shooter is None:
            return ValidationResult(False, "shooter missing")
        if shooter.owner_player_id != action.player_id:
            return ValidationResult(False, "shooter does not belong to player")

        model = UNIT_MODELS[shooter.unit_type]
        target_distance = dist((shooter.x, shooter.y), (action.target_x, action.target_y))
        if target_distance > model.attack_range:
            return ValidationResult(False, "target out of range")

        ray = raytrace_line((shooter.x, shooter.y), (action.target_x, action.target_y))
        impact_index = len(ray) - 1
        if model.bullet_drop and len(ray) > 3:
            drop_steps = max(0, int(target_distance // 3))
            impact_index = max(1, impact_index - drop_steps)

        impact_point = ray[impact_index]

        direct_target = None
        for point in ray[1 : impact_index + 1]:
            collider = self._unit_at(point, exclude_unit=shooter.unit_id)
            if collider is not None:
                direct_target = collider
                impact_point = point
                break

        hit_units: List[str] = []
        if direct_target is not None and direct_target.owner_player_id != shooter.owner_player_id and self._can_attack(model, direct_target):
            self._apply_damage(direct_target.unit_id, model.attack_damage)
            hit_units.append(direct_target.unit_id)

        if model.aoe_radius > 0:
            for unit in list(self.units.values()):
                if unit.unit_id == shooter.unit_id:
                    continue
                if unit.owner_player_id == shooter.owner_player_id:
                    continue
                if direct_target and unit.unit_id == direct_target.unit_id:
                    continue
                if not self._can_attack(model, unit):
                    continue
                if dist((unit.x, unit.y), impact_point) <= model.aoe_radius:
                    splash_damage = max(1, model.attack_damage // 2)
                    self._apply_damage(unit.unit_id, splash_damage)
                    hit_units.append(unit.unit_id)

        if hit_units:
            return ValidationResult(True, f"impact@{impact_point} hits {','.join(sorted(set(hit_units)))}")

        if model.bullet_drop and impact_point != (action.target_x, action.target_y):
            return ValidationResult(True, "projectile dropped before target")
        return ValidationResult(True, "projectile missed")

    def _can_attack(self, attacker_model, target: Unit) -> bool:
        return target.domain in attacker_model.attack_domains

    def _apply_damage(self, unit_id: str, damage: int) -> None:
        target = self.units.get(unit_id)
        if target is None:
            return
        target.hp -= damage
        if target.hp <= 0:
            del self.units[target.unit_id]

    def _unit_at(self, point: Coord, exclude_unit: str) -> Unit | None:
        for unit in self.units.values():
            if unit.unit_id == exclude_unit:
                continue
            if (unit.x, unit.y) == point:
                return unit
        return None

    def _create_group(self, action: ActionRequest) -> ValidationResult:
        player = self.players[action.player_id]
        if not action.group_id:
            return ValidationResult(False, "group_id required")
        if action.group_id in player.groups:
            return ValidationResult(False, "group already exists")
        player.groups[action.group_id] = []
        return ValidationResult(True, "accepted")

    def _assign_group(self, action: ActionRequest) -> ValidationResult:
        player = self.players[action.player_id]
        if action.group_id not in player.groups:
            return ValidationResult(False, "group does not exist")

        for unit_id in action.unit_ids:
            unit = self.units.get(unit_id)
            if unit is None or unit.owner_player_id != action.player_id:
                return ValidationResult(False, "invalid unit in assignment")
        player.groups[action.group_id] = list(sorted(set(action.unit_ids)))
        return ValidationResult(True, "accepted")

    def _spawn_unit(self, action: ActionRequest) -> ValidationResult:
        model = UNIT_MODELS.get(action.unit_type)
        if model is None:
            return ValidationResult(False, "unknown unit_type")

        player = self.players[action.player_id]
        if not self.game_map.in_bounds(action.target_x, action.target_y):
            return ValidationResult(False, "spawn out of bounds")

        tile = self.game_map.tile(action.target_x, action.target_y)
        if model.domain == "land" and tile != "land":
            return ValidationResult(False, "land unit must spawn on land")
        if model.domain == "water" and tile != "water":
            return ValidationResult(False, "water unit must spawn on water")
        if self._unit_at((action.target_x, action.target_y), exclude_unit="") is not None:
            return ValidationResult(False, "spawn tile occupied (collision)")

        if player.resources.metal < model.metal or player.resources.energy < model.energy or player.resources.food < model.food:
            return ValidationResult(False, "insufficient resources")

        player.resources.metal -= model.metal
        player.resources.energy -= model.energy
        player.resources.food -= model.food

        unit_id = f"u-{self.next_unit_index}"
        self.next_unit_index += 1
        self.units[unit_id] = Unit(unit_id, action.player_id, action.unit_type, model.domain, action.target_x, action.target_y, model.hp)
        return ValidationResult(True, "accepted")

    def _mine(self, action: ActionRequest) -> ValidationResult:
        unit = self.units.get(action.unit_id)
        if unit is None or unit.owner_player_id != action.player_id:
            return ValidationResult(False, "invalid mining unit")

        node = self.game_map.resources.get((unit.x, unit.y))
        if node is None:
            return ValidationResult(False, "no resource node")
        if node.resource_type != action.resource_type:
            return ValidationResult(False, "wrong resource type for node")
        if node.amount <= 0:
            return ValidationResult(False, "resource depleted")

        player = self.players[action.player_id]
        amount = min(25, node.amount)
        node.amount -= amount
        if action.resource_type == "metal":
            player.resources.metal += amount
        elif action.resource_type == "energy":
            player.resources.energy += amount
        elif action.resource_type == "food":
            player.resources.food += amount
        else:
            return ValidationResult(False, "unknown resource_type")

        return ValidationResult(True, "accepted")

    def _apply_upkeep(self) -> None:
        for unit in self.units.values():
            player = self.players[unit.owner_player_id]
            m = UNIT_MODELS[unit.unit_type]
            metal, energy, food = m.upkeep
            player.resources.metal = max(0, player.resources.metal - metal)
            player.resources.energy = max(0, player.resources.energy - energy)
            player.resources.food = max(0, player.resources.food - food)

    def unit_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for unit in self.units.values():
            counts[unit.unit_type] = counts.get(unit.unit_type, 0) + 1
        return counts

    def state_payload(self) -> dict:
        return {
            "session_id": self.session_id,
            "map": self.game_map.name,
            "tick": self.tick,
            "players": {
                pid: {
                    "is_bot": p.is_bot,
                    "resources": {"metal": p.resources.metal, "energy": p.resources.energy, "food": p.resources.food},
                    "groups": p.groups,
                }
                for pid, p in self.players.items()
            },
            "units": {
                uid: {
                    "owner_player_id": u.owner_player_id,
                    "unit_type": u.unit_type,
                    "domain": u.domain,
                    "x": u.x,
                    "y": u.y,
                    "hp": u.hp,
                }
                for uid, u in self.units.items()
            },
            "unit_counts": self.unit_counts(),
        }
