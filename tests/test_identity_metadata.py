"""Fixed IMDSv2 endpoints and fail-closed local identity observation."""
import io
import json
import unittest

from scripts.scan_identity_metadata import BASE, FIELDS, NoRedirect, observe_identity


class Response(io.BytesIO):
    status = 200
    def __init__(self, raw, url):
        super().__init__(raw)
        self.url = url
    def geturl(self):
        return self.url


class Opener:
    def __init__(self, changes=None):
        self.values = {'id': 'ocid1.instance.oc1.phx.' + 'a' * 50,
                       'hostname': 'sanders-dash-seal', 'canonicalRegionName': 'us-phoenix-1', 'state': 'Running'}
        self.values.update(changes or {})
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        value = self.values[request.full_url.rsplit('/', 1)[1]]
        if isinstance(value, Exception):
            raise value
        return Response(value.encode(), request.full_url)


class IdentityMetadataTests(unittest.TestCase):
    def test_uses_documented_v2_keys_header_and_canonical_region(self):
        opener = Opener()
        result = observe_identity(opener=opener)
        self.assertEqual(result['state'], 'RUNNING')
        self.assertFalse(result['cryptographic_attestation'])
        self.assertFalse(result['production_ready'])
        self.assertEqual([request.full_url for request, _ in opener.calls], [BASE + field for field in FIELDS])
        for request, timeout in opener.calls:
            self.assertEqual(request.get_header('Authorization'), 'Bearer Oracle')
            self.assertEqual(timeout, 5)

    def test_timeout_has_no_success_looking_fallback(self):
        with self.assertRaises(TimeoutError):
            observe_identity(opener=Opener({'id': TimeoutError()}))

    def test_missing_region_nonrunning_state_invalid_id_and_log_injection_rejected(self):
        for changes in ({'canonicalRegionName': ''}, {'state': 'Stopped'},
                        {'id': 'invalid'}, {'hostname': 'fake\nSUCCESS'}, {'state': 'x' * 4097}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                observe_identity(opener=Opener(changes))

    def test_explicit_identity_mismatch_is_denied(self):
        with self.assertRaises(ValueError):
            observe_identity(opener=Opener(), expected_instance_id='other')

    def test_redirect_is_rejected_before_any_followup_request(self):
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://external.invalid')

    def test_quoted_metadata_is_parsed_without_exposing_other_fields(self):
        opener = Opener({'hostname': json.dumps('sanders-dash-seal')})
        self.assertEqual(observe_identity(opener=opener)['hostname'], 'sanders-dash-seal')


if __name__ == '__main__':
    unittest.main()
