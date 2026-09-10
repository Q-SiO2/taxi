"""Pytest plugin that denies DNS and outbound sockets in the T2 unit harness."""

from __future__ import annotations

import socket
import ipaddress
from typing import Any


_ORIGINALS: dict[str, Any] = {}


def _deny(*_args: Any, **_kwargs: Any) -> Any:
    raise OSError("T2 simulated-persona execution forbids network access")


def _literal_loopback(host: Any) -> bool:
    if host is None:
        return True
    try:
        return ipaddress.ip_address(str(host)).is_loopback
    except ValueError:
        return False


def _guarded_connect(sock: socket.socket, address: Any) -> Any:
    if getattr(socket, "AF_UNIX", None) is not None and sock.family == socket.AF_UNIX:
        return _ORIGINALS["socket.connect"](sock, address)
    if isinstance(address, tuple) and address and _literal_loopback(address[0]):
        return _ORIGINALS["socket.connect"](sock, address)
    return _deny()


def _guarded_connect_ex(sock: socket.socket, address: Any) -> Any:
    if getattr(socket, "AF_UNIX", None) is not None and sock.family == socket.AF_UNIX:
        return _ORIGINALS["socket.connect_ex"](sock, address)
    if isinstance(address, tuple) and address and _literal_loopback(address[0]):
        return _ORIGINALS["socket.connect_ex"](sock, address)
    return _deny()


def _guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
    if isinstance(address, tuple) and address and _literal_loopback(address[0]):
        return _ORIGINALS["socket.create_connection"](address, *args, **kwargs)
    return _deny()


def _guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
    if _literal_loopback(host):
        return _ORIGINALS["socket.getaddrinfo"](host, *args, **kwargs)
    return _deny()


def pytest_sessionstart(session: Any) -> None:
    del session
    if _ORIGINALS:
        raise RuntimeError("T2 network guard was installed more than once")
    _ORIGINALS.update(
        {
            "socket.connect": socket.socket.connect,
            "socket.connect_ex": socket.socket.connect_ex,
            "socket.create_connection": socket.create_connection,
            "socket.getaddrinfo": socket.getaddrinfo,
        }
    )
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.create_connection = _guarded_create_connection
    socket.getaddrinfo = _guarded_getaddrinfo


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    del session, exitstatus
    if not _ORIGINALS:
        return
    socket.socket.connect = _ORIGINALS.pop("socket.connect")
    socket.socket.connect_ex = _ORIGINALS.pop("socket.connect_ex")
    socket.create_connection = _ORIGINALS.pop("socket.create_connection")
    socket.getaddrinfo = _ORIGINALS.pop("socket.getaddrinfo")
