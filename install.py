"""Register a local Dion host for an explicitly selected unpacked Chrome extension."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import winreg

SOURCE = Path(__file__).resolve().parent


def local_settings():
    path = SOURCE / 'config.local.json'
    return json.loads(path.read_text('utf-8-sig')) if path.exists() else {}


def make_parser(settings=None):
    settings = local_settings() if settings is None else settings
    data = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local' / 'share')))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extension-id', default=settings.get('extension_id'))
    parser.add_argument('--extension-path', type=Path, default=Path(settings.get('extension_path', SOURCE / 'extension')))
    parser.add_argument('--runtime', type=Path, default=Path(os.environ.get('DION_HELPER_RUNTIME', settings.get('runtime', data / 'DionSpeakerHelper' / 'runtime'))))
    parser.add_argument('--data-dir', type=Path, help='Legacy option: place journals under this directory')
    parser.add_argument('--sessions', type=Path, default=Path(settings.get('sessions', Path.home() / 'DionRecordings')))
    parser.add_argument('--active-file', type=Path, default=Path(settings.get('active_file', data / 'DionSecretary' / 'active.json')))
    parser.add_argument('--python', type=Path, default=Path(settings.get('python', sys.executable)))
    parser.add_argument('--secretary-config', type=Path, default=Path(settings['secretary_config']) if settings.get('secretary_config') else None)
    parser.add_argument('--dry-run', action='store_true')
    return parser


def register_host(path):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome\NativeMessagingHosts\local.dion_speaker_helper') as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(path))


def install(args):
    if not re.fullmatch('[a-p]{32}', args.extension_id or ''):
        raise ValueError('Set a valid --extension-id from chrome://extensions or config.local.json')
    runtime = args.runtime.expanduser().resolve()
    if runtime.is_relative_to(SOURCE):
        raise ValueError('Runtime must be outside the source checkout')
    python = args.python.expanduser().resolve()
    if not python.is_file():
        raise ValueError('Configured Python executable is missing')
    extension = args.extension_path.expanduser().resolve()
    if not (extension / 'manifest.json').is_file():
        raise ValueError('Configured extension directory is missing')
    journals = (args.data_dir.expanduser().resolve() if args.data_dir else runtime) / 'journals'
    secretary = None
    if args.secretary_config:
        secretary = json.loads(args.secretary_config.read_text('utf-8-sig'))
    origin = 'chrome-extension://' + args.extension_id + '/'
    config = {'active': str(args.active_file.expanduser().resolve()),
              'sessions': str(args.sessions.expanduser().resolve()), 'journals': str(journals), 'origin': origin}
    plan = {'runtime': str(runtime), 'extension': str(extension), 'extension_id': args.extension_id,
            'journals': str(journals), 'native_host': 'local.dion_speaker_helper'}
    if args.dry_run:
        return {**plan, 'state': 'dry_run'}
    runtime.mkdir(parents=True, exist_ok=True)
    for name in ('native_host.py', 'lifecycle.py'):
        shutil.copy2(SOURCE / name, runtime / name)
    (runtime / 'host-config.json').write_text(json.dumps(config, indent=2) + '\n', 'utf-8')
    launcher = runtime / 'host.cmd'
    launcher.write_text('@echo off\n"' + str(python) + '" -X utf8 -B "' + str(runtime / 'native_host.py') + '" %*\n', 'utf-8')
    manifest = runtime / 'native-host.json'
    manifest.write_text(json.dumps({'name': 'local.dion_speaker_helper', 'description': 'Dion local speaker journal',
        'path': str(launcher), 'type': 'stdio', 'allowed_origins': [origin]}, indent=2) + '\n', 'utf-8')
    register_host(manifest)
    if secretary is not None:
        secretary.update(journal_root=str(journals), speaker_helper_extension_id=args.extension_id,
                         speaker_helper_extension_path=str(extension))
        args.secretary_config.write_text(json.dumps(secretary, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return {**plan, 'state': 'registered', 'browser_install': 'manual'}


def main():
    parser = make_parser()
    args = parser.parse_args()
    try:
        result = install(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
