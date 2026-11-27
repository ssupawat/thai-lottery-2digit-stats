import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "update_draws.py"
plan = importlib.util.spec_from_file_location("update_draws", SCRIPT_PATH)
update_draws = importlib.util.module_from_spec(plan)
plan.loader.exec_module(update_draws)


class TestAnswer:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.content


def answer_content(value):
    return {
        "statusCode": 200,
        "status": True,
        "response": {
            "result": {
                "date": "2026-10-05",
                "data": {
                    "last2": {
                        "number": [{"round": 1, "value": value}],
                    },
                },
            },
        },
    }


class UpdateDrawsTest(unittest.TestCase):
    def test_main_adds_missing_draw(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draws.json"
            path.write_text(
                json.dumps({"draws": [["2026-10-04", "12"]]}),
                encoding="utf-8",
            )

            def send(_address, json, timeout):
                if json["date"] == "05" and json["month"] == "10":
                    return TestAnswer(answer_content("08"))
                return TestAnswer({"status": True, "response": None})

            test_time = datetime(2026, 10, 6, 18, tzinfo=timezone.utc)
            with (
                patch.object(update_draws, "PATH", str(path)),
                patch.object(update_draws, "bangkok_time", return_value=test_time),
                patch.object(update_draws.requests, "post", side_effect=send),
            ):
                update_draws.main()

            content = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(["2026-10-05", "08"], content["draws"])
            self.assertEqual(content["updatedDisplay"], "5 ตุลาคม 2569")

    def test_network_problem_stops_the_update(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draws.json"
            path.write_text(json.dumps({"draws": []}), encoding="utf-8")
            test_time = datetime(2026, 10, 6, 18, tzinfo=timezone.utc)

            with (
                patch.object(update_draws, "PATH", str(path)),
                patch.object(update_draws, "bangkok_time", return_value=test_time),
                patch.object(
                    update_draws.requests,
                    "post",
                    side_effect=update_draws.requests.RequestException("offline"),
                ),
            ):
                with self.assertRaises(SystemExit) as problem:
                    update_draws.main()

            self.assertEqual(problem.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
