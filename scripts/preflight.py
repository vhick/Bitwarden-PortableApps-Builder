#!/usr/bin/env python3
"""Fail-safe duplicate publication check: 404 alone is a missing release."""
import argparse,json,os,pathlib,re,urllib.error,urllib.request

def main(info:pathlib.Path):
    ident=json.loads(info.read_text(encoding='utf-8'))
    repo=os.environ['GITHUB_REPOSITORY']
    sha=os.environ['GITHUB_SHA']
    if not re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo): raise RuntimeError('Invalid GitHub repository')
    if not re.fullmatch('[0-9a-f]{40}',sha): raise RuntimeError('Invalid builder SHA')
    tag=f'portable-bitwarden-v{ident["version"]}-b1r1-{sha[:8]}'
    url=f'https://api.github.com/repos/{repo}/releases/tags/{tag}'
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json',
       'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'User-Agent':'Bitwarden-PortableApps-Builder-b1r1'})
    try:
        with urllib.request.urlopen(req,timeout=35) as r: r.read(1024)
        skip='true'
        print('Matching build/release already exists; avoiding redundant build:',tag)
    except urllib.error.HTTPError as e:
        if e.code!=404: raise RuntimeError(f'GitHub release check failed HTTP {e.code}; refusing assumed 404') from e
        skip='false'
        print('New release tag confirmed absent:',tag)
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:
        f.write('exists='+skip+'\n')
        f.write('tag='+tag+'\n')
        f.write('version='+ident['version']+'\n')
    return skip

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--identity',required=True);a=p.parse_args()
    main(pathlib.Path(a.identity))
