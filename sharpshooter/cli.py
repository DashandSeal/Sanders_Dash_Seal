"""CLI: python -m sharpshooter.cli diagnose example.org"""
import argparse
import json
from .core import diagnose, new_incident, evidence

def main():
    p = argparse.ArgumentParser(description="SharpShooter RTSA")
    p.add_argument("command", choices=["diagnose"])
    p.add_argument("hostname")
    args = p.parse_args()
    print(evidence(new_incident(args.hostname, diagnose(args.hostname))))

if __name__ == "__main__":
    main()
