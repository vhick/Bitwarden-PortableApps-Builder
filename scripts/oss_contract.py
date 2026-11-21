#!/usr/bin/env python3
"""Hard boundary between Bitwarden's upstream OSS and commercial distributions.

Source: desktop-v2026.11.0 release notes; before that release the unprefixed
Bitwarden desktop artifact was OSS. Scope legacy support to October 2026 builds
that were explicitly released alongside the commercial variant.
"""
from __future__ import annotations
import re

_SWITCH = (2026, 11, 0)
_EARLIEST_VERIFIED_LEGACY = (2026, 10, 0)
_NEW_FLAVOR = 'upstream-oss-gplv3'
_LEGACY_FLAVOR = 'upstream-noncommercial-OSS-asset'

def parse_version(version: str) -> tuple[int, int, int]:
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Stable desktop version must be X.Y.Z')
    return tuple(map(int, version.split('.')))

def oss_filename(version: str) -> str:
    numeric = parse_version(version)
    if numeric < _EARLIEST_VERIFIED_LEGACY:
        raise ValueError('OSS identity of releases older than 2026.10.0 is not verified by this builder; refusing fallback')
    prefix = 'oss-' if numeric >= _SWITCH else ''
    return f'{prefix}Bitwarden-Portable-{version}.exe'

def assert_oss_identity(identity: dict) -> None:
    version = identity['version']
    filename = oss_filename(version)
    if identity.get('asset_filename') != filename:
        raise RuntimeError(f'OSS-only guard: expected {filename}; got {identity.get("asset_filename")!r}')
    expected_tag = f'desktop-v{version}'
    if identity.get('upstream_release_tag') != expected_tag:
        raise RuntimeError('OSS-only guard: release tag and version disagree')
    expected_url = f'https://github.com/bitwarden/clients/releases/download/{expected_tag}/{filename}'
    if identity.get('asset_url') != expected_url:
        raise RuntimeError('OSS-only guard: asset URL is not the exact official OSS asset')
    expected_flavor = _NEW_FLAVOR if parse_version(version) >= _SWITCH else _LEGACY_FLAVOR
    if identity.get('distribution_flavor') != expected_flavor:
        raise RuntimeError('OSS-only guard: incorrect distribution flavor metadata')
    if not re.fullmatch(r'[a-fA-F0-9]{64}', identity.get('asset_sha256', '')):
        raise RuntimeError('OSS-only guard: upstream SHA-256 digest is absent or invalid')
