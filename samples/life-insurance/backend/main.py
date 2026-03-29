"""Start all A2A agent servers locally.

Usage:
    python main.py                          # Start all agents
    python main.py --agent product_catalog  # Start single agent
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

AGENTS = [
    "product_catalog", "underwriting_risk", "premium_calculator",
    "compliance_check", "explanation", "recommendation",
]

BACKEND_DIR = Path(__file__).parent


def start_all():
    procs = []
    for name in AGENTS:
        script = BACKEND_DIR / "agents" / f"{name}.py"
        print(f"Starting {name}...")
        procs.append(subprocess.Popen([sys.executable, str(script)], cwd=str(BACKEND_DIR)))
        time.sleep(1)  # stagger startup

    print("\nAll agents started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()


def start_one(name: str):
    script = BACKEND_DIR / "agents" / f"{name}.py"
    subprocess.run([sys.executable, str(script)], cwd=str(BACKEND_DIR))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insurance Demo Agent Launcher")
    parser.add_argument("--agent", choices=AGENTS, help="Start a single agent")
    args = parser.parse_args()

    if args.agent:
        start_one(args.agent)
    else:
        start_all()
