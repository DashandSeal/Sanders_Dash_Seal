"""Upload a complete release and deploy the stack's actual Oracle host profile."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from deploy.activate_on_oracle import cli, deploy


class OCICommandFailure(RuntimeError):
    pass


def diagnostic_cli(args, *, raw=False):
    operation = ' '.join(args[:3])
    try:
        return cli(args, raw=raw)
    except subprocess.CalledProcessError as error:
        # OCI may reject the CLI invocation or respond with private identifiers.
        # Classify known failures; never disclose unfiltered stderr.
        stderr = error.stderr or ''
        status = re.search(r"""['"]?status['"]?\s*[:=]\s*['"]?(\d{3})""", stderr, re.I)
        code = re.search(r"""['"]?code['"]?\s*[:=]\s*['"]?([A-Za-z][A-Za-z0-9_]{0,79})""", stderr, re.I)
        low = stderr.lower()
        if any(s in low for s in ('request entity too large', 'payload too large',
                                  'zip file too large', 'maximum size', 'exceeds maximum')):
            category = 'upload_size_limit'
        elif any(s in low for s in ('no such option', 'unrecognized arguments',
                                    'invalid value for', 'missing option')):
            category = 'invalid_cli_argument'
        elif 'permission denied' in low or 'notauthorizedornotfound' in low:
            category = 'authorization_or_visibility'
        elif any(s in low for s in ('timed out', 'timeout', 'connection error',
                                    'connection refused', 'name resolution')):
            category = 'network_or_timeout'
        elif 'invalid' in low and ('key' in low or 'signature' in low):
            category = 'signing_key_rejected'
        elif 'serviceerror' in low or 'service error' in low:
            category = 'oci_service_rejected'
        elif error.returncode == 2:
            category = 'cli_argument_or_usage'
        else:
            category = 'cli_failure_unclassified'
        suffix = ' exit_code=' + str(error.returncode) + ' category=' + category
        if status:
            suffix += ' status=' + status.group(1)
        if code:
            suffix += ' service_code=' + code.group(1)
        raise OCICommandFailure('OCI command failed at ' + operation + suffix) from None

from deploy.publish_provider_secrets import environment_values, publish


@contextlib.contextmanager
def credentials(environment=None):
    env = os.environ if environment is None else environment
    names = ('OCI_TENANCY_OCID', 'OCI_USER_OCID', 'OCI_FINGERPRINT', 'OCI_PRIVATE_KEY')
    missing = [name for name in names if not env.get(name, '').strip()]
    if missing:
        raise ValueError('Missing GitHub Actions secrets: ' + ', '.join(missing))
    for name, kind in [('OCI_TENANCY_OCID', 'tenancy'), ('OCI_USER_OCID', 'user')]:
        if not re.fullmatch(r'ocid1\.' + kind + r'\.[A-Za-z0-9.]+', env[name]):
            raise ValueError('Actual OCI identity identifiers are required')
    if not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}', env['OCI_FINGERPRINT']):
        raise ValueError('Invalid OCI API signing-key fingerprint')
    if env.get('OCI_REGION', 'us-phoenix-1') != 'us-phoenix-1':
        raise ValueError('This deployment uses the owner home region us-phoenix-1')
    key = env['OCI_PRIVATE_KEY']
    if not key.startswith(('-----BEGIN PRIVATE KEY-----', '-----BEGIN RSA PRIVATE KEY-----')):
        raise ValueError('OCI_PRIVATE_KEY must contain the actual unencrypted PEM signing key')
    with tempfile.TemporaryDirectory(prefix='sds-oci-auth-') as folder:
        root = Path(folder)
        private = root / 'signing.pem'
        private.touch(mode=0o600)
        private.write_text(key)
        config = root / 'config'
        config.touch(mode=0o600)
        config.write_text('[DEFAULT]\nuser=' + env['OCI_USER_OCID'] + '\n'
            'tenancy=' + env['OCI_TENANCY_OCID'] + '\nfingerprint=' + env['OCI_FINGERPRINT'] + '\n'
            'key_file=' + str(private) + '\nregion=us-phoenix-1\n')
        values = {'OCI_CLI_CONFIG_FILE': str(config), 'OCI_CLI_AUTH': 'api_key'}
        previous = {name: os.environ.get(name) for name in values}
        os.environ.update(values)
        try:
            yield config
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


def release(zip_path, commit, stack_id, *, api=diagnostic_cli, activation=deploy, provider_environment=None):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Exact source commit required')
    if not re.fullmatch(r'ocid1\.ormstack\.[A-Za-z0-9.]+', stack_id):
        raise ValueError('OCI_STACK_OCID must identify the actual existing Resource Manager stack')
    release_size = Path(zip_path).stat().st_size
    print('OCI_RESOURCE_MANAGER_STACK_ZIP_BYTES=' + str(release_size), flush=True)
    if release_size > 11_000_000:
        raise ValueError('Release ZIP exceeds the Oracle Resource Manager 11 MB stack limit')
    with zipfile.ZipFile(zip_path) as archive:
        manifest = json.loads(archive.read('package_manifest.json'))
        if manifest.get('source_commit') != commit:
            raise ValueError('Release commit mismatch')
        for name, checksum in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != checksum:
                raise ValueError('Release archive checksum mismatch')
        defaults = archive.read('variables.tf').decode()
    current = api(['resource-manager', 'stack', 'get', '--stack-id', stack_id])['data']
    variables = dict(current.get('variables') or {})
    state = json.loads(api(['resource-manager', 'stack', 'get-stack-tf-state',
                           '--stack-id', stack_id, '--file', '-'], raw=True))
    managed_node = any(r.get('mode') == 'managed' and r.get('type') == 'oci_core_instance'
                       for r in state.get('resources', []))
    default_new = bool(re.search(r'variable "create_instance"\s*{\s*type\s*=\s*bool\s*default\s*=\s*true', defaults))
    new_node = managed_node or str(variables.get('create_instance', str(default_new))).lower() == 'true'
    variables.update(create_instance=str(new_node).lower(),
        deploy_existing_instance=str(not new_node).lower(), wait_for_application='false')
    # Resource Manager finishes provisioning first; the agent installs the exact
    # release below. This also updates an already-booted new-node stack, where
    # changing cloud-init metadata alone does not rerun application installation.
    api(['resource-manager', 'stack', 'update', '--stack-id', stack_id,
         '--config-source', str(Path(zip_path).resolve()),
         '--variables', json.dumps(variables), '--force'])
    supplied = environment_values(provider_environment or {})
    if supplied:
        result = activation(stack_id, api=api,
            before_install=lambda config, actual_api: publish(config['compartment_id'], supplied, actual_api))
    else:
        result = activation(stack_id, api=api)
    if result.get('commit') != commit:
        raise ValueError('Oracle installed a different source commit')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    with credentials():
        result = release(args.zip, args.commit, os.environ.get('OCI_STACK_OCID', ''), provider_environment=os.environ)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OCICommandFailure) as error:
        # Validation and sanitized command errors contain no secret values.
        raise SystemExit('OCI_GITOPS_NOT_COMPLETED: ' + str(error))
    except Exception:
        raise SystemExit('OCI_GITOPS_NOT_COMPLETED: unclassified Oracle deployment error; inspect OCI job logs')
