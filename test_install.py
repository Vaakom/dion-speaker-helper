import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import install
from verify import check_installed_identity


class InstallTests(unittest.TestCase):
    def test_verify_rejects_matching_test_origin_instead_of_actual_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder)
            origin = 'chrome-extension://' + 'a' * 32 + '/'
            (runtime/'host-config.json').write_text(json.dumps({'origin': origin}), 'utf-8')
            (runtime/'native-host.json').write_text(json.dumps({'allowed_origins': [origin]}), 'utf-8')
            with self.assertRaises(ValueError):
                check_installed_identity(runtime, 'onaebjhhdohmgklfbdgdbekecdbnndpp')
            self.assertEqual(check_installed_identity(runtime, 'a' * 32), origin)

    def args(self, runtime, *extra):
        return install.make_parser({}).parse_args([
            '--extension-id', 'a' * 32, '--runtime', str(runtime), '--python', sys.executable, *extra])

    def test_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder).resolve() / 'runtime'
            with patch.object(install, 'register_host') as register:
                result = install.install(self.args(runtime, '--dry-run'))
            self.assertEqual(result['state'], 'dry_run')
            self.assertFalse(runtime.exists())
            register.assert_not_called()

    def test_registration_and_legacy_journal_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder).resolve() / 'runtime'
            data = Path(folder).resolve() / 'data'
            recorder = Path(folder).resolve() / 'recorder.json'
            recorder.write_text(json.dumps({'keep': 'unchanged'}), 'utf-8')
            with patch.object(install, 'register_host') as register:
                result = install.install(self.args(runtime, '--data-dir', str(data), '--secretary-config', str(recorder)))
            register.assert_called_once_with(runtime / 'native-host.json')
            cfg = json.loads((runtime / 'host-config.json').read_text('utf-8'))
            self.assertEqual(cfg['journals'], str(data / 'journals'))
            self.assertEqual(json.loads((runtime / 'native-host.json').read_text('utf-8'))['allowed_origins'], ['chrome-extension://' + 'a' * 32 + '/'])
            self.assertTrue((runtime / 'lifecycle.py').is_file())
            self.assertEqual(json.loads(recorder.read_text('utf-8'))['keep'], 'unchanged')

    def test_invalid_id_and_in_source_runtime_are_rejected(self):
        # Use an isolated source tree: the laptop's legacy runtime can be an
        # intentional junction to a valid external installation.
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder).resolve()/'source'
            source.mkdir()
            with patch.object(install,'SOURCE',source):
                args = self.args(source / 'runtime')
                with self.assertRaises(ValueError):
                    install.install(args)
                args.extension_id = 'invalid'
                with self.assertRaises(ValueError):
                    install.install(args)
