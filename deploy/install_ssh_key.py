"""One-time SSH key bootstrap: installs the local public key on a remote server
using password auth (via WONYO_SSH_PW env var), so all later deploys use
passwordless key auth. Generic and idempotent.

Usage:
  WONYO_SSH_PW=... uv run --with paramiko python deploy/install_ssh_key.py <host> <user>
"""

import os
import sys
from pathlib import Path

import paramiko


def main() -> None:
    host, user = sys.argv[1], sys.argv[2]
    password = os.environ.get("WONYO_SSH_PW")
    if not password:
        sys.exit("Set WONYO_SSH_PW env var")

    pub_path = Path.home() / ".ssh" / "id_ed25519.pub"
    pubkey = pub_path.read_text(encoding="utf-8").strip()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=10)

    cmd = (
        'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && '
        f'grep -qF "{pubkey}" ~/.ssh/authorized_keys || echo "{pubkey}" >> ~/.ssh/authorized_keys; '
        'chmod 600 ~/.ssh/authorized_keys; echo KEY_INSTALLED; uname -a; '
        'command -v python3 git uv; cat /etc/os-release | head -2'
    )
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out)
    if err.strip():
        print("STDERR:", err)
    client.close()


if __name__ == "__main__":
    main()
