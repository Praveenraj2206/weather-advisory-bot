import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Make the project root importable when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policies import evaluate_condition, evaluate_conditions, find_matching_sop
from fastapi.testclient import TestClient
from app import app


client = TestClient(app)


class TestPolicyMatching(unittest.TestCase):

    def test_picnic_conditions_match(self):
        weather = {
            "temperature": 24,
            "wind_speed": 10,
            "precipitation_probability": 5,
        }

        sop = find_matching_sop("picnic", weather)

        self.assertIsNotNone(sop)
        self.assertEqual(sop["id"], "SOP-05")

    def test_hiking_matches_windy_conditions(self):
        weather = {
            "wind_speed": 40,
            "precipitation_probability": 10,
        }

        sop = find_matching_sop("hiking", weather)

        self.assertIsNotNone(sop)
        self.assertEqual(sop["id"], "SOP-10")

    def test_no_skydiving_specific_rule(self):
        weather = {
            "temperature": 30,
            "wind_speed": 10,
            "precipitation_probability": 5,
        }

        sop = find_matching_sop("skydiving", weather)
        self.assertIsNone(sop)

    def test_any_condition_group(self):
        conditions = {
            "any": [
                {"field": "wind_speed", "operator": ">", "value": 35},
                {
                    "field": "precipitation_probability",
                    "operator": ">",
                    "value": 50,
                },
            ]
        }

        weather = {
            "wind_speed": 40,
            "precipitation_probability": 10,
        }

        self.assertTrue(evaluate_conditions(conditions, weather))

    def test_missing_weather_field_does_not_match(self):
        condition = {
            "field": "wind_speed",
            "operator": ">",
            "value": 35,
        }

        self.assertFalse(evaluate_condition(condition, {}))

    def test_boundary_is_not_greater_than(self):
        condition = {
            "field": "wind_speed",
            "operator": ">",
            "value": 40,
        }

        self.assertFalse(
            evaluate_condition(condition, {"wind_speed": 40})
        )


class TestAPI(unittest.TestCase):

    def test_health_endpoint(self):
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_advice_endpoint_returns_result(self):
        # Replace the workflow with a predictable result so this test
        # does not need a Groq API call or live weather service.
        fake_result = {
            "question": "Is a picnic suitable in Bengaluru?",
            "location": "Bengaluru, Karnataka, India",
            "activity": "picnic",
            "weather": {"temperature": 24},
            "sop": {
                "id": "SOP-05",
                "severity": "low",
                "advice": "Conditions look suitable for a picnic.",
            },
            "error": None,
            "response": "The weather looks suitable for a picnic.",
        }

        with patch("app.run_advisor", return_value=fake_result):
            response = client.post(
                "/advice",
                json={"question": "Is a picnic suitable in Bengaluru?"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sop"]["id"], "SOP-05")
        self.assertIn("picnic", response.json()["response"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)