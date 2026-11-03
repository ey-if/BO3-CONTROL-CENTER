import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from BO3_Control_Center import (
    build_ping_command,
    clean_log_text,
    is_local_ipv4_target,
    is_valid_ipv4,
)


class IPv4ValidationTests(unittest.TestCase):
    def test_accepts_valid_ipv4(self):
        self.assertTrue(is_valid_ipv4("192.168.1.25"))
        self.assertTrue(is_valid_ipv4(" 10.0.0.1 "))

    def test_rejects_invalid_or_ipv6(self):
        self.assertFalse(is_valid_ipv4("999.1.1.1"))
        self.assertFalse(is_valid_ipv4("192.168.1"))
        self.assertFalse(is_valid_ipv4("::1"))
        self.assertFalse(is_valid_ipv4("example.com"))


class LocalPingTargetTests(unittest.TestCase):
    def test_accepts_private_link_local_and_loopback(self):
        for address in (
            "10.0.0.5",
            "172.16.0.1",
            "172.31.255.254",
            "192.168.1.25",
            "169.254.10.2",
            "127.0.0.1",
        ):
            with self.subTest(address=address):
                self.assertTrue(is_local_ipv4_target(address))

    def test_rejects_public_reserved_and_non_ipv4_targets(self):
        for address in (
            "8.8.8.8",
            "172.32.0.1",
            "192.0.2.1",
            "224.0.0.1",
            "255.255.255.255",
            "::1",
            "invalid",
        ):
            with self.subTest(address=address):
                self.assertFalse(is_local_ipv4_target(address))


class LogTextTests(unittest.TestCase):
    def test_collapses_whitespace_and_removes_control_characters(self):
        self.assertEqual(
            clean_log_text("  First\nSecond\t\x00 third  "),
            "First Second third"
        )

    def test_limits_length(self):
        self.assertEqual(clean_log_text("abcdefgh", 5), "abcde")


class PingCommandTests(unittest.TestCase):
    def test_windows_command_uses_argument_list(self):
        self.assertEqual(
            build_ping_command("192.168.1.25", "Windows"),
            ["ping", "-n", "2", "-w", "1200", "192.168.1.25"],
        )

    def test_unix_command_uses_argument_list(self):
        self.assertEqual(
            build_ping_command("192.168.1.25", "Linux"),
            ["ping", "-c", "2", "-W", "2", "192.168.1.25"],
        )


if __name__ == "__main__":
    unittest.main()
