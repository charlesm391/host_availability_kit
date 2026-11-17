"""Host availability probing with short connect timeouts.

This module intentionally uses only the standard library so it can run in
network-isolated test containers.  The core trade-off is that we do not
attempt retries or exponential backoff: a single connect attempt per host-port
pair keeps the wall-clock cost predictable and makes the classification
(REACHABLE / UNREACHABLE / TIMEOUT) unambiguous.  Callers who want retries can
wrap ``probe_hosts`` in their own loop.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Sequence, Tuple


class ProbeResult(Enum):
    """Outcome of a single host-port probe."""

    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class HostProbe:
    """A host and port to probe.

    ``host`` may be a hostname or a literal IP address.  ``port`` must be a
    valid TCP port number.  We validate in ``__post_init__`` so that a bad
    probe is rejected before any network activity happens.
    """

    host: str
    port: int

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host:
            raise ValueError("host must be a non-empty string")
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise TypeError("port must be an int")
        if not (0 < self.port < 65536):
            raise ValueError("port must be between 1 and 65535")


def _classify_exception(exc: BaseException) -> ProbeResult:
    """Map a socket exception to a ProbeResult.

    ``socket.timeout`` is a subclass of ``OSError`` in Python 3.10+, so we
    check it first.  ``TimeoutError`` covers the built-in timeout raised by
    ``socket.create_connection`` on some platforms.  Everything else that is
    an ``OSError`` (connection refused, network unreachable, name resolution
    failure) is treated as UNREACHABLE.  We deliberately do not catch
    ``BaseException`` subclasses like ``KeyboardInterrupt``.
    """
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return ProbeResult.TIMEOUT
    if isinstance(exc, OSError):
        return ProbeResult.UNREACHABLE
    raise exc


def probe_hosts(
    hosts: Iterable[HostProbe],
    timeout: float = 1.0,
) -> List[Tuple[HostProbe, ProbeResult]]:
    """Probe each host-port pair and return results in input order.

    ``timeout`` is the connect timeout in seconds.  A value of 0 or less is
    rejected because it would make every probe fail immediately in a way that
    is hard to distinguish from a real timeout.  The function returns a list
    of ``(HostProbe, ProbeResult)`` tuples so callers can correlate results
    with inputs even when the input iterable is a generator.
    """
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    results: List[Tuple[HostProbe, ProbeResult]] = []
    for probe in hosts:
        if not isinstance(probe, HostProbe):
            raise TypeError("hosts must contain HostProbe instances")
        try:
            with socket.create_connection((probe.host, probe.port), timeout=timeout):
                pass
        except BaseException as exc:  # noqa: BLE001 - classification is explicit
            result = _classify_exception(exc)
        else:
            result = ProbeResult.REACHABLE
        results.append((probe, result))
    return results
