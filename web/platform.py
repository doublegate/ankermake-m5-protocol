import os
import platform as py_platform

import libflagship.logincache


def os_platform(os_family: str):
    if os_family.startswith('Mac OS') or os_family.startswith('Darwin'):
        return 'macos'
    elif os_family.startswith('Windows'):
        return 'windows'
    elif 'Linux' in os_family:
        return 'linux'
    else:
        return None


def current_platform():
    return os_platform(py_platform.system())


def login_path(platform: str):
    if platform == 'macos':
        return '~/Library/Application Support/AnkerMake/AnkerMake_64bit_fp/login.json'
    elif platform == 'windows':
        return r'%LOCALAPPDATA%\eufyMake Studio Profile\EBWebView\Default\Local Storage\leveldb\*.ldb'
    else:
        return 'Unsupported OS: You must supply path to login.json/user_info'


def _login_candidates(platform: str):
    if platform == 'macos':
        return [os.path.expanduser('~/Library/Application Support/AnkerMake/AnkerMake_64bit_fp/login.json')]

    if platform == 'windows':
        candidates = []
        leveldb_dir = os.path.expandvars(
            r'%LOCALAPPDATA%\eufyMake Studio Profile\EBWebView\Default\Local Storage\leveldb'
        )
        if os.path.isdir(leveldb_dir):
            for name in sorted(os.listdir(leveldb_dir), reverse=True):
                if name.lower().endswith(('.ldb', '.log')):
                    candidates.append(os.path.join(leveldb_dir, name))

        candidates.extend([
            os.path.expandvars(r'%APPDATA%\eufyMake Studio Profile\cache\offline\user_info'),
            os.path.expandvars(r'%LOCALAPPDATA%\Ankermake\AnkerMake_64bit_fp\login.json'),
            os.path.expandvars(r'%LOCALAPPDATA%\Ankermake\login.json'),
        ])
        return candidates

    return []


def autodetect_login_path(platform: str | None = None):
    platform = platform or current_platform()

    for candidate in _login_candidates(platform):
        if not os.path.isfile(candidate):
            continue

        if candidate.lower().endswith(('.ldb', '.log')):
            try:
                with open(candidate, 'rb') as probe:
                    if not libflagship.logincache.has_webview_session_marker(probe.read()):
                        continue
            except OSError:
                continue

        return candidate

    return None
