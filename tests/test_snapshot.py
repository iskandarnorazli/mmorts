import json
import unittest
from pathlib import Path

from server.persistence import InMemoryRepository
from server.service import GameService


class SnapshotTests(unittest.TestCase):
    def test_create_snapshot_writes_file(self):
        service = GameService(repository=InMemoryRepository())
        out = Path('snapshots/test_snapshot.json')
        if out.exists():
            out.unlink()

        result = service.create_snapshot('demo', target_path=str(out))

        self.assertTrue(out.exists())
        body = json.loads(out.read_text())
        self.assertEqual('demo', body['state']['session_id'])
        self.assertEqual(str(out), result['snapshot_path'])


if __name__ == '__main__':
    unittest.main()
