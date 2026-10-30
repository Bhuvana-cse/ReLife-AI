import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db_file.close()
os.environ["RELIFE_DB_PATH"] = db_file.name
os.environ["RELIFE_SECRET_KEY"] = "test-secret-key-long-enough-for-hmac"

from app.main import app, evaluate_opening_hours


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        app.router.on_startup[0]()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        os.unlink(db_file.name)

    def setUp(self):
        response = self.client.post("/api/auth/register", json={
            "name": "Test Student", "email": f"test{os.urandom(3).hex()}@example.edu", "password": "SecurePass123"
        })
        self.assertEqual(response.status_code, 201)
        self.headers = {"Authorization": f"Bearer {response.json()['token']}"}

    def test_auth_protects_history_and_password_not_returned(self):
        self.assertEqual(self.client.get("/api/history").status_code, 401)
        profile = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(profile.status_code, 200)
        self.assertNotIn("password", profile.text.lower())
        registered = self.client.post("/api/auth/register", json={
            "name": "Student ID User", "email": f"studentid{os.urandom(3).hex()}@example.edu",
            "student_id": "stu-1042", "password": "SecurePass123"
        })
        self.assertEqual(registered.status_code, 201)
        student_login = self.client.post("/api/auth/login", json={
            "identifier": "STU-1042", "password": "SecurePass123"
        })
        self.assertEqual(student_login.status_code, 200)

    def test_analysis_generates_passport_and_is_user_scoped(self):
        response = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "electronics", "age_years": "2", "condition": "good",
            "visible_damage": "small crack", "repair_cost": "20", "resale_value": "80"
        })
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["inference_mode"], "rule-based demo")
        self.assertEqual(len(body["options"]), 6)
        self.assertIn("decision_calculation", body)
        for option in body["options"]:
            self.assertIn("estimated_cost", option)
            self.assertIn("estimated_proceeds", option)
            self.assertIn("eligible", option)
        self.assertEqual(self.client.get(f"/api/passports/{body['product_id']}", headers=self.headers).status_code, 200)
        other = self.client.post("/api/auth/register", json={
            "name": "Other Student", "email": f"other{os.urandom(3).hex()}@example.edu", "password": "SecurePass123"
        }).json()
        self.assertEqual(self.client.get(f"/api/passports/{body['product_id']}",
                                         headers={"Authorization": f"Bearer {other['token']}"}).status_code, 404)

    def test_simulation_and_plan_steps(self):
        analysis = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "furniture", "age_years": "5", "condition": "fair",
            "repair_cost": "15", "resale_value": "40"
        }).json()
        simulated = self.client.post("/api/simulations", headers=self.headers, json={
            "product_id": analysis["product_id"], "repair_cost": 15, "resale_value": 40,
            "useful_life_years": 2, "period_years": 3, "replacement_cost_per_year": 20
        })
        self.assertEqual(simulated.status_code, 200)
        self.assertIn("no precise carbon", simulated.json()["disclaimer"].lower())
        self.assertEqual(simulated.json()["results"][0]["estimated_total_cost"], 35)
        self.assertEqual(simulated.json()["results"][0]["cost_per_additional_year"], 17.5)
        saved = self.client.get(f"/api/simulations/{analysis['product_id']}", headers=self.headers)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["assumptions"]["repair_cost"], 15)
        changed = self.client.post("/api/simulations", headers=self.headers, json={
            "product_id": analysis["product_id"], "repair_cost": 90, "resale_value": 5,
            "useful_life_years": 0.5, "period_years": 3, "replacement_cost_per_year": 20,
        })
        self.assertNotEqual(changed.json()["results"][0]["estimated_total_cost"], 35)
        self.assertEqual(self.client.get(f"/api/simulations/{analysis['product_id']}", headers=self.headers)
                         .json()["assumptions"]["repair_cost"], 90)
        plan = self.client.post(f"/api/plans/{analysis['product_id']}", headers=self.headers).json()
        self.assertTrue(plan["steps"])
        step = plan["steps"][0]
        updated = self.client.patch(f"/api/plans/steps/{step['id']}", headers=self.headers, json={"status": "completed"})
        self.assertEqual(updated.json()["status"], "completed")

    def test_reanalysis_updates_same_product_and_passport_lookup_is_private(self):
        first = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "electronics", "product_name": "Laptop", "age_years": "3",
            "useful_life_years": "2", "condition": "fair", "repair_cost": "25", "resale_value": "100",
        }).json()
        second = self.client.post("/api/analyses", headers=self.headers, data={
            "product_id": str(first["product_id"]), "category": "electronics", "product_name": "Laptop",
            "age_years": "3", "useful_life_years": "4", "condition": "good",
            "repair_cost": "30", "resale_value": "120",
        })
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["product_id"], first["product_id"])
        self.assertEqual(second.json()["passport_id"], first["passport_id"])
        self.assertNotEqual(second.json()["recommendation"], first["recommendation"])
        passport = self.client.get(f"/api/passports/lookup/{first['passport_id']}", headers=self.headers)
        self.assertEqual(passport.status_code, 200)
        self.assertEqual(len(passport.json()["analysis_history"]), 2)
        self.assertEqual(passport.json()["product_name"], "Laptop")
        self.assertEqual(passport.json()["useful_life_years"], 4)
        self.assertIn(f"?passport={first['passport_id']}", passport.json()["qr_payload"])
        other = self.client.post("/api/auth/register", json={
            "name": "Private Record User", "email": f"private{os.urandom(3).hex()}@example.edu", "password": "SecurePass123"
        }).json()
        self.assertEqual(self.client.get(f"/api/passports/lookup/{first['passport_id']}",
                                         headers={"Authorization": f"Bearer {other['token']}"}).status_code, 404)

    def test_component_conditions_and_recovery_plan_alternative_persist(self):
        analysis = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "electronics", "product_name": "Laptop", "age_years": "4",
            "condition": "fair", "repair_cost": "25", "resale_value": "100",
        }).json()
        product_id = analysis["product_id"]
        saved = self.client.post(f"/api/salvage/{product_id}", headers=self.headers, json={
            "category": "laptop", "condition_states": {"RAM": "working", "SSD": "untested", "battery": "damaged"},
        })
        self.assertEqual(saved.status_code, 201)
        components = {component["name"]: component for component in saved.json()["components"]}
        self.assertEqual(components["RAM"]["condition_state"], "working")
        self.assertIsNotNone(components["RAM"]["estimated_value_range"])
        self.assertIsNone(components["SSD"]["estimated_value_range"])
        restored = self.client.get(f"/api/salvage/{product_id}", headers=self.headers)
        self.assertEqual(restored.json()["components"], saved.json()["components"])

        plan = self.client.post(f"/api/plans/{product_id}", headers=self.headers).json()
        repair_step = next(step for step in plan["steps"] if step["action"] == "repair")
        self.client.patch(f"/api/plans/steps/{repair_step['id']}", headers=self.headers, json={"status": "unavailable"})
        fallback = self.client.post(
            f"/api/plans/{product_id}/steps/{repair_step['id']}/alternative", headers=self.headers,
        )
        self.assertEqual(fallback.status_code, 200)
        self.assertEqual(fallback.json()["alternative"]["action"], "donation")
        persisted = self.client.get(f"/api/plans/{product_id}", headers=self.headers).json()
        self.assertEqual(persisted["steps"][0]["status"], "unavailable")
        passport = self.client.get(f"/api/passports/{product_id}", headers=self.headers).json()
        self.assertEqual(passport["components"], saved.json()["components"])
        self.assertEqual(passport["recovery_plan"][0]["status"], "unavailable")

        broken = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "electronics", "product_name": "Damaged laptop", "age_years": "6",
            "condition": "broken", "repair_cost": "200", "resale_value": "20",
        }).json()
        unsafe_plan = self.client.post(f"/api/plans/{broken['product_id']}", headers=self.headers).json()
        self.assertFalse({"repair", "resale", "donation", "reuse"} & {step["action"] for step in unsafe_plan["steps"]})

    def test_matching_salvage_centers_passport_updates_and_impact(self):
        analysis = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "electronics", "age_years": "3", "condition": "good",
            "location": "Campus", "repair_cost": "30", "resale_value": "60"
        }, files={"image": ("device.png", b"sample-image-bytes", "image/png")})
        self.assertEqual(analysis.status_code, 201)
        body = analysis.json()
        self.assertIn("Images are validated but not analyzed", body["image_note"])
        product_id = body["product_id"]
        self.assertEqual(body["location"], "Campus")

        invalid_image = self.client.post("/api/analyses", headers=self.headers, data={
            "category": "electronics", "age_years": "3", "condition": "good"
        }, files={"image": ("device.gif", b"gif-data", "image/gif")})
        self.assertEqual(invalid_image.status_code, 415)

        match_list = self.client.get(f"/api/matches/{product_id}", headers=self.headers)
        self.assertEqual(match_list.status_code, 200)
        self.assertTrue(match_list.json())
        campus_match = next(match for match in match_list.json() if "Campus" in match["location"])
        self.assertIn("Location matches", campus_match["reason"])
        self.assertEqual(campus_match["score"], 100)
        match = match_list.json()[0]
        changed = self.client.patch(
            f"/api/matches/{product_id}/{match['id']}", headers=self.headers, json={"status": "accepted"}
        )
        self.assertEqual(changed.json()["status"], "accepted")
        self.assertEqual(
            self.client.get(f"/api/matches/{product_id}", headers=self.headers).json()[0]["status"], "accepted"
        )

        salvage = self.client.post(
            f"/api/salvage/{product_id}", headers=self.headers,
            json={"category": "electronics", "confirmations": {"power cable": True}}
        )
        self.assertEqual(salvage.status_code, 201)
        self.assertIsNotNone(salvage.json()["estimated_salvage_value"])
        self.assertTrue(salvage.json()["components"][0]["user_confirmed_condition"])

        centers = self.client.get("/api/centers?category=electronics&kind=repair", headers=self.headers)
        self.assertEqual(centers.status_code, 200)
        self.assertTrue(all(center["demo"] == 1 for center in centers.json()))
        update = self.client.post(f"/api/passports/{product_id}/updates", headers=self.headers, json={
            "update_type": "repair", "detail": "Replaced a visible cable"
        })
        self.assertEqual(update.status_code, 201)
        report = self.client.get("/api/impact", headers=self.headers)
        self.assertEqual(report.status_code, 200)
        self.assertTrue(report.json()["weekly"])

    def test_live_center_search_returns_only_openstreetmap_contact_data(self):
        mapped = {
            "centers": [{
                "id": "osm-node-42",
                "name": "Mapped Repair Shop",
                "kind": "repair",
                "location": "Main Road, Vijayawada",
                "description": "OpenStreetMap provider listing.",
                "phone": "+91-0000000000",
                "email": None,
                "website": "https://example.invalid",
                "opening_hours": "Mo-Fr 09:00-17:00",
                "availability": "Published hours: Mo-Fr 09:00-17:00 (OpenStreetMap data; verify with provider).",
                "availability_status": "published_hours",
                "contact_note": "Only contact details present in OpenStreetMap are shown.",
                "categories": "",
                "map_url": "https://www.openstreetmap.org/node/42",
                "latitude": 16.5,
                "longitude": 80.6,
                "demo": False,
            }],
            "message": None,
        }
        with patch("app.main.query_openstreetmap", new=AsyncMock(return_value=mapped)):
            response = self.client.get(
                "/api/centers/live",
                headers=self.headers,
                params={"location": "Vijayawada", "kind": "repair"},
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "OpenStreetMap")
        self.assertEqual(body["centers"][0]["phone"], "+91-0000000000")
        self.assertEqual(body["centers"][0]["availability_status"], "published_hours")
        self.assertIn("does not provide appointment slots", body["availability_note"])

    def test_published_hours_are_evaluated_and_unlisted_hours_remain_unknown(self):
        state, summary = evaluate_opening_hours("24/7", 16.5, 80.6)
        self.assertEqual(state, "open")
        self.assertIn("according to listed hours", summary)
        state, summary = evaluate_opening_hours(None, 16.5, 80.6)
        self.assertEqual(state, "unknown")
        self.assertIn("not listed", summary)
        state, _summary = evaluate_opening_hours("not valid hours", 16.5, 80.6)
        self.assertEqual(state, "unknown")


if __name__ == "__main__":
    unittest.main()
