"""Regression tests for Imperial Jade public page routing.

Preserve existing appointment, authentication and payment handlers.
"""
from core_platform.customer_app import ASSETS, create_customer_app


def _request(app, path, method="GET"):
    captured = {}
    def start(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)
    body = b"".join(app({"PATH_INFO": path, "REQUEST_METHOD": method}, start))
    return captured["status"], captured["headers"], body


def test_jade_static_routes_are_registered():
    assert ASSETS["/"][0] == "jade-landing.html"
    assert ASSETS["/landing"][0] == "jade-landing.html"
    assert ASSETS["/assets/jade-landing.css"][0] == "jade-landing.css"
    assert ASSETS["/assets/jade-landing.js"][0] == "jade-landing.js"
    assert ASSETS["/appointments"][0] == "index.html"
    assert ASSETS["/auth/login"][0] == "auth.html"


def test_jade_landing_served_without_appointment_authority():
    app = create_customer_app(None, lambda env: None, None,
                              lambda env, start: [b""],
                              "https://sandersdashandseal.com")
    for path, mime in (
        ("/", "text/html"),
        ("/landing", "text/html"),
        ("/assets/jade-landing.css", "text/css"),
        ("/assets/jade-landing.js", "application/javascript"),
    ):
        status, headers, body = _request(app, path)
        assert status == "200 OK"
        assert headers["Content-Type"].startswith(mime)
        assert body
        assert headers["X-Content-Type-Options"] == "nosniff"
    status, _, body = _request(app, "/api/appointments")
    assert status == "503 Service Unavailable"
    assert b"appointments_unavailable" in body


def test_jade_landing_keeps_existing_appointments():
    app = create_customer_app(None, lambda env: None, None,
                              lambda env, start: [b""],
                              "https://sandersdashandseal.com")
    status, _, body = _request(app, "/appointments")
    assert status == "200 OK"
    assert b'booking-form' in body


def test_jade_csp_allows_same_origin_images():
    app = create_customer_app(None, lambda env: None, None,
                              lambda env, start: [b""],
                              "https://sandersdashandseal.com")
    status, headers, _ = _request(app, "/")
    assert status == "200 OK"
    assert "img-src 'self'" in headers["Content-Security-Policy"]
