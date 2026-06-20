from __future__ import unicode_literals

import json
import re

import requests
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth1Session
try:
    from urllib.parse import parse_qs, urlsplit
except ImportError:
    from urlparse import parse_qs, urlsplit

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


MAX_REQUEST_BYTES = 4 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
MAX_TARGETING_VALUE_BYTES = 1024
_IDENTIFIER = re.compile(r"^[A-Za-z0-9]{1,64}$")
_TARGETING_TYPE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


class AdsProtocolError(Exception):
    def __init__(self, message, outcome_unknown=False):
        super(AdsProtocolError, self).__init__(message)
        self.outcome_unknown = outcome_unknown


def _validate_identifier(name, value):
    if not isinstance(value, string_types) or not _IDENTIFIER.match(value):
        raise AdsProtocolError("%s is invalid" % name)
    return value


def _validate_targeting_type(value):
    if not isinstance(value, string_types) or not _TARGETING_TYPE.match(value):
        raise AdsProtocolError("targeting_type is invalid")
    return value


def _validate_targeting_value(value):
    if not isinstance(value, string_types) or not value or "\x00" in value:
        raise AdsProtocolError("targeting_value is invalid")
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_TARGETING_VALUE_BYTES:
        raise AdsProtocolError("targeting_value is too large")
    return value


def _validated_base_url(base_url, allow_loopback_http):
    if not isinstance(base_url, string_types):
        raise AdsProtocolError("Ads API base URL is invalid")
    parsed = urlsplit(base_url.rstrip("/"))
    loopback = parsed.hostname in ("127.0.0.1", "::1", "localhost")
    if parsed.scheme != "https" and not (allow_loopback_http and parsed.scheme == "http" and loopback):
        raise AdsProtocolError("Ads API base URL must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AdsProtocolError("Ads API base URL is invalid")
    return base_url.rstrip("/")


class TwitterAdsTargetingClient(object):
    def __init__(self, consumer_key, consumer_secret, access_token,
                 access_token_secret, base_url,
                 connect_timeout=3.05, read_timeout=10.0,
                 allow_loopback_http=False):
        credentials = (consumer_key, consumer_secret, access_token, access_token_secret)
        if not all(isinstance(value, string_types) and value for value in credentials):
            raise AdsProtocolError("Twitter Ads credentials are incomplete")
        if connect_timeout <= 0 or read_timeout <= 0:
            raise AdsProtocolError("Twitter Ads timeouts must be positive")

        self._base_url = _validated_base_url(base_url, allow_loopback_http)
        self._timeout = (connect_timeout, read_timeout)
        self._session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        self._session.mount("http://", HTTPAdapter(max_retries=0))
        self._session.mount("https://", HTTPAdapter(max_retries=0))

    def create_targeting_criterion(self, account_id, line_item_id,
                                   targeting_type, targeting_value):
        account_id = _validate_identifier("account_id", account_id)
        form = {
            "line_item_id": _validate_identifier("line_item_id", line_item_id),
            "targeting_type": _validate_targeting_type(targeting_type),
            "targeting_value": _validate_targeting_value(targeting_value),
        }
        url = "%s/accounts/%s/targeting_criteria" % (self._base_url, account_id)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "data-ads-demo-targeting/1",
        }

        try:
            response = self._session.post(
                url,
                data=form,
                headers=headers,
                allow_redirects=False,
                timeout=self._timeout,
                stream=True,
            )
        except requests.Timeout:
            raise AdsProtocolError(
                "Twitter Ads request timed out; outcome is unknown",
                outcome_unknown=True,
            )
        except requests.RequestException:
            raise AdsProtocolError(
                "Twitter Ads request failed; outcome is unknown",
                outcome_unknown=True,
            )

        try:
            if 300 <= response.status_code < 400:
                raise AdsProtocolError("Twitter Ads redirect was rejected")

            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                raise AdsProtocolError("Twitter Ads response was not JSON")
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > MAX_RESPONSE_BYTES:
                        raise AdsProtocolError("Twitter Ads response is too large")
                except ValueError:
                    raise AdsProtocolError("Twitter Ads response length is invalid")

            body = bytearray()
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise AdsProtocolError("Twitter Ads response is too large")
            except requests.RequestException:
                raise AdsProtocolError("Twitter Ads response was incomplete")

            try:
                payload = json.loads(bytes(body).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                raise AdsProtocolError("Twitter Ads response contained invalid JSON")

            if not isinstance(payload, dict):
                raise AdsProtocolError("Twitter Ads response schema is invalid")
            if response.status_code < 200 or response.status_code >= 300:
                raise AdsProtocolError(_safe_provider_error(payload))
            data = payload.get("data")
            if not isinstance(data, dict):
                raise AdsProtocolError("Twitter Ads response schema is invalid")
            return data
        finally:
            response.close()


def _safe_provider_error(payload):
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return "Twitter Ads rejected the request"
    first = errors[0]
    if not isinstance(first, dict):
        return "Twitter Ads rejected the request"
    message = first.get("message")
    if not isinstance(message, string_types):
        return "Twitter Ads rejected the request"
    message = "".join(character for character in message if character >= " " and character != "\x7f")
    message = message[:256].strip()
    return message or "Twitter Ads rejected the request"


def parse_targeting_form(method, content_type, body):
    if method != "POST":
        raise AdsProtocolError("targeting creation requires POST")
    if not isinstance(content_type, string_types):
        raise AdsProtocolError("targeting request content type is invalid")
    media_type, separator, parameters = content_type.partition(";")
    if media_type.strip().lower() != "application/x-www-form-urlencoded":
        raise AdsProtocolError("targeting request must be form encoded")
    if separator:
        parameter = parameters.strip().lower().replace(" ", "")
        if parameter != "charset=utf-8":
            raise AdsProtocolError("targeting request charset must be UTF-8")
    if not isinstance(body, bytes) or not body or len(body) > MAX_REQUEST_BYTES:
        raise AdsProtocolError("targeting request body is invalid")
    if re.search(br"%(?![0-9A-Fa-f]{2})", body):
        raise AdsProtocolError("targeting request encoding is invalid")
    try:
        decoded = body.decode("ascii")
        parsed = parse_qs(
            decoded,
            keep_blank_values=True,
            strict_parsing=True,
            encoding="utf-8",
            errors="strict",
        )
    except (UnicodeDecodeError, ValueError, TypeError):
        raise AdsProtocolError("targeting request encoding is invalid")

    expected = set(("account_id", "line_item_id", "targeting_type", "targeting_value"))
    if set(parsed) != expected or any(len(values) != 1 for values in parsed.values()):
        raise AdsProtocolError("targeting request schema is invalid")
    result = dict((name, values[0]) for name, values in parsed.items())
    _validate_identifier("account_id", result["account_id"])
    _validate_identifier("line_item_id", result["line_item_id"])
    _validate_targeting_type(result["targeting_type"])
    _validate_targeting_value(result["targeting_value"])
    return result


def process_targeting_request(method, content_type, body, client_factory):
    try:
        values = parse_targeting_form(method, content_type, body)
    except AdsProtocolError:
        return 400, {"valid": False, "error": "invalid_request"}

    try:
        data = client_factory().create_targeting_criterion(**values)
    except AdsProtocolError as error:
        if error.outcome_unknown:
            return 504, {"valid": False, "error": "provider_outcome_unknown"}
        return 502, {"valid": False, "error": "provider_request_failed"}

    identifier = data.get("id") if isinstance(data, dict) else None
    if not isinstance(identifier, string_types) or not _IDENTIFIER.match(identifier):
        return 502, {"valid": False, "error": "provider_response_invalid"}
    return 201, {"valid": True, "id": identifier}
