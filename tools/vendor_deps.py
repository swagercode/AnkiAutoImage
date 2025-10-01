from __future__ import annotations

"""
Populate the add-on's local vendor directory with required third-party packages.

Why: Some Anki users cannot install pip deps in the bundled Python. Vendoring
packages into the add-on ensures it works out-of-the-box.

Usage (from repo root):
  python -m pip install --upgrade pip
  python tools/vendor_deps.py

This reads vendor_requirements.txt and installs packages (with their
dependencies) into the add-on's vendor/ directory. Commit the vendor/ folder
after running this so users don't need pip.
"""

import os
import subprocess
import sys


def main() -> None:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    vendor_dir = os.path.join(base_dir, "vendor")
    req_file = os.path.join(base_dir, "vendor_requirements.txt")

    os.makedirs(vendor_dir, exist_ok=True)
    if not os.path.exists(req_file):
        print(f"Missing requirements file: {req_file}")
        sys.exit(1)

    # Install to vendor using pip's --target
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "-r",
        req_file,
        "--target",
        vendor_dir,
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)
    print("Vendored deps installed into:", vendor_dir)


if __name__ == "__main__":
    main()


