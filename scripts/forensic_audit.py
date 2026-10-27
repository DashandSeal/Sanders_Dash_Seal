"""
Module: scripts/forensic_audit
Architectural Layer: Platinum Forensic Integrity Tripwire Core
Property of: Sanders Legal Helpers LLC
Developed by: Roosevelt Sanders
Description: Scans the repository tree to compare expected file hashes, file permissions,
             and matching contract manifest sidecar files (*.pbd.json) natively.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
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
        raise ValueError('Forensic integrity policy manifest missing')
        
    policy = json.loads(policy_path.read_text())
    if policy.get('schema') != 1:
        raise ValueError('Unknown forensic policy schema version context')
        
    # FIX: Cast to a list comprehension containing sets to avoid unhashable set-in-set errors
    approved_duplicates = [set(group) for group in policy.get('allowed_duplicates', [])]
    
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
            issues.append({'path': name, 'reason': 'Unsupported git entry mode configuration'})
            continue
            
        if source.is_symlink() or not source.is_file():
            issues.append({'path': name, 'reason': 'Missing or unsafe link file format'})
            continue
            
        permissions = stat.S_IMODE(source.stat().st_mode)
        expected = 0o755 if mode == '100755' else 0o644
        if permissions != expected:
            issues.append({'path': name, 'reason': f'Permission mismatch: expected {oct(expected)}, got {oct(permissions)}'})
            
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        inventory[name] = {'name': name, 'sha256': digest, 'mode': mode}
        
        if raw.strip():
            duplicates[digest].append(name)
            
        requires_pair = source.suffix in ('.py', '.js', '.sh') or name in ('compose.yaml', 'docker-compose.yml')
        pair = Path(str(source) + '.pbd.json')
        
        if requires_pair or pair.exists():
            try:
                manifest = json.loads(pair.read_text())
                
                # FIX: Clean, enclosed parentheses logic execution block to clear SyntaxErrors
                if (manifest['body']['artifact'] != name or 
                    manifest['body']['payload_hash'] != digest):
                    raise ValueError('Pair mismatch')
                    
                if not manifest.get('signatures'):
                    unsigned.append(name)
            except Exception:
                issues.append({'path': name, 'reason': 'Missing or mismatched sidecar metadata signature contract'})

    for digest, names in duplicates.items():
        if len(names) > 1 and set(names) not in approved_duplicates:
            issues.append({'path': sorted(names)[0], 'reason': f'Unapproved duplicate code content matching files: {sorted(names)}'})
            
    if git(root, 'status', '--porcelain=v1', '-z').strip():
        issues.append({'path': 'repository_root', 'reason': 'Uncommitted changes or un-tracked directory drift discovered'})
        
    return {
        'platform': 'Sanders Dash & Seal',
        'schema': 1,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'commit': git(root, 'rev-parse', 'HEAD').strip(),
        'integrity_passed': len(issues) == 0,
        'issues': issues,
        'inventory': sorted(inventory.values(), key=lambda item: item['path'] if 'path' in item else item['name']),
        'unsigned_pairs': unsigned,
        'production_signatures_verified': False
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    
    root_path = Path(arguments.root).resolve()
    output_path = Path(arguments.output).resolve()
    
    if output_path.is_relative_to(root_path) and output_path.name != 'forensic-report.json':
        print("Error: Forensic report destination must reside outside the validation stream box checkout", file=sys.stderr)
        sys.exit(1)
        
    try:
        report = audit(root_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=4))
        
        print(f"🟢 Forensic Audit Complete. Passed: {report['integrity_passed']}. Open issues detected: {len(report['issues'])}")
        return 0 if report['integrity_passed'] else 1
    except Exception as err:
        print(f"🛑 Forensic Tripwire Terminal Boot Crash Failure: {str(err)}", file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
