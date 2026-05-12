"""Smoke tests for the safe_get() SSRF wrapper in _common.py.

Mocks socket.getaddrinfo so the tests are network-free and deterministic.
Covers each private/internal IP family that safe_get must refuse plus
the happy-path case where a public IP is allowed through.
"""
from __future__ import annotations

import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _common import SSRFRefused, safe_get  # noqa: E402


def _fake_getaddrinfo(ip: str):
    """Build a socket.getaddrinfo return value pinning to a specific IP."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]


class SSRFGuardTest(unittest.TestCase):
    def _assert_refused(self, ip: str):
        """safe_get must raise SSRFRefused for the given IP."""
        with mock.patch("socket.getaddrinfo",
                        return_value=_fake_getaddrinfo(ip)):
            with self.assertRaises(SSRFRefused) as cm:
                safe_get(f"http://example.test/x")
        self.assertEqual(cm.exception.ip, ip)
        self.assertEqual(cm.exception.host, "example.test")

    def test_refuses_loopback(self):
        self._assert_refused("127.0.0.1")

    def test_refuses_aws_metadata(self):
        # 169.254.169.254 is the canonical SSRF target on AWS/GCP/Azure.
        # link-local range (169.254.0.0/16).
        self._assert_refused("169.254.169.254")

    def test_refuses_rfc1918_10_net(self):
        self._assert_refused("10.0.0.1")

    def test_refuses_rfc1918_192_168(self):
        self._assert_refused("192.168.1.1")

    def test_refuses_rfc1918_172_16(self):
        self._assert_refused("172.16.0.1")

    def test_refuses_unspecified(self):
        self._assert_refused("0.0.0.0")

    def test_allows_public_ip_calls_httpx(self):
        """A non-private IP must reach httpx.get unchanged."""
        with mock.patch("socket.getaddrinfo",
                        return_value=_fake_getaddrinfo("8.8.8.8")), \
             mock.patch("httpx.get") as fake_get:
            fake_get.return_value = mock.Mock(status_code=200)
            safe_get("http://dns.example/q",
                     timeout=10.0, headers={"User-Agent": "test"})
        fake_get.assert_called_once()
        kwargs = fake_get.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 10.0)
        self.assertEqual(kwargs["headers"], {"User-Agent": "test"})

    def test_dns_failure_translates_to_httpx_connect_error(self):
        """gaierror must become httpx.ConnectError so existing
        `except httpx.HTTPError` clauses keep working — adding a separate
        socket-error branch in every caller would be regression-prone."""
        import httpx
        with mock.patch("socket.getaddrinfo",
                        side_effect=socket.gaierror("dns is broken")):
            with self.assertRaises(httpx.ConnectError) as cm:
                safe_get("http://no-such-host.test/x")
        self.assertIn("dns is broken", str(cm.exception))

    def test_ssrfrefused_carries_envelope_ready_attrs(self):
        """SSRFRefused must expose url/host/ip so the caller can pass
        them to err() context without parsing the exception message."""
        e = SSRFRefused("http://x.test/", "x.test", "10.0.0.1")
        self.assertEqual(e.url, "http://x.test/")
        self.assertEqual(e.host, "x.test")
        self.assertEqual(e.ip, "10.0.0.1")


if __name__ == "__main__":
    unittest.main()
