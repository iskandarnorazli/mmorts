import unittest

from server.domain import ActionRequest, GameSession, PlayerState, Unit
from server.maps import get_map


class GameSessionValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = GameSession(
            session_id="demo",
            tick=0,
            game_map=get_map("islands"),
            players={"p-1": PlayerState("p-1"), "p-2": PlayerState("p-2")},
            units={
                "u-1": Unit(unit_id="u-1", owner_player_id="p-1", unit_type="land_infantry", domain="land", x=4, y=4, hp=55),
                "u-2": Unit(unit_id="u-2", owner_player_id="p-2", unit_type="land_tank", domain="land", x=13, y=13, hp=180),
                "u-3": Unit(unit_id="u-3", owner_player_id="p-1", unit_type="water_destroyer", domain="water", x=0, y=0, hp=210),
                "u-4": Unit(unit_id="u-4", owner_player_id="p-2", unit_type="land_sniper", domain="land", x=6, y=4, hp=70),
                "u-5": Unit(unit_id="u-5", owner_player_id="p-2", unit_type="land_infantry", domain="land", x=7, y=4, hp=55),
            },
        )

    def test_rejects_move_for_other_players_unit(self) -> None:
        action = ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="move", unit_id="u-2", target_x=14, target_y=13)
        result = self.session.apply_action(action)
        self.assertFalse(result.accepted)

    def test_rejects_move_into_occupied_tile(self) -> None:
        result = self.session.apply_action(
            ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="move", unit_id="u-1", target_x=6, target_y=4)
        )
        self.assertFalse(result.accepted)
        self.assertIn("occupied", result.reason)

    def test_group_create_and_assign(self) -> None:
        create = ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="create_group", group_id="alpha")
        assign = ActionRequest(session_id="demo", player_id="p-1", tick=2, action_type="assign_group", group_id="alpha", unit_ids=["u-1"])

        self.assertTrue(self.session.apply_action(create).accepted)
        self.assertTrue(self.session.apply_action(assign).accepted)
        self.assertEqual(["u-1"], self.session.players["p-1"].groups["alpha"])

    def test_spawn_and_resource_consumption(self) -> None:
        resources_before = self.session.players["p-1"].resources.metal
        action = ActionRequest(
            session_id="demo",
            player_id="p-1",
            tick=1,
            action_type="spawn_unit",
            unit_type="land_sniper",
            target_x=5,
            target_y=5,
        )
        result = self.session.apply_action(action)
        self.assertTrue(result.accepted)
        self.assertLess(self.session.players["p-1"].resources.metal, resources_before)

    def test_mine_metal(self) -> None:
        self.session.units["u-1"].x = 4
        self.session.units["u-1"].y = 4
        before = self.session.players["p-1"].resources.metal

        result = self.session.apply_action(
            ActionRequest(
                session_id="demo",
                player_id="p-1",
                tick=1,
                action_type="mine",
                unit_id="u-1",
                resource_type="metal",
            )
        )
        self.assertTrue(result.accepted)
        self.assertGreater(self.session.players["p-1"].resources.metal, before)

    def test_pathfinding_respects_terrain(self) -> None:
        result = self.session.apply_action(
            ActionRequest(
                session_id="demo",
                player_id="p-1",
                tick=1,
                action_type="move",
                unit_id="u-1",
                target_x=1,
                target_y=1,
            )
        )
        self.assertFalse(result.accepted)
        self.assertIn("path", result.reason)

    def test_projectile_raytrace_hits_and_registers_damage(self) -> None:
        result = self.session.apply_action(
            ActionRequest(
                session_id="demo",
                player_id="p-1",
                tick=1,
                action_type="fire",
                unit_id="u-1",
                target_x=7,
                target_y=4,
            )
        )
        self.assertTrue(result.accepted)
        self.assertIn("hits", result.reason)
        self.assertLess(self.session.units["u-4"].hp, 70)

    def test_sniper_has_no_drop_and_can_hit_long_line(self) -> None:
        self.session.units["u-4"].owner_player_id = "p-1"
        self.session.units["u-4"].x = 2
        self.session.units["u-4"].y = 4
        self.session.units["u-1"].x = 4
        self.session.units["u-1"].y = 6
        self.session.units["u-5"].x = 10
        self.session.units["u-5"].y = 4

        result = self.session.apply_action(
            ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="fire", unit_id="u-4", target_x=10, target_y=4)
        )
        self.assertTrue(result.accepted)
        self.assertIn("u-5", result.reason)

    def test_aoe_damage_applies_splash(self) -> None:
        self.session.units["u-1"].unit_type = "land_artillery"
        self.session.units["u-1"].x = 4
        self.session.units["u-1"].y = 4
        self.session.units["u-4"].x = 6
        self.session.units["u-4"].y = 4
        self.session.units["u-5"].x = 6
        self.session.units["u-5"].y = 5

        result = self.session.apply_action(
            ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="fire", unit_id="u-1", target_x=7, target_y=4)
        )
        self.assertTrue(result.accepted)
        self.assertTrue("u-4" not in self.session.units or self.session.units["u-4"].hp < 70)
        self.assertTrue("u-5" not in self.session.units or self.session.units["u-5"].hp < 55)

    def test_land_infantry_cannot_attack_air(self) -> None:
        self.session.units["u-2"].domain = "air"
        self.session.units["u-2"].x = 5
        self.session.units["u-2"].y = 4

        result = self.session.apply_action(
            ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="fire", unit_id="u-1", target_x=5, target_y=4)
        )
        self.assertTrue(result.accepted)
        self.assertIn("miss", result.reason)
        self.assertEqual(180, self.session.units["u-2"].hp)

    def test_air_fighter_cannot_attack_land(self) -> None:
        self.session.units["u-1"].unit_type = "air_fighter"
        self.session.units["u-1"].domain = "air"
        self.session.units["u-1"].x = 4
        self.session.units["u-1"].y = 4
        self.session.units["u-4"].x = 6
        self.session.units["u-4"].y = 4

        result = self.session.apply_action(
            ActionRequest(session_id="demo", player_id="p-1", tick=1, action_type="fire", unit_id="u-1", target_x=6, target_y=4)
        )
        self.assertTrue(result.accepted)
        self.assertIn("miss", result.reason)
        self.assertEqual(70, self.session.units["u-4"].hp)


if __name__ == "__main__":
    unittest.main()
