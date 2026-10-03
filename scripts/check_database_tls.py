"""Validate the database TLS chain before migrations, without sending credentials."""
import os
import socket
import ssl
from datetime import datetime, timezone

host = os.environ["POSTGRES_HOST"]
port = int(os.environ["POSTGRES_PORT"])
context = ssl.create_default_context(cafile=os.environ["POSTGRES_SSLROOTCERT"])
try:
    with socket.create_connection((host, port), timeout=10) as connection:
        connection.sendall(bytes.fromhex("0000000804d2162f"))
        if connection.recv(1) != b"S":
            raise RuntimeError("O banco não aceitou TLS.")
        with context.wrap_socket(connection, server_hostname=host) as secured:
            print("Database TLS verified:", secured.version(), flush=True)
except ssl.SSLCertVerificationError as error:
    print("Database certificate validation failed:", error.verify_code,
          error.verify_message, "UTC:", datetime.now(timezone.utc).isoformat(), flush=True)
    raise SystemExit(1) from None
