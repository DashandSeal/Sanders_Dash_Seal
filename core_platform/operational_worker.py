"""Run one actual operational observation cycle in the existing backend container."""
import argparse
import json
import os
from pathlib import Path
import sys

from .glass_box_audit import GlassBoxAudit
from .operational_probes import configured_probes
from .operational_runtime import OperationalRuntime
from .incident_diagnosis import diagnose_open_incidents
from .local_inference import configured_client


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path(os.environ.get('SQLITE_DB_PATH', '/app/data/sds_production.db')))
    args = parser.parse_args()
    if not args.database.is_file() or args.database.is_symlink():
        raise ValueError('Existing platform database required')
    audit_path = args.database.with_name('sds_audit.db')
    if not audit_path.is_file() or audit_path.is_symlink():
        raise ValueError('Existing separate audit database required')
    runtime = OperationalRuntime(args.database)
    audit = GlassBoxAudit(audit_path)
    result = runtime.cycle(configured_probes(args.database, audit))
    audit.preserve({'stage': 'OPERATIONAL_OBSERVATION_CYCLE', **result})
    try:model=configured_client()
    except (OSError,ValueError):
        model=None;result['diagnostic_model_configuration']='INVALID'
    else:result['diagnostic_model_configuration']='CONFIGURED' if model is not None else 'NOT_CONFIGURED'
    result['diagnostic_tasks']=diagnose_open_incidents(runtime,audit,model)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never echo exception messages from configuration or service responses.
        raise SystemExit('OPERATIONAL_OBSERVATION_NOT_COMPLETED')
