from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

Coord = Tuple[int, int]


@dataclass
class UnitModel:
    unit_type: str
    domain: str
    hp: int
    speed: int
    attack_damage: int
    attack_range: int
    metal: int
    energy: int
    food: int
    upkeep: Tuple[int, int, int]
    attack_domains: Tuple[str, ...]
    bullet_drop: bool = False
    aoe_radius: int = 0


@dataclass
class ResourceNode:
    resource_type: str
    amount: int


@dataclass
class MapModel:
    name: str
    width: int
    height: int
    terrain: List[List[str]]
    resources: Dict[Coord, ResourceNode] = field(default_factory=dict)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, x: int, y: int) -> str:
        return self.terrain[y][x]


UNIT_MODELS: Dict[str, UnitModel] = {
    "land_artillery": UnitModel("land_artillery", "land", 130, 2, 70, 8, 120, 60, 4, (2, 3, 1), attack_domains=("land", "water"), bullet_drop=True, aoe_radius=2),
    "land_sniper": UnitModel("land_sniper", "land", 70, 3, 55, 10, 50, 20, 2, (1, 1, 1), attack_domains=("land",), bullet_drop=False, aoe_radius=0),
    "land_tank": UnitModel("land_tank", "land", 180, 2, 40, 6, 160, 80, 3, (3, 3, 1), attack_domains=("land", "water"), bullet_drop=False, aoe_radius=1),
    "land_infantry": UnitModel("land_infantry", "land", 55, 3, 18, 4, 20, 10, 2, (0, 1, 1), attack_domains=("land",), bullet_drop=True, aoe_radius=0),
    "air_scout": UnitModel("air_scout", "air", 65, 5, 14, 4, 70, 100, 2, (1, 4, 1), attack_domains=("air",), bullet_drop=False, aoe_radius=0),
    "air_bomber": UnitModel("air_bomber", "air", 120, 4, 65, 7, 180, 160, 3, (3, 5, 1), attack_domains=("land", "water"), bullet_drop=True, aoe_radius=2),
    "air_fighter": UnitModel("air_fighter", "air", 100, 5, 36, 6, 130, 130, 2, (2, 4, 1), attack_domains=("air",), bullet_drop=False, aoe_radius=0),
    "water_submarine": UnitModel("water_submarine", "water", 140, 3, 44, 7, 170, 90, 2, (2, 3, 1), attack_domains=("water",), bullet_drop=False, aoe_radius=1),
    "water_destroyer": UnitModel("water_destroyer", "water", 210, 2, 56, 8, 240, 130, 5, (4, 4, 1), attack_domains=("water", "air"), bullet_drop=False, aoe_radius=1),
    "water_aircraft_carrier": UnitModel("water_aircraft_carrier", "water", 350, 1, 50, 9, 500, 300, 8, (6, 7, 2), attack_domains=("air", "water"), bullet_drop=False, aoe_radius=1),
    "water_battleship": UnitModel("water_battleship", "water", 320, 2, 62, 9, 420, 240, 6, (5, 6, 2), attack_domains=("land", "water"), bullet_drop=True, aoe_radius=2),
}
