from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IntegrationContractTests(unittest.TestCase):
    def test_django_endpoint_uses_bounded_protocol_handler(self):
        source = (ROOT / "home" / "lineitems.py").read_text(encoding="utf-8")
        required = [
            "process_targeting_request(",
            "request.method",
            "request.META.get(\"CONTENT_TYPE\", \"\")",
            "request.META.get(\"CONTENT_LENGTH\", \"\")",
            "MAX_REQUEST_BYTES",
            "request.body",
            "TwitterAdsTargetingClient(",
            "status=status",
        ]
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)
        self.assertNotIn("TargetingCriteria(account)", source)
        self.assertNotIn("e.response.body", source)

    def test_browser_uses_csrf_protected_form_posts_with_correct_schema(self):
        source = (ROOT / "static" / "js" / "ads.js").read_text(encoding="utf-8")
        required = [
            'type: "POST"',
            '"X-CSRFToken": getCookie("csrftoken")',
            'targeting_type: "CUSTOM_AUDIENCE"',
            'targeting_type: "PHRASE_KEYWORD"',
            "line_item_id: line_item_id",
            "targetingWriteInFlight || payloads.length === 0",
        ]
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)
        self.assertNotIn("$.getJSON(\"../../ads/api/targeting/new?", source)
        self.assertNotIn("line_item_id: campaign_id", source)
        self.assertNotIn("console.log(json)", source)

    def test_current_ads_endpoint_and_transport_are_declared(self):
        protocol = (ROOT / "home" / "ads_protocol.py").read_text(encoding="utf-8")
        settings = (ROOT / "app" / "settings.py").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("HTTPAdapter(max_retries=0)", protocol)
        self.assertIn("allow_redirects=False", protocol)
        self.assertIn("timeout=self._timeout", protocol)
        self.assertIn("https://ads-api.x.com/12", settings)
        self.assertIn("requests-oauthlib", requirements)


if __name__ == "__main__":
    unittest.main()
