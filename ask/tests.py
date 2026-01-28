from django.test import SimpleTestCase
from rest_framework.test import APIClient

from .logic import route_question, search_geo, search_regulation


class RoutingTests(SimpleTestCase):
    def test_route_geo(self):
        source = route_question("What is the mobiscore per ha?")
        self.assertEqual(source, "geo")

    def test_route_regulation(self):
        source = route_question("What does Art. 0.4 say about trees?")
        self.assertEqual(source, "regulation")

    def test_route_unknown(self):
        source = route_question("What is the capital of France?")
        self.assertEqual(source, "unknown")


class SearchTests(SimpleTestCase):
    def test_geo_search_finds_mobiscore(self):
        answer = search_geo("mobiscore per ha").answer
        self.assertIn("Mobiscore per ha", answer)

    def test_regulation_search_finds_bouwlaag(self):
        answer = search_regulation("What is a bouwlaag?").answer
        self.assertIn("Bouwlaag", answer)


class ApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_api_success_geo(self):
        response = self.client.post(
            "/api/ask/", {"question": "mobiscore per ha"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source"], "geo")
        self.assertIn("Mobiscore per ha", response.data["answer"])
        self.assertIn("meta", response.data)

    def test_api_missing_question(self):
        response = self.client.post("/api/ask/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["source"], "unknown")

    def test_api_root_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")

    def test_api_answer_result_shape(self):
        response = self.client.post(
            "/api/ask/", {"question": "What is a bouwlaag?"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.data)
        self.assertIn("source", response.data)
        self.assertIn("meta", response.data)
        self.assertIn("confidence", response.data["meta"])
        self.assertIn("route_scores", response.data["meta"])

    def test_api_top_k_respected(self):
        response = self.client.post(
            "/api/ask/", {"question": "mobiscore per ha", "top_k": 1}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["meta"]["top_matches"]), 1)
