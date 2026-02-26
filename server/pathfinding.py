from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

from server.models import MapModel

Coord = Tuple[int, int]


def _neighbors(x: int, y: int) -> List[Coord]:
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def _heuristic(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def terrain_allowed(unit_domain: str, tile: str) -> bool:
    if unit_domain == "air":
        return True
    if unit_domain == "land":
        return tile == "land"
    if unit_domain == "water":
        return tile == "water"
    return False


def astar_path(game_map: MapModel, start: Coord, goal: Coord, unit_domain: str) -> Optional[List[Coord]]:
    if not game_map.in_bounds(*start) or not game_map.in_bounds(*goal):
        return None
    if not terrain_allowed(unit_domain, game_map.tile(*goal)):
        return None

    open_heap: List[Tuple[int, Coord]] = [(0, start)]
    came_from: Dict[Coord, Coord] = {}
    g_score: Dict[Coord, int] = {start: 0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            return _reconstruct(came_from, current)

        for nxt in _neighbors(*current):
            x, y = nxt
            if not game_map.in_bounds(x, y):
                continue
            if not terrain_allowed(unit_domain, game_map.tile(x, y)):
                continue

            tentative = g_score[current] + 1
            if tentative < g_score.get(nxt, 10**9):
                came_from[nxt] = current
                g_score[nxt] = tentative
                heapq.heappush(open_heap, (tentative + _heuristic(nxt, goal), nxt))

    return None


def raytrace_line(start: Coord, end: Coord) -> List[Coord]:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    points: List[Coord] = []
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return points


def _reconstruct(came_from: Dict[Coord, Coord], current: Coord) -> List[Coord]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
