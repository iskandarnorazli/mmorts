from __future__ import annotations

from typing import Dict, List, Tuple

from server.models import MapModel, ResourceNode

Coord = Tuple[int, int]


def _fill(width: int, height: int, tile: str) -> List[List[str]]:
    return [[tile for _ in range(width)] for _ in range(height)]


def _nodes(ore: Dict[Coord, int], oil: Dict[Coord, int], food: Dict[Coord, int]) -> Dict[Coord, ResourceNode]:
    result: Dict[Coord, ResourceNode] = {}
    for k, v in ore.items():
        result[k] = ResourceNode("metal", v)
    for k, v in oil.items():
        result[k] = ResourceNode("energy", v)
    for k, v in food.items():
        result[k] = ResourceNode("food", v)
    return result


def islands_map() -> MapModel:
    terrain = _fill(20, 20, "water")
    for y in range(3, 9):
        for x in range(2, 8):
            terrain[y][x] = "land"
    for y in range(10, 17):
        for x in range(11, 18):
            terrain[y][x] = "land"
    for y in range(7, 13):
        for x in range(8, 12):
            terrain[y][x] = "land"
    return MapModel(
        name="islands",
        width=20,
        height=20,
        terrain=terrain,
        resources=_nodes({(4, 4): 500, (13, 13): 600, (9, 10): 400}, {(5, 7): 400, (15, 14): 500}, {(3, 6): 350, (14, 12): 400}),
    )


def desert_map() -> MapModel:
    terrain = _fill(20, 20, "land")
    for y in range(0, 20):
        terrain[y][9] = "water"
        terrain[y][10] = "water"
    for y in range(8, 12):
        terrain[y][9] = "land"
        terrain[y][10] = "land"
    return MapModel(
        name="desert",
        width=20,
        height=20,
        terrain=terrain,
        resources=_nodes({(2, 2): 700, (17, 17): 700, (8, 9): 300}, {(6, 15): 650, (14, 4): 650}, {(4, 10): 300, (15, 10): 300}),
    )


def archipelago_map() -> MapModel:
    terrain = _fill(24, 24, "water")
    islands = [(2, 2, 6, 6), (10, 3, 14, 8), (16, 12, 22, 18), (4, 15, 9, 21), (12, 18, 16, 22)]
    for x0, y0, x1, y1 in islands:
        for y in range(y0, y1):
            for x in range(x0, x1):
                terrain[y][x] = "land"
    return MapModel(
        name="archipelago",
        width=24,
        height=24,
        terrain=terrain,
        resources=_nodes({(3, 3): 350, (11, 4): 300, (18, 15): 450, (6, 17): 400}, {(5, 5): 300, (19, 16): 450, (13, 20): 250}, {(4, 4): 300, (12, 6): 250, (17, 14): 350, (7, 19): 250}),
    )


def get_map(name: str) -> MapModel:
    maps = {"islands": islands_map, "desert": desert_map, "archipelago": archipelago_map}
    if name not in maps:
        raise ValueError(f"unknown map: {name}")
    return maps[name]()
