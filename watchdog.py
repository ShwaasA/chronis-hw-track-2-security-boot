"""
Watchdog Daemon — Track HW-2, Day 3
Monitors daemon liveness. Encryption daemon failure mid-operation -> full
system HALT (not a reboot). Any other daemon failure -> normal restart of
just that daemon.
"""


class SystemHaltException(Exception):
    """Raised when a CRITICAL daemon fails — the whole system must stop."""
    pass


class DaemonRestartSignal(Exception):
    """Raised when a non-critical daemon fails — only that daemon restarts."""
    def __init__(self, daemon_name):
        self.daemon_name = daemon_name
        super().__init__(f"Restarting {daemon_name}")


class Watchdog:
    # Only the encryption daemon's failure is catastrophic — Rule 1 depends
    # on it being alive for the entire system to function safely.
    CRITICAL_DAEMONS = {"encryption_daemon"}

    def __init__(self):
        self.daemon_status = {}

    def report_failure(self, daemon_name: str):
        self.daemon_status[daemon_name] = "failed"
        if daemon_name in self.CRITICAL_DAEMONS:
            raise SystemHaltException(
                f"{daemon_name} failed mid-operation — full system HALT required."
            )
        raise DaemonRestartSignal(daemon_name)
