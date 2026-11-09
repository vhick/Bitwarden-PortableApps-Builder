#!/usr/bin/env python3
"""Resolve a verified Bitwarden DESKTOP stable release, with no main-branch fallback."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, re, sys, urllib.error, urllib.request

BASE='https://api.github.com/repos/bitwarden/clients'
VERSION=re.compile(r'^desktop-v(\d+)\.(\d+)\.(\d+)$')
ASSET=re.compile(r'^Bitwarden-Portable-(\d+\.\d+\.\d+)\.exe$')


def request(url: str, binary=False):
    if not url.startswith('https://api.github.com/') and not url.startswith('https://raw.githubusercontent.com/bitwarden/clients/'):
        raise ValueError('Unexpected source host: '+url)
    headers={'Accept':'application/vnd.github+json','User-Agent':'Bitwarden-PortableApps-Builder-b1r1','X-GitHub-Api-Version':'2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60) as r:
            data=r.read(60*1024*1024+1)
            if len(data)>60*1024*1024: raise RuntimeError('Remote response too large')
            return data if binary else json.loads(data)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'GitHub request failed HTTP {e.code} for {url} (no unverified fallback)') from e


def choose_release(version:str):
    if version != 'latest':
        if not re.fullmatch(r'\d+\.\d+\.\d+',version):
            raise ValueError('Specific version must be stable numeric X.Y.Z')
        rel=request(f'{BASE}/releases/tags/desktop-v{version}')
        items=[rel]
    else:
        items=[]
        # Only inspect reasonably recent GitHub releases. They mix desktop/browser/web/CLI.
        for page in range(1,5):
            batch=request(f'{BASE}/releases?per_page=50&page={page}')
            if not isinstance(batch,list): raise RuntimeError('GitHub releases API did not return an array')
            items.extend(batch)
            desktop=[x for x in items if VERSION.fullmatch(x.get('tag_name','')) and not x.get('draft') and not x.get('prerelease')]
            if len(desktop)>=5 or len(batch)<50: break
    stable=[x for x in items if VERSION.fullmatch(x.get('tag_name','')) and not x.get('draft') and not x.get('prerelease')]
    if not stable: raise RuntimeError('No stable desktop release found; no main-branch fallback')
    stable.sort(key=lambda x:tuple(map(int,VERSION.fullmatch(x['tag_name']).groups())),reverse=True)
    rel=stable[0]
    if version!='latest' and rel['tag_name']!=f'desktop-v{version}': raise RuntimeError('Version mismatch')
    return rel


def resolve(version:str, output:pathlib.Path):
    release=choose_release(version)
    tag=release['tag_name']; ver=tag.removeprefix('desktop-v')
    exact=f'Bitwarden-Portable-{ver}.exe'
    assets=[a for a in release.get('assets',[]) if a.get('name')==exact]
    if len(assets)!=1: raise RuntimeError(f'Expected one official Windows portable asset {exact}; found {len(assets)}')
    asset=assets[0]
    digest=asset.get('digest','') or ''
    if not re.fullmatch('sha256:[0-9a-fA-F]{64}',digest):
        raise RuntimeError('No vendor/GitHub SHA-256 digest for selected asset. Refusing unverifiable download.')
    url=asset.get('browser_download_url','')
    expected=f'https://github.com/bitwarden/clients/releases/download/{tag}/{exact}'
    if url != expected: raise RuntimeError(f'Unexpected official download URL {url!r}')
    commit=request(f'{BASE}/commits/{tag}')['sha']
    if not re.fullmatch('[a-f0-9]{40}',commit): raise RuntimeError('Invalid resolved source SHA')
    lock_url=f'https://raw.githubusercontent.com/bitwarden/clients/{commit}/package-lock.json'
    lock_hash=hashlib.sha256(request(lock_url,binary=True)).hexdigest()
    info={'application':'Bitwarden Desktop','version':ver,'upstream_repository':'bitwarden/clients',
          'upstream_release_tag':tag,'upstream_commit_sha':commit,'upstream_lockfile_sha256':lock_hash,
          'asset_filename':exact,'distribution_flavor':'upstream-noncommercial-OSS-asset','asset_url':url,'asset_sha256':digest.split(':',1)[1].lower(),
          'asset_size':asset.get('size'), 'release_id':release['id'],
          'release_published_at':release.get('published_at'),
          'builder_revision':'b1r1','package_revision':'b1r1',
          'package_builder':'vhick/Portable-Package-Builder@v1.0.0',
          'release_publisher':'vhick/portable-release-publisher@v1.1.1'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Resolved {tag} / {commit}, SHA256 {info["asset_sha256"]}')
    print(f'Identity at {output}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='latest');p.add_argument('--output',required=True)
    a=p.parse_args();resolve(a.version,pathlib.Path(a.output))
