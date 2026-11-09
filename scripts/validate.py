#!/usr/bin/env python3
"""Independent layout, integrity, version, PE and upgrade-safety validation."""
import argparse, configparser, hashlib, json, pathlib, re, struct, sys, zipfile

def pe_arch(p):
    with p.open('rb') as f:
        assert f.read(2)==b'MZ',f'Not PE: {p}'
        f.seek(0x3c);off=struct.unpack('<I',f.read(4))[0]
        assert off<p.stat().st_size-6,'invalid PE offset'
        f.seek(off);assert f.read(4)==b'PE\x00\x00','missing PE header'
        return struct.unpack('<H',f.read(2))[0]

def validate(root:pathlib.Path,identity:pathlib.Path):
    j=json.loads(identity.read_text(encoding='utf-8'))
    assert root.name=='BitwardenPortable','wrong root folder name'
    app=root/'App'/'Bitwarden';info=root/'App'/'AppInfo'
    assert pe_arch(root/'BitwardenPortable.exe')==0x8664,'root launcher must be x64 real PE'
    assert pe_arch(app/'Bitwarden.exe')==0x8664,'upstream Bitwarden must be Windows x64 PE'
    assert (app/'resources'/'app.asar').is_file() or (app/'resources'/'app').is_dir(),'Electron resources missing'
    assert (app/'desktop_proxy.exe').is_file(),'browser integration proxy missing; cannot package incomplete app'
    for icon in ['appicon.ico','appicon_16.png','appicon_32.png']:
        assert (info/icon).is_file() and (info/icon).stat().st_size>32,icon+' missing'
    assert (info/'appicon.ico').read_bytes()[:4]==b'\x00\x00\x01\x00','invalid ico'
    for icon in ['appicon_16.png','appicon_32.png']:
        assert (info/icon).read_bytes()[:8]==b'\x89PNG\r\n\x1a\n','invalid png'
    cp=configparser.ConfigParser(interpolation=None);cp.optionxform=str
    cp.read(info/'appinfo.ini',encoding='utf-8')
    assert cp.get('Details','AppID')=='BitwardenDesktopCommunityPortable'
    assert cp.get('Version','PackageVersion')==j['version']+'.0'
    assert cp.get('Control','Start')=='BitwardenPortable.exe'
    for d in ['Data','Data/Profile','Data/Temp','Data/TraceGuard','Other/Source']:
        assert (root/d).is_dir(),d
    assert not (root/'Bitwarden.exe').exists(),'Wrong-mode root Bitwarden binary'
    assert not (root/'App'/'AppInfo'/'Launcher').exists(),'Not using PortableApps.com Launcher script'
    source=json.loads((root/'Other'/'Source'/'BUILD-IDENTITY.json').read_text(encoding='utf-8'))
    assert source['upstream_commit_sha']==j['upstream_commit_sha']
    assert source['asset_sha256']==j['asset_sha256']
    print('STATIC-VALIDATED: upstream x64 app, genuine launcher, proxy, icons, metadata, source identity, directories.')


def produce_zip(root:pathlib.Path,dist:pathlib.Path,version:str,buildsha:str):
    dist.mkdir(exist_ok=True,parents=True)
    name=f'BitwardenPortable_{version}_x64_b1r2_{buildsha[:8]}.zip'
    out=dist/name
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for child in sorted(root.rglob('*')):
            relative=child.relative_to(root.parent).as_posix()
            if child.is_dir(): z.writestr(relative+'/',b'')
            else: z.write(child,relative)
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
        if bad: raise RuntimeError('ZIP corruption at '+bad)
        names=z.namelist();prefix='BitwardenPortable/'
        for req in ['BitwardenPortable.exe','App/Bitwarden/Bitwarden.exe','App/AppInfo/appinfo.ini','Data/Profile/','Data/TraceGuard/','Other/Source/BUILD-IDENTITY.json']:
            if prefix+req not in names: raise RuntimeError('ZIP missing '+req)
    with out.open('rb') as handle:
        sha=hashlib.file_digest(handle,'sha256').hexdigest()
    (dist/'BUILD-CHECKSUMS.txt').write_text(f'{sha}  {name}\n',encoding='utf-8')
    print('INDEPENDENT-ZIP-VALIDATED:',out,'SHA256',sha)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--identity',required=True)
    p.add_argument('--dist',required=True);p.add_argument('--builder-sha',required=True)
    a=p.parse_args();root=pathlib.Path(a.root);identity=pathlib.Path(a.identity)
    validate(root,identity)
    info=json.loads(identity.read_text(encoding='utf-8'))
    produce_zip(root,pathlib.Path(a.dist),info['version'],a.builder_sha)
