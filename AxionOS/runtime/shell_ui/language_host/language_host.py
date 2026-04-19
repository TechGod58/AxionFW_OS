import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))

from event_bus import publish

STATE_PATH = Path(axion_path_str('config', 'TIME_LANGUAGE_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save(s):
    STATE_PATH.write_text(json.dumps(s, indent=2), encoding='utf-8')


def snapshot(corr='corr_lang_snap_001'):
    s = _load()
    out = {
        'ts': _now(),
        'corr': corr,
        'time': s.get('time', {}),
        'language': s.get('language', {}),
        'input': s.get('input', {}),
        'locale': s.get('locale', {}),
        'actions': [
            'set_display_language',
            'add_preferred_language',
            'remove_preferred_language',
            'set_primary_layout',
            'set_locale_profile',
            'set_speech_language'
        ]
    }
    publish('shell.time_language.refreshed', {'ok': True}, corr=corr, source='language_host')
    return out


def set_display_language(lang: str, corr='corr_lang_display_001'):
    s = _load()
    old = s['language']['display']
    s['language']['display'] = lang
    if lang not in s['language']['preferred']:
        s['language']['preferred'].insert(0, lang)
    _save(s)
    publish('shell.language.display.changed', {'old': old, 'new': lang}, corr=corr, source='language_host')
    return {'ok': True, 'code': 'LANG_DISPLAY_SET_OK', 'display': lang}


def add_preferred_language(lang: str, corr='corr_lang_add_001'):
    s = _load()
    if lang not in s['language']['preferred']:
        s['language']['preferred'].append(lang)
    _save(s)
    publish('shell.language.preferred.added', {'lang': lang}, corr=corr, source='language_host')
    return {'ok': True, 'code': 'LANG_PREFERRED_ADD_OK', 'lang': lang}


def remove_preferred_language(lang: str, corr='corr_lang_remove_001'):
    s = _load()
    if lang == s['language']['display']:
        return {'ok': False, 'code': 'LANG_REMOVE_ACTIVE_DENY'}
    s['language']['preferred'] = [x for x in s['language']['preferred'] if x != lang]
    _save(s)
    publish('shell.language.preferred.removed', {'lang': lang}, corr=corr, source='language_host')
    return {'ok': True, 'code': 'LANG_PREFERRED_REMOVE_OK', 'lang': lang}


def set_primary_layout(layout: str, corr='corr_layout_set_001'):
    s = _load()
    if layout not in s['input']['keyboard_layouts']:
        s['input']['keyboard_layouts'].append(layout)
    s['input']['primary_layout'] = layout
    _save(s)
    publish('shell.input.layout.changed', {'primary_layout': layout}, corr=corr, source='language_host')
    return {'ok': True, 'code': 'INPUT_LAYOUT_SET_OK', 'layout': layout}


def set_locale_profile(region: str, date_format: str, time_format: str, number_format: str, currency: str, first_day_of_week: str, corr='corr_locale_set_001'):
    s = _load()
    s['locale'] = {
        'region': region,
        'date_format': date_format,
        'time_format': time_format,
        'number_format': number_format,
        'currency': currency,
        'first_day_of_week': first_day_of_week
    }
    _save(s)
    publish('shell.locale.changed', s['locale'], corr=corr, source='language_host')
    return {'ok': True, 'code': 'LOCALE_SET_OK'}


def set_speech_language(lang: str, corr='corr_speech_lang_001'):
    s = _load()
    old = s['language']['speech']
    s['language']['speech'] = lang
    _save(s)
    publish('shell.language.speech.changed', {'old': old, 'new': lang}, corr=corr, source='language_host')
    return {'ok': True, 'code': 'LANG_SPEECH_SET_OK', 'speech': lang}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

