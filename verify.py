"""Run synthetic product checks; optionally verify an existing native host."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def check_installed_identity(runtime, extension_id):
    if not extension_id:
        raise ValueError('Actual extension ID is required for installed-host verification')
    origin = 'chrome-extension://' + extension_id + '/'
    cfg = json.loads((runtime / 'host-config.json').read_text('utf-8'))
    manifest = json.loads((runtime / 'native-host.json').read_text('utf-8'))
    if cfg.get('origin') != origin or manifest.get('allowed_origins') != [origin]:
        raise ValueError('Installed Native Messaging origin differs from the configured actual extension ID')
    return origin


def main():
    config = ROOT / 'config.local.json'
    settings = json.loads(config.read_text('utf-8-sig')) if config.exists() else {}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default=settings.get('node') or shutil.which('node'))
    parser.add_argument('--runtime', type=Path, default=Path(settings['runtime']) if settings.get('runtime') else None)
    parser.add_argument('--extension-id', default=settings.get('extension_id'))
    args = parser.parse_args()
    if not args.node:
        parser.error('Node.js is required; set --node or add node to PATH')
    installed = {}
    if args.runtime:
        check_installed_identity(args.runtime, args.extension_id)
        installed = {name: (args.runtime / name).read_bytes()
                     for name in ('host-config.json', 'native-host.json', 'host.cmd')}
    for path in ROOT.glob('*.py'):
        compile(path.read_text('utf-8'), str(path), 'exec')
    subprocess.run([sys.executable, '-X', 'utf8', '-B', '-m', 'unittest',
        'test_helper', 'test_hybrid', 'test_browser_names', 'test_auto_journals', 'test_install'], cwd=ROOT, check=True)
    for path in (ROOT / 'extension').glob('*.js'):
        subprocess.run([args.node, '--check', str(path)], check=True)
    subprocess.run([args.node, '--test', *[str(ROOT / name) for name in
        ('test_content.cjs', 'test_auto_background.cjs', 'test_status.cjs', 'test_lifecycle.cjs', 'test_toolbar.cjs')]], check=True)
    if args.runtime:
        for name, before in installed.items():
            if (args.runtime / name).read_bytes() != before:
                raise RuntimeError('Tests modified installed runtime: ' + name)
        origin = check_installed_identity(args.runtime, args.extension_id)
        data = json.dumps({'type': 'unbind'}).encode('utf-8')
        result = subprocess.run([os.environ['COMSPEC'], '/d', '/c', str(args.runtime / 'host.cmd'), origin],
            input=struct.pack('<I', len(data)) + data, capture_output=True, timeout=15, check=True)
        size = struct.unpack('<I', result.stdout[:4])[0]
        reply = json.loads(result.stdout[4:4+size])
        assert reply == {'ok': True, 'state': 'detached'}, reply
        print('Existing native host round trip passed; no audio captured.')
    print('ALL PRODUCT CHECKS PASSED')


if __name__ == '__main__':
    main()
