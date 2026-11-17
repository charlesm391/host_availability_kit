# host_availability_kit

Probe a list of host-port pairs with short connect timeouts and classify each as reachable, unreachable, or timeout.

## Usage

```python
from host_availability_kit import HostProbe, ProbeResult, probe_hosts

probes = [
    HostProbe("localhost", 80),
    HostProbe("192.0.2.1", 443),
]
for probe, result in probe_hosts(probes, timeout=0.5):
    if result is ProbeResult.REACHABLE:
        print(f"{probe.host}:{probe.port} is up")
    elif result is ProbeResult.TIMEOUT:
        print(f"{probe.host}:{probe.port} timed out")
    else:
        print(f"{probe.host}:{probe.port} is unreachable")
```

## Why this exists

Scripts that check whether a service is listening often reach for a full
HTTP client or a port scanner, which drags in dependencies and makes the
result ambiguous.  This library does one thing: a single TCP connect attempt
per host-port pair with a caller-supplied timeout.  The trade-off is that it
performs no retries and no backoff.  That keeps the classification crisp
(reachable means the connect succeeded; timeout means the connect did not
finish in time; unreachable means the OS rejected the connect) and keeps the
runtime predictable.  If you need retries, wrap ``probe_hosts`` in your own
loop.

## Edge case

``socket.create_connection`` may raise ``TimeoutError`` rather than
``socket.timeout`` on some platforms, and ``socket.timeout`` is a subclass of
``OSError`` on recent Pythons.  The classifier checks the timeout forms first
so a slow host is reported as ``TIMEOUT`` and not ``UNREACHABLE``.
