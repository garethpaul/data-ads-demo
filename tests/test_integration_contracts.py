from pathlib import Path
import hashlib
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

    def test_gnip_client_has_no_caller_controlled_file_export(self):
        source = (ROOT / "gnip_search" / "gnip_search_api.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("output_file_path", source)
        self.assertNotIn("codecs.open(", source)

    def test_browser_uses_patched_bootstrap_and_current_jquery_assets(self):
        bootstrap = (ROOT / "static" / "js" / "bootstrap.min.js").read_text(
            encoding="utf-8"
        )
        jquery = (ROOT / "static" / "js" / "jquery-3.7.1.min.js").read_text(
            encoding="utf-8"
        )
        templates = "\n".join(
            (ROOT / "templates" / name).read_text(encoding="utf-8")
            for name in ("base.html", "login.html")
        )

        self.assertIn("Bootstrap v3.4.1", bootstrap)
        self.assertIn("jQuery v3.7.1", jquery)
        self.assertEqual(
            "9ee2fcff6709e4d0d24b09ca0fc56aade12b4961ed9c43fd13b03248bfb57afe",
            hashlib.sha256(bootstrap.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            "fc9a93dd241f6b045cbff0481cf4e1901becd0e12fb45166a8f17f95823f0b1a",
            hashlib.sha256(jquery.encode("utf-8")).hexdigest(),
        )
        self.assertFalse((ROOT / "static" / "js" / "bootstrap.js").exists())
        self.assertFalse((ROOT / "static" / "js" / "jquery-1.10.1.min.js").exists())
        self.assertFalse((ROOT / "static" / "js" / "jquery-1.10.1.min.map").exists())
        self.assertIn("js/bootstrap.min.js", templates)
        self.assertIn("js/jquery-3.7.1.min.js", templates)
        self.assertNotIn("js/bootstrap.js", templates)
        self.assertNotIn("js/jquery-1.10.1.min.js", templates)

    def test_repository_does_not_track_local_credentials(self):
        self.assertFalse((ROOT / "app" / "settings_my.py").exists())
        settings = (ROOT / "app" / "settings.py").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for variable in (
            "CONSUMER_KEY",
            "CONSUMER_SECRET",
            "ACCESS_TOKEN",
            "ACCESS_TOKEN_SECRET",
            "GNIP_USERNAME",
            "GNIP_PASSWORD",
            "GNIP_SEARCH_ENDPOINT",
        ):
            with self.subTest(variable=variable):
                self.assertIn("environ.get('%s')" % variable, settings)
                self.assertIn(variable, readme)

    def test_custom_browser_code_avoids_removed_jquery_apis(self):
        script = (ROOT / "static" / "js" / "script.js").read_text(
            encoding="utf-8"
        )
        datetimepicker = (
            ROOT / "static" / "js" / "bootstrap-datetimepicker.min.js"
        ).read_text(encoding="utf-8")
        self.assertNotIn("$(window).load(", script)
        self.assertIn('$(window).on("load",', script)
        self.assertNotIn('.find(".datepickerbutton").size()', datetimepicker)
        self.assertIn('.find(".datepickerbutton").length', datetimepicker)
        self.assertEqual(
            "cdc565042da17642325962724f83b9fc06fd66d030943e6bd02453531efe7fc4",
            hashlib.sha256(datetimepicker.encode("utf-8")).hexdigest(),
        )

    def test_browser_executes_only_same_origin_script_assets(self):
        template = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        nprogress_path = ROOT / "static" / "js" / "nprogress-0.2.0.min.js"
        self.assertTrue(nprogress_path.exists())
        nprogress = nprogress_path.read_text(encoding="utf-8")
        self.assertNotIn("<script src=\"http", template)
        self.assertNotIn("<script srcp=", template)
        self.assertIn("js/nprogress-0.2.0.min.js", template)
        self.assertEqual(
            "5d6cd2509f85210dfc76a0b4ebfe3cb0d470535421dff69f8e6274f344a7780f",
            hashlib.sha256(nprogress.encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
