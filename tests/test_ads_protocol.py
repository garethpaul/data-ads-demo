import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from home.ads_protocol import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    AdsProtocolError,
    TwitterAdsTargetingClient,
    parse_targeting_form,
    process_targeting_request,
)


class FakeAdsHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    response_status = 201
    response_headers = {"Content-Type": "application/json; charset=utf-8"}
    response_body = json.dumps({"data": {"id": "criterion-1"}}).encode("utf-8")
    response_delay = 0
    omit_content_length = False
    requests = []

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        self.__class__.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
            }
        )
        if self.__class__.response_delay:
            time.sleep(self.__class__.response_delay)
        self.send_response(self.__class__.response_status)
        headers = dict(self.__class__.response_headers)
        if not self.__class__.omit_content_length:
            headers.setdefault("Content-Length", str(len(self.__class__.response_body)))
        headers.setdefault("Connection", "close")
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(self.__class__.response_body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        return


class FakeAdsServer:
    def __enter__(self):
        FakeAdsHandler.response_status = 201
        FakeAdsHandler.response_headers = {"Content-Type": "application/json; charset=utf-8"}
        FakeAdsHandler.response_body = json.dumps({"data": {"id": "criterion-1"}}).encode("utf-8")
        FakeAdsHandler.response_delay = 0
        FakeAdsHandler.omit_content_length = False
        FakeAdsHandler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAdsHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = "http://%s:%d/12" % (host, port)
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class TwitterAdsTargetingClientTests(unittest.TestCase):
    def make_client(self, base_url, **overrides):
        options = {
            "consumer_key": "consumer-key",
            "consumer_secret": "consumer-secret",
            "access_token": "access-token",
            "access_token_secret": "access-token-secret",
            "base_url": base_url,
            "connect_timeout": 0.25,
            "read_timeout": 0.25,
            "allow_loopback_http": True,
        }
        options.update(overrides)
        return TwitterAdsTargetingClient(**options)

    def test_posts_utf8_form_body_and_oauth_header_without_query_parameters(self):
        with FakeAdsServer() as server:
            response = self.make_client(server.base_url).create_targeting_criterion(
                account_id="18ce54d4x5t",
                line_item_id="8u94t",
                targeting_type="PHRASE_KEYWORD",
                targeting_value="grumpy cat ☕",
            )

        self.assertEqual({"id": "criterion-1"}, response)
        self.assertEqual(1, len(FakeAdsHandler.requests))
        request = FakeAdsHandler.requests[0]
        self.assertEqual(
            "/12/accounts/18ce54d4x5t/targeting_criteria",
            urlsplit(request["path"]).path,
        )
        self.assertEqual("", urlsplit(request["path"]).query)
        self.assertEqual(
            {
                "line_item_id": ["8u94t"],
                "targeting_type": ["PHRASE_KEYWORD"],
                "targeting_value": ["grumpy cat ☕"],
            },
            parse_qs(request["body"].decode("utf-8"), strict_parsing=True),
        )
        self.assertEqual("application/x-www-form-urlencoded", request["headers"]["Content-Type"])
        authorization = request["headers"].get("Authorization", "")
        self.assertTrue(authorization.startswith("OAuth "))
        self.assertIn('oauth_signature="', authorization)
        self.assertNotIn("consumer-secret", request["body"].decode("utf-8"))
        self.assertNotIn("access-token-secret", request["body"].decode("utf-8"))

    def test_oauth_signature_changes_when_only_signed_form_body_changes(self):
        with FakeAdsServer() as server:
            client = self.make_client(server.base_url)
            with patch("oauthlib.oauth1.rfc5849.generate_nonce", return_value="fixednonce"), patch(
                "oauthlib.oauth1.rfc5849.generate_timestamp", return_value="1700000000"
            ):
                client.create_targeting_criterion("account", "line", "LOCATION", "first")
                client.create_targeting_criterion("account", "line", "LOCATION", "second")

        first = FakeAdsHandler.requests[0]["headers"]["Authorization"]
        second = FakeAdsHandler.requests[1]["headers"]["Authorization"]
        self.assertNotEqual(first, second)
        self.assertIn('oauth_nonce="fixednonce"', first)
        self.assertIn('oauth_timestamp="1700000000"', first)

    def test_rejects_redirect_without_forwarding_credentials(self):
        with FakeAdsServer() as server:
            FakeAdsHandler.response_status = 307
            FakeAdsHandler.response_headers = {
                "Content-Type": "text/plain",
                "Location": "http://127.0.0.1:1/credential-sink",
            }
            FakeAdsHandler.response_body = b"redirect"
            with self.assertRaisesRegex(AdsProtocolError, "redirect"):
                self.make_client(server.base_url).create_targeting_criterion(
                    "18ce54d4x5t", "8u94t", "LOCATION", "123"
                )
        self.assertEqual(1, len(FakeAdsHandler.requests))

    def test_does_not_retry_ambiguous_server_failure(self):
        with FakeAdsServer() as server:
            FakeAdsHandler.response_status = 503
            FakeAdsHandler.response_body = json.dumps(
                {"errors": [{"message": "temporarily unavailable", "code": "UNAVAILABLE"}]}
            ).encode("utf-8")
            with self.assertRaisesRegex(AdsProtocolError, "temporarily unavailable"):
                self.make_client(server.base_url).create_targeting_criterion(
                    "18ce54d4x5t", "8u94t", "LOCATION", "123"
                )
        self.assertEqual(1, len(FakeAdsHandler.requests))

    def test_enforces_read_timeout(self):
        with FakeAdsServer() as server:
            FakeAdsHandler.response_delay = 0.2
            with self.assertRaisesRegex(AdsProtocolError, "timed out"):
                self.make_client(server.base_url, read_timeout=0.05).create_targeting_criterion(
                    "18ce54d4x5t", "8u94t", "LOCATION", "123"
                )
        self.assertEqual(1, len(FakeAdsHandler.requests))

    def test_rejects_oversized_response(self):
        with FakeAdsServer() as server:
            FakeAdsHandler.omit_content_length = True
            FakeAdsHandler.response_body = b"{" + (b"x" * MAX_RESPONSE_BYTES) + b"}"
            with self.assertRaisesRegex(AdsProtocolError, "response is too large"):
                self.make_client(server.base_url).create_targeting_criterion(
                    "18ce54d4x5t", "8u94t", "LOCATION", "123"
                )

    def test_rejects_declared_oversized_response_before_reading(self):
        with FakeAdsServer() as server:
            FakeAdsHandler.response_headers = {
                "Content-Type": "application/json",
                "Content-Length": str(MAX_RESPONSE_BYTES + 1),
            }
            FakeAdsHandler.response_body = b"{}"
            with self.assertRaisesRegex(AdsProtocolError, "response is too large"):
                self.make_client(server.base_url).create_targeting_criterion(
                    "18ce54d4x5t", "8u94t", "LOCATION", "123"
                )

    def test_rejects_non_json_response(self):
        with FakeAdsServer() as server:
            FakeAdsHandler.response_headers = {"Content-Type": "text/html"}
            FakeAdsHandler.response_body = b"<html>provider error</html>"
            with self.assertRaisesRegex(AdsProtocolError, "JSON"):
                self.make_client(server.base_url).create_targeting_criterion(
                    "18ce54d4x5t", "8u94t", "LOCATION", "123"
                )

    def test_rejects_invalid_schema_before_network(self):
        with FakeAdsServer() as server:
            client = self.make_client(server.base_url)
            invalid_cases = [
                ("../account", "8u94t", "LOCATION", "123"),
                ("account", "", "LOCATION", "123"),
                ("account", "line", "location", "123"),
                ("account", "line", "LOCATION", ""),
                ("account", "line", "LOCATION", "x" * 1025),
                ("account", "line", "LOCATION", "value\x00suffix"),
            ]
            for values in invalid_cases:
                with self.subTest(values=values):
                    with self.assertRaises(AdsProtocolError):
                        client.create_targeting_criterion(*values)
        self.assertEqual([], FakeAdsHandler.requests)

    def test_rejects_non_https_non_loopback_endpoint(self):
        with self.assertRaisesRegex(AdsProtocolError, "HTTPS"):
            TwitterAdsTargetingClient(
                consumer_key="key",
                consumer_secret="secret",
                access_token="token",
                access_token_secret="token-secret",
                base_url="http://example.com/12",
            )


class TargetingFormTests(unittest.TestCase):
    def test_accepts_exact_utf8_form_schema(self):
        body = (
            b"account_id=18ce54d4x5t&line_item_id=8u94t&"
            b"targeting_type=PHRASE_KEYWORD&targeting_value=grumpy+cat+%E2%98%95"
        )
        self.assertEqual(
            {
                "account_id": "18ce54d4x5t",
                "line_item_id": "8u94t",
                "targeting_type": "PHRASE_KEYWORD",
                "targeting_value": "grumpy cat ☕",
            },
            parse_targeting_form(
                "POST",
                "application/x-www-form-urlencoded; charset=UTF-8",
                body,
            ),
        )

    def test_rejects_wrong_method_content_type_size_and_schema(self):
        valid = (
            b"account_id=account&line_item_id=line&targeting_type=LOCATION&"
            b"targeting_value=value"
        )
        cases = [
            ("GET", "application/x-www-form-urlencoded", valid),
            ("POST", "application/json", valid),
            ("POST", "application/x-www-form-urlencoded; charset=latin-1", valid),
            ("POST", "application/x-www-form-urlencoded", b""),
            ("POST", "application/x-www-form-urlencoded", valid + b"&extra=value"),
            ("POST", "application/x-www-form-urlencoded", valid + b"&account_id=other"),
            ("POST", "application/x-www-form-urlencoded", valid.replace(b"LOCATION", b"location")),
            ("POST", "application/x-www-form-urlencoded", b"x" * (MAX_REQUEST_BYTES + 1)),
            ("POST", "application/x-www-form-urlencoded", valid + b"%ZZ"),
        ]
        for method, content_type, body in cases:
            with self.subTest(method=method, content_type=content_type, body=body[:80]):
                with self.assertRaises(AdsProtocolError):
                    parse_targeting_form(method, content_type, body)


class TargetingRequestHandlerTests(unittest.TestCase):
    class RecordingClient:
        def __init__(self, error=None):
            self.error = error
            self.calls = []

        def create_targeting_criterion(self, **values):
            self.calls.append(values)
            if self.error:
                raise self.error
            return {"id": "criterion1", "ignored": "provider data"}

    def setUp(self):
        self.body = (
            b"account_id=account&line_item_id=line&targeting_type=LOCATION&"
            b"targeting_value=value"
        )

    def test_valid_request_calls_provider_once_and_returns_bounded_schema(self):
        client = self.RecordingClient()
        status, payload = process_targeting_request(
            "POST", "application/x-www-form-urlencoded", self.body, lambda: client
        )
        self.assertEqual(201, status)
        self.assertEqual({"valid": True, "id": "criterion1"}, payload)
        self.assertEqual(
            [{
                "account_id": "account",
                "line_item_id": "line",
                "targeting_type": "LOCATION",
                "targeting_value": "value",
            }],
            client.calls,
        )

    def test_invalid_request_never_constructs_client(self):
        constructed = []
        status, payload = process_targeting_request(
            "GET",
            "application/x-www-form-urlencoded",
            self.body,
            lambda: constructed.append(True),
        )
        self.assertEqual(400, status)
        self.assertEqual({"valid": False, "error": "invalid_request"}, payload)
        self.assertEqual([], constructed)

    def test_provider_error_does_not_expose_raw_details(self):
        client = self.RecordingClient(
            AdsProtocolError("provider body contained account names and internal details")
        )
        status, payload = process_targeting_request(
            "POST", "application/x-www-form-urlencoded", self.body, lambda: client
        )
        self.assertEqual(502, status)
        self.assertEqual({"valid": False, "error": "provider_request_failed"}, payload)

    def test_timeout_reports_unknown_outcome_without_retrying(self):
        client = self.RecordingClient(
            AdsProtocolError("Twitter Ads request timed out; outcome is unknown", outcome_unknown=True)
        )
        status, payload = process_targeting_request(
            "POST", "application/x-www-form-urlencoded", self.body, lambda: client
        )
        self.assertEqual(504, status)
        self.assertEqual({"valid": False, "error": "provider_outcome_unknown"}, payload)
        self.assertEqual(1, len(client.calls))


if __name__ == "__main__":
    unittest.main()
