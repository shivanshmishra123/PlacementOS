"""ClamAV malware scanner client and network-isolated scanning protocol."""

from __future__ import annotations

import logging
import socket
import struct
from typing import Protocol

from placementos.core.config import settings

logger = logging.getLogger(__name__)

EICAR_MARKER = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


class ScannerProtocol(Protocol):
    """Protocol for document malware scanners."""

    def scan_bytes(self, data: bytes) -> str:
        """Scan bytes and return status string or raise exception."""
        ...


class ClamAVScanner:
    """Production ClamAV daemon client implementing the standard clamd INSTREAM protocol."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.host = host or getattr(settings, "CLAMAV_HOST", "127.0.0.1")
        self.port = port or getattr(settings, "CLAMAV_PORT", 3310)
        self.timeout = timeout_seconds or getattr(settings, "CLAMAV_TIMEOUT_SECONDS", 10)

    def scan_bytes(self, data: bytes) -> str:
        """Stream bytes to clamd via INSTREAM protocol and evaluate result.

        ClamAV INSTREAM protocol format:
        1. Send command: b'zINSTREAM\x00' (or b'nINSTREAM\n')
        2. Stream chunks: 4-byte big-endian length prefix followed by chunk bytes.
        3. Terminate stream: 4-byte zero length prefix (b'\\x00\\x00\\x00\\x00').
        4. Read response: e.g. 'stream: OK\\n' or 'stream: <signature> FOUND\\n'.
        """
        from placementos.services.parsers import MalwareDetectedError, ParseError

        # Fast-fail on standard EICAR test string
        if EICAR_MARKER in data:
            logger.warning("EICAR test malware signature detected locally.")
            raise MalwareDetectedError("Malware signature detected: Eicar-Test-Signature")

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                # Send INSTREAM command
                sock.sendall(b"zINSTREAM\x00")

                # Chunk data in 32KB blocks
                chunk_size = 32768
                offset = 0
                total_len = len(data)

                while offset < total_len:
                    chunk = data[offset : offset + chunk_size]
                    length_header = struct.pack(">I", len(chunk))
                    sock.sendall(length_header + chunk)
                    offset += len(chunk)

                # Send 0-length termination chunk
                sock.sendall(struct.pack(">I", 0))

                # Read response
                response_bytes = b""
                while True:
                    packet = sock.recv(4096)
                    if not packet:
                        break
                    response_bytes += packet
                    if b"\n" in response_bytes or b"\x00" in response_bytes:
                        break

                response = response_bytes.decode("utf-8", errors="replace").strip()
                logger.info("ClamAV scan completed with response: %s", response)

                if "OK" in response:
                    return "clamav_clean"

                if "FOUND" in response:
                    parts = response.split("FOUND")[0].replace("stream:", "").strip()
                    signature = parts or "Unknown-Malware-Signature"
                    logger.warning("Malware signature detected by ClamAV: %s", signature)
                    raise MalwareDetectedError(f"Malware signature detected: {signature}")

                # If unexpected response from daemon
                raise ParseError("SCANNER_ERROR", f"Unexpected response from ClamAV daemon: {response}")

        except TimeoutError as exc:
            logger.error("ClamAV daemon scan timed out at %s:%s", self.host, self.port)
            raise ParseError("SCANNER_UNAVAILABLE", "Malware scanner service timed out") from exc
        except (ConnectionRefusedError, OSError) as exc:
            logger.error("ClamAV daemon connection failed at %s:%s: %s", self.host, self.port, exc)
            raise ParseError("SCANNER_UNAVAILABLE", "Configured malware scanner service is unavailable") from exc
