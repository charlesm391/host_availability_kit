import unittest
from unittest import mock

from host_availability_kit import HostProbe, ProbeResult, probe_hosts


class HostProbeTests(unittest.TestCase):
    def test_valid_probe(self):
        p = HostProbe("localhost", 80)
        self.assertEqual(p.host, "localhost")
        self.assertEqual(p.port, 80)

    def test_empty_host_rejected(self):
        with self.assertRaises(ValueError):
            HostProbe("", 80)

    def test_non_string_host_rejected(self):
        with self.assertRaises(ValueError):
            HostProbe(None, 80)  # type: ignore[arg-type]

    def test_port_out_of_range(self):
        with self.assertRaises(ValueError):
            HostProbe("localhost", 0)
        with self.assertRaises(ValueError):
            HostProbe("localhost", 65536)

    def test_bool_port_rejected(self):
        with self.assertRaises(TypeError):
            HostProbe("localhost", True)  # type: ignore[arg-type]


class ProbeHostsTests(unittest.TestCase):
    def test_reachable(self):
        probes = [HostProbe("localhost", 80)]
        with mock.patch("socket.create_connection") as conn:
            conn.return_value.__enter__.return_value = None
            results = probe_hosts(probes, timeout=0.5)
        self.assertEqual(results, [(probes[0], ProbeResult.REACHABLE)])
        conn.assert_called_once_with(("localhost", 80), timeout=0.5)

    def test_unreachable_on_oserror(self):
        probes = [HostProbe("localhost", 80)]
        with mock.patch("socket.create_connection", side_effect=OSError("refused")):
            results = probe_hosts(probes, timeout=0.5)
        self.assertEqual(results, [(probes[0], ProbeResult.UNREACHABLE)])

    def test_timeout_on_socket_timeout(self):
        probes = [HostProbe("localhost", 80)]
        with mock.patch("socket.create_connection", side_effect=TimeoutError("timed out")):
            results = probe_hosts(probes, timeout=0.5)
        self.assertEqual(results, [(probes[0], ProbeResult.TIMEOUT)])

    def test_order_preserved(self):
        probes = [HostProbe("a", 1), HostProbe("b", 2), HostProbe("c", 3)]

        def fake_create_connection(address, timeout):
            host, _ = address
            if host == "a":
                return mock.MagicMock()
            if host == "b":
                raise OSError("no")
            raise TimeoutError("slow")

        with mock.patch("socket.create_connection", side_effect=fake_create_connection):
            results = probe_hosts(probes, timeout=0.5)
        self.assertEqual(
            results,
            [
                (probes[0], ProbeResult.REACHABLE),
                (probes[1], ProbeResult.UNREACHABLE),
                (probes[2], ProbeResult.TIMEOUT),
            ],
        )

    def test_zero_timeout_rejected(self):
        with self.assertRaises(ValueError):
            probe_hosts([HostProbe("localhost", 80)], timeout=0)

    def test_negative_timeout_rejected(self):
        with self.assertRaises(ValueError):
            probe_hosts([HostProbe("localhost", 80)], timeout=-1)

    def test_non_hostprobe_rejected(self):
        with self.assertRaises(TypeError):
            probe_hosts([("localhost", 80)])  # type: ignore[list-item]

    def test_empty_iterable(self):
        self.assertEqual(probe_hosts([], timeout=1.0), [])


if __name__ == "__main__":
    unittest.main()
