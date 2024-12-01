import re
import asyncio
import requests
from constants import API_GITHUB_ENDPOINT
from semver import Version
from version_handler import __version_semver__, _get_semver_version

def remove_ansi_escape(text):
    # 7-bit C1 ANSI sequences
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)
    return ansi_escape.sub('', text)

def wait_awaitable(coroutine_):
    loop = asyncio.new_event_loop()
    return loop.run_until_complete(coroutine_)

def convert_version_to_tuple(version):
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:\.(dev|a|b|rc)(\d+)?)?$"
    match = re.match(pattern, version)
    if not match:
        raise ValueError(
            "Version string must follow the format 'major.minor.patch[.qualifier[qualifier_number]]'."
        )
    major, minor, patch, stage, stage_number = match.groups()
    major, minor, patch = int(major), int(minor), int(patch)
    stage = stage or 'final'
    stage_number = int(stage_number) if stage_number else 0
    return (major, minor, patch, stage, stage_number)


def check_version():
    #Code response, (local, remote, code)
    #code: 0=latest, 1=outdated, 2=local is future, -1 = error
    try:
        response = requests.get(API_GITHUB_ENDPOINT)
        response.raise_for_status()
    except requests.RequestException as e:
        return str(e), e, -1
    response_data = response.json()
    remote_version = convert_version_to_tuple(response_data["tag_name"])
    latest_remote_version = Version.parse(_get_semver_version(remote_version))
    current_local_version = Version.parse(__version_semver__)
    if current_local_version.compare(latest_remote_version) < 0:
        return current_local_version, latest_remote_version, 1
    elif current_local_version.compare(latest_remote_version) > 0:
        return current_local_version, latest_remote_version, 2
    return current_local_version, latest_remote_version, 0
