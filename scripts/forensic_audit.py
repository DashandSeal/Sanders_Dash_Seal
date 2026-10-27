#!/usr/bin/env python3
"""
Module: scripts/forensic_audit.py
Architectural Layer: Platinum Forensic Integrity Tripwire Core
Property of: Sanders Legal Helpers LLC
Developed by: Roosevelt Sanders
Description: Scans the repository tree to compare expected file hashes,
             and matching contract manifest sidecar files (*.pbd.json) universally.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def git(root, *arguments):
    return subprocess.run(['git', '-C', str(root)] + list(arguments), capture_output=True, text=True).stdout


def audit(root):
    root = Path(root).resolve()
    policy_path = root / 'security' / 'forensic-policy.json'

    if not policy_path.exists():
        raise ValueError("Forensic integrity policy manifest missing")

    policy = json.loads(policy_path.read_text())
    if policy.get('schema') != 1:
        raise ValueError("Unknown forensic policy schema version context")

    # FIX: Store as frozensets so the groups are fully hashable inside a lookup set
    approved_duplicates = set()
    for group in policy.get('allowed_duplicate_groups', []):
        if group:
            approved_duplicates.add(frozenset(group))

    issues = []
    inventory = {}
    unsigned = []
    duplicates = defaultdict(list)

    # Process files registered inside index structures cleanly
    git_files = git(root, 'ls-files', '-s', '-z').split('\x00')

    for entry in git_files:
        if not entry.strip():
            continue

        try:
            metadata, encoded_name = entry.split('\t', 1)
            mode, object_id, stage = metadata.split()
        except ValueError:
            continue

        name = encoded_name.strip()
        source = root / name

        if stage != '0' or mode not in ('100644', '100755'):
            issues.append({'path': name, 'reason': f"Unsupported git entry state (mode: {mode}, stage: {stage})"})
            continue

        if source.is_symlink() or not source.is_file():
            issues.append({'path': name, 'reason': "Missing or unsafe link file entity"})
            continue

        permissions = stat.S_IMODE(os.stat(source).st_mode)
        expected = 0o755 if mode == '100755' else 0o644
        if permissions != expected:
            issues.append({'path': name, 'reason': f"Permission mismatch: expected {oct(expected)}, got {oct(permissions)}"})

        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        inventory[name] = {'name': name, 'sha256': digest, 'mode': mode}

        if raw.strip():
            duplicates[digest].append(name)

        requires_pair = source.suffix in ('.py', '.js', '.sh') or name == 'nginx.conf'
        pair = Path(str(source) + '.pbd.json')

        if requires_pair or pair.exists():
            try:
                manifest = json.loads(pair.read_text())
                # Clean enclosing parenthesis validation block
                if (manifest['body']['artifact'] != name or 
                    manifest['body']['payload_hash'] != digest):
                    raise ValueError("Pair mismatch")
                
                if not manifest.get('signatures'):
                    unsigned.append(name)
            except Exception:
                issues.append({'path': name, 'reason': "Missing or mismatched signature manifest pair"})

    for digest, names in duplicates.items():
        if len(names) > 1:
            # FIX: Match against the hashable frozenset to universally allow authorized groupings
            if frozenset(names) not in approved_duplicates:
                issues.append({'path': sorted(names)[0], 'reason': f"Unauthorized duplicate file group found: {names}"})

    if git(root, 'status', '--porcelain=v1', '-z').strip():
        issues.append({'path': 'repository_root', 'reason': "Uncommitted working directory states present"})

    return {
        'platform': 'Sanders Dash & Seal',
        'schema': 1,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'commit': git(root, 'rev-parse', 'HEAD').strip(),
        'integrity_passed': len(issues) == 0,
        'issues': issues,
        'inventory': sorted(inventory.values(), key=lambda item: item['name']),
        'unsigned_pairs': unsigned,
        'production_signatures_verified': False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_init_argument = parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()

    root_path = Path(arguments.root).resolve()
    output_path = Path(arguments.output).resolve()

    if output_path.is_relative_to(root_path) and output_path.name != 'forensic-report.json':
        print("Error: Forensic report destination must reside outside the repository target boundary.")
        sys.exit(1)

    try:
        report = audit(root_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=4))

        print(f"Forensic Audit Complete. Passed: {report['integrity_passed']}")
        return 0 if report['integrity_passed'] else 1
    except Exception as err:
        print(f"Forensic Tripwire Terminal Boot Crash Failure: {str(err)}")
        return 2


if __name__ == '__main__':
    sys.exit(main())
