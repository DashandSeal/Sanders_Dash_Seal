"""Host bootstrap regressions with fake host tools; never mutates the machine."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from deploy.host_integrity import inventory, check


ROOT = Path(__file__).resolve().parents[1]


class HostBootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)

    def shell(self, commands, *, tools=None):
        env = os.environ.copy()
        if tools:
            directory = self.temp / 'bin'
            directory.mkdir(exist_ok=True)
            for name, content in tools.items():
                path = directory / name
                path.write_text('#!/bin/bash\n' + content)
                path.chmod(0o755)
            env['PATH'] = str(directory) + os.pathsep + env['PATH']
        return subprocess.run(['bash', '-c', 'source "$1"; ' + commands,
            'fixture', str(ROOT / 'deploy.sh')], env=env, capture_output=True, text=True)

    def test_firewall_uses_actual_interface_zone_without_reload(self):
        log = self.temp / 'firewall.log'
        tools = {
            'ip': "printf 'default via 10.0.0.1 dev ens3 proto dhcp\\n'\n",
            'firewall-cmd': f'''printf '%s\\n' "$*" >> '{log}'
case "$1" in
  --get-zone-of-interface=ens3) echo external ;;
  --get-zones) echo 'public external' ;;
esac
'''}
        result = self.shell('configure_firewall', tools=tools)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = log.read_text()
        self.assertIn('--zone=external --add-service=https', commands)
        self.assertIn('--permanent --zone=external --add-service=http', commands)
        self.assertNotIn('--reload', commands)
        self.assertNotIn('--remove', commands)

    def test_unresolved_interface_zone_fails_before_rule_changes(self):
        log = self.temp / 'firewall.log'
        result = self.shell('configure_firewall', tools={
            'ip': "echo 'default via 10.0.0.1 dev ens3'\n",
            'firewall-cmd': f"echo \"$*\" >> '{log}'\necho 'no zone'\n"})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('--add-service', log.read_text())

    def test_missing_independent_authorizer_is_not_approval(self):
        result = self.shell(f"SDS_RELEASE_AUTHORIZER='{self.temp}/missing'; authorize_release /unused")
        self.assertNotEqual(result.returncode, 0)

    def test_production_os_rejection_does_not_install_or_restart(self):
        metadata = self.temp / 'os-release'
        metadata.write_text('ID=other\nVERSION_ID=9\n')
        result = self.shell(f"SDS_OS_RELEASE_FILE='{metadata}'; check_host")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Oracle Linux required', result.stderr)

    def test_host_monitor_detects_changed_missing_extra_and_permission_changes(self):
        source = self.temp / 'source'
        source.mkdir()
        (source / 'original.txt').write_text('approved')
        baseline = self.temp / 'integrity.json'
        baseline.write_text(json.dumps({'schema': 1, 'files': inventory(source)}))
        self.assertTrue(check(source, baseline)['passed'])
        (source / 'original.txt').chmod(0o600)
        self.assertIn('original.txt', check(source, baseline)['changed'])
        (source / 'original.txt').unlink()
        (source / 'extra.txt').write_text('unexpected')
        result = check(source, baseline)
        self.assertIn('original.txt', result['missing'])
        self.assertIn('extra.txt', result['unexpected'])

    def test_host_monitor_rejects_symlinks(self):
        source = self.temp / 'source'
        source.mkdir()
        (source / 'link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            inventory(source)

    def renewal(self, mode):
        log, count = self.temp / 'renew.log', self.temp / 'count'
        commands = f'''
compose() {{
    printf '%s\\n' "$*" >> '{log}'
    if [[ "$*" == *sha256sum* ]]; then
        n=$(cat '{count}' 2>/dev/null || echo 0)
        echo $((n+1)) > '{count}'
        if [[ '{mode}' == changed && "$n" != 0 ]]; then echo new; else echo old; fi
    elif [[ "$*" == *'certbot renew'* && '{mode}' == failed ]]; then
        return 1
    fi
}}
renew_certificates
'''
        return self.shell(commands), log

    def test_certificate_change_tests_config_then_reloads(self):
        result, log = self.renewal('changed')
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = log.read_text()
        self.assertLess(commands.index('nginx -t'), commands.index('nginx -s reload'))

    def test_unchanged_certificate_does_not_reload(self):
        result, log = self.renewal('unchanged')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('nginx -s reload', log.read_text())

    def test_failed_renewal_does_not_reload(self):
        result, log = self.renewal('failed')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('nginx -s reload', log.read_text())
