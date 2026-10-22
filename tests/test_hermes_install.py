"""Installer regressions: CDPATH, profile scope and deliberate checkout changes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


FAKE_HERMES = '''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
profile = pathlib.Path(os.environ['HERMES_HOME']) / 'profiles/clipper'
if args[:2] == ['profile', 'create']:
    profile.mkdir(parents=True)
    (profile / 'config.yaml').write_text('{}')
    (profile / '.env').write_text('HERMES_CUSTOM_NYOLAB_API_KEY=fixture-not-a-key\\n')
    sys.exit(0)
assert args[:3] == ['-p', 'clipper', 'config'], args
config = profile / 'config.yaml'
data = json.loads(config.read_text())
if args[3:] == ['get', 'terminal.cwd']:
    print(data['terminal']['cwd'])
elif args[3:5] == ['set', 'terminal.cwd']:
    assert len(args) == 6, args
    data.setdefault('terminal', {})['cwd'] = args[5]
    config.write_text(json.dumps(data))
else:
    raise AssertionError(args)
'''


@unittest.skipIf(os.name == 'nt' or not shutil.which('bash'), 'POSIX Hermes installer')
class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'checkout with spaces & symbols'
        self.script = self.repo / 'integrations/hermes/install.sh'
        self.script.parent.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1]
        shutil.copy2(source / 'integrations/hermes/install.sh', self.script)
        (self.repo / '.agents/skills/clipping').mkdir(parents=True)
        (self.script.parent / 'SOUL.md').write_text('fixture identity')
        self.template = {'model': {'default': 'fixture-model'},
                         'terminal': {'cwd': 'REPO_PATH', 'timeout': 900},
                         'providers': {'fixture': {'base_url': 'https://example.invalid'}}}
        (self.script.parent / 'config.yaml.example').write_text(json.dumps(self.template))
        self.home = self.root / 'hermes home'
        self.profile = self.home / 'profiles/clipper'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        command = self.bin / 'hermes'
        command.write_text(FAKE_HERMES)
        command.chmod(0o755)
        self.env = dict(os.environ, HERMES_HOME=str(self.home), CDPATH='.',
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def existing(self, cwd=None):
        self.profile.mkdir(parents=True)
        data = dict(self.template, terminal={'cwd': str(cwd or self.repo), 'timeout': 900})
        (self.profile / 'config.yaml').write_text(json.dumps(data))
        (self.profile / '.env').write_text('HERMES_CUSTOM_NYOLAB_API_KEY=fixture-not-a-key\n')
        (self.profile / 'SOUL.md').write_text('prior identity')
        return data

    def run_install(self, *args):
        return subprocess.run(['bash', 'integrations/hermes/install.sh', *args],
                              cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_cdpath_does_not_duplicate_cwd(self):
        before = self.existing()
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads((self.profile / 'config.yaml').read_text())
        self.assertEqual(after, before)
        self.assertEqual((self.profile / 'SOUL.md').resolve(), self.script.parent / 'SOUL.md')

    def test_selected_profile_uses_root_without_nesting(self):
        self.existing()
        self.env['HERMES_HOME'] = str(self.profile) + '/'
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.profile / 'profiles').exists())
        self.assertTrue((self.profile / 'skills/media/clipping').is_symlink())

    def test_other_checkout_is_refused_without_changes(self):
        other = self.root / 'other checkout'
        other.mkdir()
        self.existing(other)
        before = (self.profile / 'config.yaml').read_bytes()
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--retarget', result.stderr)
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), before)
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'prior identity')
        self.assertFalse(list(self.profile.glob('*.bak-*')))

    def test_explicit_retarget_preserves_settings_and_backup(self):
        before = self.existing('/nonexistent/old-checkout')
        result = self.run_install('--retarget')
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads((self.profile / 'config.yaml').read_text())
        before['terminal']['cwd'] = str(self.repo)
        self.assertEqual(after, before)
        self.assertTrue(list(self.profile.glob('config.yaml.bak-*')))
        self.assertTrue(list(self.profile.glob('SOUL.md.bak-*')))

    def test_new_profile_handles_spaces_and_ampersands(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads((self.profile / 'config.yaml').read_text())
        self.assertEqual(after['terminal']['cwd'], str(self.repo))
        self.assertEqual(after['model'], self.template['model'])


if __name__ == '__main__':
    unittest.main()
