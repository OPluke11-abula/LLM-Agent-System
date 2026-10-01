"""Unit tests for Quota-Aware Router and 429 Cooldown Pool (Phase 105 Task D).

Verifies QuotaAwareRouter, 429 exponential backoff, RPM/TPM tracking,
account rotation, and QuotaExhaustedError when all pools are depleted.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from agent_workspace.core.account_manager import (
    AccountManager,
    QuotaAwareRouter,
    QuotaExhaustedError,
)


class TestQuotaAwareRouter(unittest.TestCase):
    """Verifies QuotaAwareRouter and 429 cooling mechanisms."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_quota_")
        self.am = AccountManager(self.temp_dir)
        self.am.delete_account("default-account")
        
        # Configure multiple accounts
        self.am.add_account({
            "id": "acc-1",
            "provider": "google-genai",
            "model": "gemini-2.5-flash",
            "token_budget": 1000,
            "tokens_used": 0,
            "is_active": True,
        })
        self.am.add_account({
            "id": "acc-2",
            "provider": "google-genai",
            "model": "gemini-2.5-flash",
            "token_budget": 5000,
            "tokens_used": 0,
            "is_active": False,
        })
        self.am.add_account({
            "id": "acc-3",
            "provider": "openai",
            "model": "gpt-4o",
            "token_budget": 10000,
            "tokens_used": 0,
            "is_active": False,
        })

        self.router = QuotaAwareRouter(self.am)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rate_limited_exponential_backoff(self):
        """Each consecutive 429 doubles cooldown up to max limit."""
        cd1 = self.router.mark_rate_limited("acc-1")
        self.assertEqual(cd1, 5.0)
        self.assertTrue(self.router.is_account_cooling("acc-1"))

        cd2 = self.router.mark_rate_limited("acc-1")
        self.assertEqual(cd2, 10.0)

        cd3 = self.router.mark_rate_limited("acc-1")
        self.assertEqual(cd3, 20.0)

    def test_cooling_account_expiration(self):
        """Accounts auto-evict from cooldown pool once timer expires."""
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            self.router.mark_rate_limited("acc-1", retry_after=5.0)
            self.assertTrue(self.router.is_account_cooling("acc-1"))

            # Advance past cooldown
            mock_time.return_value = 1006.0
            self.assertFalse(self.router.is_account_cooling("acc-1"))

    def test_auto_rotate_to_healthy_account(self):
        """When active account is rate-limited, router automatically picks next available."""
        self.router.mark_rate_limited("acc-1")
        available = self.router.get_available_account()
        self.assertIsNotNone(available)
        self.assertIn(available["id"], ("acc-2", "acc-3"))

    def test_filter_by_preferred_provider(self):
        """Can request available account for specific provider."""
        self.router.mark_rate_limited("acc-1")
        available = self.router.get_available_account(preferred_provider="google-genai")
        self.assertEqual(available["id"], "acc-2")

    def test_rpm_and_tpm_sliding_window(self):
        """Tracks request and token rates within 60 second sliding window."""
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            self.router.record_request_telemetry("acc-1", tokens=150)
            self.router.record_request_telemetry("acc-1", tokens=250)

            rpm, tpm = self.router.get_rate_metrics("acc-1")
            self.assertEqual(rpm, 2)
            self.assertEqual(tpm, 400)

            # Advance past 60s
            mock_time.return_value = 1065.0
            rpm2, tpm2 = self.router.get_rate_metrics("acc-1")
            self.assertEqual(rpm2, 0)
            self.assertEqual(tpm2, 0)

    def test_quota_exhausted_error_when_all_cooling_or_over_budget(self):
        """Raises QuotaExhaustedError when all available accounts cannot serve requests."""
        self.router.mark_rate_limited("acc-1")
        self.router.mark_rate_limited("acc-2")
        self.router.mark_rate_limited("acc-3")

        with self.assertRaises(QuotaExhaustedError):
            self.router.get_available_account()


if __name__ == "__main__":
    unittest.main()
