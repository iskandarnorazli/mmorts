# Progress

- Reworked simulation domain to include players, groups, bots, resources, and expanded unit classes.
- Added three map templates (`islands`, `desert`, `archipelago`) with ore/oil/plantation nodes.
- Implemented A* pathfinding and terrain compatibility checks for land, air, and water units.
- Added actions for grouping, spawning units, mining resources, and bot ticks.
- Added durability test suite with memory tracking (`tracemalloc`) and network-byte analytics checks.
- Added offline simulation entrypoint for local no-server testing.
- Updated README and created `awandb.md` with an extensive improvement critique.
- Added collision-aware movement/spawn validation and combat damage registration with bullet-drop and AoE behaviors.
- Added web viewer rendering and snapshot export endpoint for war-state review.
