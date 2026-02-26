from __future__ import annotations

import base64
import json
from dataclasses import asdict
from typing import Dict

from server.domain import ActionRequest


class Repository:
    def persist_action(self, action: ActionRequest, accepted: bool, reason: str) -> None:
        raise NotImplementedError

    def analytics_snapshot(self, session_id: str) -> Dict[str, int]:
        raise NotImplementedError


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._records = []

    def persist_action(self, action: ActionRequest, accepted: bool, reason: str) -> None:
        payload = asdict(action)
        payload["accepted"] = accepted
        payload["reason"] = reason
        payload["network_bytes"] = len(json.dumps(asdict(action)))
        self._records.append(payload)

    def analytics_snapshot(self, session_id: str) -> Dict[str, int]:
        scoped = [record for record in self._records if record["session_id"] == session_id]
        accepted = len([record for record in scoped if record["accepted"]])
        total = len(scoped)
        network_bytes = sum(record["network_bytes"] for record in scoped)
        return {
            "session_id": session_id,
            "total_actions": total,
            "accepted_actions": accepted,
            "rejected_actions": total - accepted,
            "network_bytes": network_bytes,
        }


class AwanDbRepository(Repository):
    def __init__(self, endpoint: str, username: str, password: str) -> None:
        from adbc_driver_flightsql import dbapi

        self._dbapi = dbapi
        auth = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        self._conn = self._dbapi.connect(
            endpoint,
            db_kwargs={"adbc.flight.sql.rpc.call_header.Authorization": f"Basic {auth}"},
        )
        self._cursor = self._conn.cursor()
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_log (
                session_id STRING,
                player_id STRING,
                tick INT,
                action_type STRING,
                unit_id STRING,
                target_x INT,
                target_y INT,
                group_id STRING,
                unit_type STRING,
                resource_type STRING,
                accepted BOOLEAN,
                reason STRING,
                network_bytes INT
            )
            """
        )

    def persist_action(self, action: ActionRequest, accepted: bool, reason: str) -> None:
        self._cursor.execute(
            """
            INSERT INTO action_log
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action.session_id,
                action.player_id,
                action.tick,
                action.action_type,
                action.unit_id,
                action.target_x,
                action.target_y,
                action.group_id,
                action.unit_type,
                action.resource_type,
                accepted,
                reason,
                len(json.dumps(asdict(action))),
            ),
        )

    def analytics_snapshot(self, session_id: str) -> Dict[str, int]:
        self._cursor.execute(
            """
            SELECT
                COUNT(*) AS total_actions,
                SUM(CASE WHEN accepted THEN 1 ELSE 0 END) AS accepted_actions,
                SUM(network_bytes) AS network_bytes
            FROM action_log
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = self._cursor.fetchall()[0]
        total = int(row[0] or 0)
        accepted = int(row[1] or 0)
        network_bytes = int(row[2] or 0)
        return {
            "session_id": session_id,
            "total_actions": total,
            "accepted_actions": accepted,
            "rejected_actions": total - accepted,
            "network_bytes": network_bytes,
        }
