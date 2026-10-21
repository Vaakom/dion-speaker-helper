"""Durable per-tab lifecycle, independent of a native host process lifetime."""
import json
from pathlib import Path
import re
import time

END_REASONS = {'tab_closed', 'browser_window_closed', 'meeting_ended', 'meeting_page_closed'}


def lifecycle_path(root, client, tab):
    if not isinstance(client, str) or not re.fullmatch(r'[a-zA-Z0-9-]{8,80}', client):
        raise ValueError('Invalid lifecycle client')
    if not isinstance(tab, int) or isinstance(tab, bool) or tab < 0:
        raise ValueError('Invalid lifecycle tab')
    return Path(root) / 'lifecycle' / client / f'{tab}.json'


def save_lifecycle(root, value):
    path = lifecycle_path(root, value['client'], value['tab'])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')
    tmp.replace(path)


def end_lifecycle(root, msg):
    reason = msg.get('reason')
    if reason not in END_REASONS:
        return  # Old extension messages are not evidence for automatic stopping.
    path = lifecycle_path(root, msg['client'], msg['tab'])
    try:
        value = json.loads(path.read_text('utf-8'))
    except FileNotFoundError:
        return
    if value.get('page_id') != msg['page_id'] or value.get('state') == 'ended':
        return
    ended = time.time()
    event = {key: value[key] for key in ('page_id', 'meeting_id')}
    event.update(reason=reason, ended_at=ended)
    value['ends'] = (value.get('ends', []) + [event])[-16:]
    value.update(state='ended', reason=reason, ended_at=ended)
    save_lifecycle(root, value)


def active_lifecycle(root, msg):
    if msg.get('lifecycle_version') != 1:
        return
    path = lifecycle_path(root, msg['client'], msg['tab'])
    try:
        previous = json.loads(path.read_text('utf-8'))
    except FileNotFoundError:
        previous = {}
    save_lifecycle(root, {key: msg[key] for key in ('client', 'tab', 'page_id', 'meeting_id')} |
                   {'state': 'active', 'last_at': time.time(), 'lifecycle_version': 1,
                    'ends': previous.get('ends', [])})
