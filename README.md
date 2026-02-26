# MMORTS AwanDB HTAP Prototype (Python, Expanded)

This repository contains a larger Python MMORTS prototype designed to showcase AwanDB-friendly HTAP flows with:

- Multiplayer sessions (human + bot players)
- Expanded land/air/water unit roster
- Group management for player squads
- Resource economy (metal, energy, food)
- Map templates (islands, desert, archipelago)
- Server-side authoritative validation + A* pathfinding
- Projectile path/ray tracing for combat actions, collision checks, bullet-drop weapons, and AoE damage
- Durability/load-oriented tests (memory + traffic + action throughput)
- Offline simulation mode for local testing without HTTP server

## Unit classes

### Land
- `land_artillery`
- `land_sniper`
- `land_tank`
- `land_infantry`

### Air
- `air_scout`
- `air_bomber`
- `air_fighter`

### Water
- `water_submarine`
- `water_destroyer`
- `water_aircraft_carrier`
- `water_battleship`

Each unit has build costs and upkeep consumption (`metal`, `energy`, `food`).

## Gameplay actions

Supported server-side actions:
- `move` (pathfinding + terrain constraints)
- `fire` (projectile ray tracing + collision detection + damage registration, with bullet drop and AoE for selected weapons, plus domain-based targeting rules (e.g. some units cannot hit air/water))
- `create_group`
- `assign_group`
- `spawn_unit`
- `mine` (`metal`, `energy`, `food`)

All actions are validated and persisted; analytics snapshots include accepted/rejected counts and network byte estimates.

## HTTP API

- `POST /actions` – submit one action request.
- `POST /bots/tick` – tick bot players in a given session/tick.
- `GET /state?session_id=...` – fetch authoritative state + analytics.
- `GET /metrics?session_id=...` – fetch operational metrics (players, bots, units by type/domain, analytics).
- `GET /sessions` – list all available sessions with map/player/unit summaries.
- `POST /snapshot` – export a war-state snapshot to JSON for later review.

Invalid JSON and malformed action payloads now return `400` with an error message.

## Project structure

- `server/` authoritative logic, models (units/maps), pathfinding+rays, persistence, HTTP server, offline simulator
- `client/` CLI client for action submissions
- `tests/` domain, service, and durability tests
- `.vscode/tasks.json` terminal tasks
- `Plan.md` implementation plan
- `Progress.md` implementation progress
- `awandb.md` 2000+ word improvement critique for AwanDB

## Run

### Tests
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Online server mode
```bash
python -m server.app
```

### Client example (move)
```bash
python -m client.client --session-id demo --player-id p-1 --unit-id u-1 --tick 1 --action move --x 5 --y 4 --tick-bots
```

### Offline simulation
```bash
python -m server.offline_sim
```

### Render verification (web viewer)
```bash
python -m server.app
python -m http.server 9000
# open http://localhost:9000/client/web/index.html and click Refresh
```

## AwanDB integration

To use AwanDB Flight SQL, set:

- `AWANDB_ENDPOINT` (e.g. `grpc://localhost:3000`)
- `AWANDB_USERNAME` (default: `admin`)
- `AWANDB_PASSWORD` (default: `admin`)

If unavailable/failing, system falls back to in-memory storage.

## Scale notes

This remains a prototype, but now includes system boundaries useful for bigger scaling efforts:

- map-based spatial logic and traversal constraints
- bot step execution hooks
- resource economy accounting
- load/durability baselines with memory and traffic metrics

Next production steps: sharded simulation workers, distributed queues, snapshot/delta replication, anti-cheat audit trails, and stricter transactional batching per frame.
