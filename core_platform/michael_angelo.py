"""MICHAEL ANGELO #49's distinct, evidence-bound RTSA observation conductor.

Preserves the recovered Conductor Principle. This coordination path is not the
full synthesis/inference engine and grants no IT Manager/MINOTAUR authority.
"""
from .rtsa_registry import RTSA_ROLES
from .operational_runtime import observation


def conductor_observation(snapshots):
    by_role={value['role']:value for value in snapshots if value['role'] in RTSA_ROLES}
    if len(by_role)!=len([v for v in snapshots if v['role'] in RTSA_ROLES]):
        raise ValueError('Distinct RTSA observations required')
    verified=[value for value in by_role.values()
        if value['record_status']=='VERIFIED_RECENT_OBSERVATION']
    faults=sum(value['state']=='FAULT' for value in verified)
    unknown=sum(value['state']=='UNKNOWN' for value in verified)
    complete=len(verified)==14
    return observation('FAULT' if faults else 'HEALTHY' if complete and not unknown else 'UNKNOWN',
        'RTSA_MATRIX_OBSERVED',expected_rtsas=14,verified_rtsas=len(verified),
        faulted_rtsas=faults,unknown_rtsas=unknown)
