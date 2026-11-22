"""Scan tracked files and print locations only, never matching secret values."""
import re
import subprocess
from pathlib import Path


PATTERNS = {
    "openai_key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "telegram_token": re.compile(rb"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b"),
    "github_token": re.compile(rb"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def main() -> int:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], check=True, stdout=subprocess.PIPE
    ).stdout.split(b"\0")
    findings: list[tuple[str, str]] = []
    for raw_path in tracked:
        if not raw_path:
            continue
        path = Path(raw_path.decode("utf-8"))
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for kind, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((kind, str(path)))
    if findings:
        for kind, path in findings:
            print(f"SECRET_CANDIDATE type={kind} file={path}")
        return 1
    print("secret_scan=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
