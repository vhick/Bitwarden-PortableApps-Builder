#!/usr/bin/env python3
"""Unpack official Electron-builder Windows portable image; assemble PortableApps staging."""
from __future__ import annotations
import argparse, configparser, hashlib, json, os, pathlib, re, shutil, struct, subprocess, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]

def find_7z():
    choices=[shutil.which('7z'),shutil.which('7za')]
    if sys.platform=='win32':
        choices += [r'C:\Program Files\7-Zip\7z.exe',r'C:\Program Files (x86)\7-Zip\7z.exe']
    for exe in choices:
        if exe and pathlib.Path(exe).is_file(): return exe
    raise RuntimeError('7-Zip missing on Windows runner. Install 7zip from Chocolatey first.')

def extract(seven:str,archive:pathlib.Path,dest:pathlib.Path):
    dest.mkdir(parents=True,exist_ok=True)
    cmd=[seven,'x',str(archive),'-y','-o'+str(dest)]
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=900)
    print(result.stdout[-8000:])
    if result.returncode!=0: raise RuntimeError(f'7-Zip failed ({result.returncode}) for {archive.name}')

def pe_arch(path:pathlib.Path):
    with path.open('rb') as f:
        if f.read(2)!=b'MZ': return None
        f.seek(0x3c); off=struct.unpack('<I',f.read(4))[0]
        if off>path.stat().st_size-6: return None
        f.seek(off)
        if f.read(4)!=b'PE\x00\x00': return None
        return struct.unpack('<H',f.read(2))[0]

def find_app(temp:pathlib.Path,dst:pathlib.Path):
    seven=find_7z()
    outers=sorted(temp.rglob('app-64.7z'),key=lambda p:len(p.parts))
    if not outers: outers=sorted(temp.rglob('*64*.7z'),key=lambda p:len(p.parts))
    if outers:
        print('Extracting official embedded Windows 64-bit application archive',outers[0])
        extract(seven,outers[0],dst)
        roots=list(dst.rglob('Bitwarden.exe'))
        if len(roots)==1 and roots[0].parent!=dst:
            inner=roots[0].parent
            for child in list(inner.iterdir()): shutil.move(str(child),str(dst/child.name))
        elif len(roots)!=1: raise RuntimeError('Official archive contained zero/multiple Bitwarden.exe binaries')
    else:
        # Some archive revisions expose the extracted Electron app directly.
        roots=list(temp.rglob('Bitwarden.exe'))
        roots=[p for p in roots if (p.parent/'resources').is_dir()]
        if len(roots)!=1:
            raise RuntimeError('Could not locate uniquely identifiable x64 Bitwarden.exe in official portable image; release packaging changed')
        shutil.copytree(roots[0].parent,dst,dirs_exist_ok=True)
    app=dst/'Bitwarden.exe'
    if not app.is_file() or pe_arch(app)!=0x8664:
        raise RuntimeError('Unpacked official Windows application missing or not x64 PE')
    if not (dst/'resources').is_dir():
        raise RuntimeError('Official app resources missing')
    if not (dst/'resources'/'app.asar').exists() and not (dst/'resources'/'app').is_dir():
        raise RuntimeError('Missing Electron application resources')
    print('Official app unpacked:',app,'size',app.stat().st_size)


def get_official_text(commit:str,file:str):
    url=f'https://raw.githubusercontent.com/bitwarden/clients/{commit}/{file}'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Bitwarden-PortableApps-Builder-b1r2'}),timeout=45) as r:
        data=r.read(2*1024*1024)
    return data.decode('utf-8')


def stage(identity_file:pathlib.Path,download_dir:pathlib.Path,work_dir:pathlib.Path,launch_exe:pathlib.Path):
    info=json.loads(identity_file.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[a-f0-9]{40}',info['upstream_commit_sha']): raise RuntimeError('Invalid source commit')
    binary=download_dir/info['asset_filename']
    if not binary.exists(): raise RuntimeError('Official portable asset missing')
    with binary.open('rb') as handle:
        actual=hashlib.file_digest(handle,'sha256').hexdigest()
    if actual!=info['asset_sha256']:
        raise RuntimeError('Upstream binary mismatch prior to extraction')
    root=work_dir/'BitwardenPortable'; app_dir=root/'App'/'Bitwarden'
    raw=work_dir/'official-extraction'; raw.mkdir(parents=True,exist_ok=True)
    app_dir.mkdir(parents=True,exist_ok=True)
    extract(find_7z(),binary,raw)
    find_app(raw,app_dir)
    launcher=root/'BitwardenPortable.exe'
    if not launch_exe.is_file() or pe_arch(launch_exe)!=0x8664: raise RuntimeError('Real compiled x64 root launcher missing')
    shutil.copy2(launch_exe,launcher)
    for rel in ['Data/Profile','Data/Temp','Data/TraceGuard','Other/Source','App/AppInfo']:
        (root/rel).mkdir(parents=True,exist_ok=True)
    ini=f'''[Format]\nType=PortableApps.comFormat\nVersion=3.8\n\n[Details]\nName=Bitwarden Desktop Portable (Community)\nAppID=BitwardenDesktopCommunityPortable\nPublisher=Bitwarden Inc. (application); community builder (launcher)\nHomepage=https://github.com/bitwarden/clients\nCategory=Security\nDescription=Unofficial PortableApps-style package of the official Bitwarden Desktop app\nLanguage=Multilingual\n\n[License]\nShareable=true\nOpenSource=true\nFreeware=true\nCommercialUse=true\n\n[Version]\nPackageVersion={info['version']}.0\nDisplayVersion={info['version']} Community b1r2\n\n[Control]\nIcons=1\nStart=BitwardenPortable.exe\n'''
    (root/'App'/'AppInfo'/'appinfo.ini').write_text(ini,encoding='utf-8')
    # Source tree is not modified; preserve vendor license and source location.
    for filename in ('LICENSE.txt','LICENSE_GPL.txt','LICENSE_BITWARDEN.txt'):
        (root/'Other'/'Source'/filename).write_text(get_official_text(info['upstream_commit_sha'],filename),encoding='utf-8')
    shutil.copy2(ROOT/'launcher'/'BitwardenPortable'/'Program.cs',root/'Other'/'Source'/'BitwardenPortable-Program.cs')
    shutil.copy2(ROOT/'launcher'/'BitwardenPortable'/'BitwardenPortable.csproj',root/'Other'/'Source'/'BitwardenPortable.csproj')
    shutil.copy2(ROOT/'licenses'/'LICENSE-launcher-MIT.txt',root/'Other'/'Source'/'LICENSE-launcher-MIT.txt')
    (root/'Other'/'Source'/'BUILD-IDENTITY.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    (root/'Other'/'Source'/'README.txt').write_text(
        'Unofficial Bitwarden PortableApps-style community package.\n'
        'Application source: https://github.com/bitwarden/clients/tree/'+info['upstream_commit_sha']+'/apps/desktop\n'
        'Vendor portable original: '+info['asset_url']+'\n'
        'Launcher: MIT-licensed source included in this folder.\n'
        'Application licensing: see upstream LICENSE files here. The software and logo are Bitwarden-owned.\n'
        'Portable settings: Data\\Profile; logs: Data\\Profile\\logs.\n'
        'Installed Bitwarden profiles are NEVER imported, deleted, or edited by this community launcher.\n'
        'ShellGuard: narrowly snapshots 6 browser native messaging keys and the Bitwarden user Run value.\n'
        'Do not use browser integration/autostart on a USB drive that moves often without retesting.\n',encoding='utf-8')
    (root/'README.txt').write_text(
        'BITWARDEN DESKTOP PORTABLE (COMMUNITY, UNOFFICIAL)\n\n'
        'Run BitwardenPortable.exe. Vault data is stored in Data\\Profile.\n'
        'To quit: use the Bitwarden tray icon > Quit, then eject USB drive.\n'
        'Do not run the same portable folder from two Windows sessions simultaneously.\n'
        'Upgrade: BACK UP Data first. Replace App, AppInfo, Other, root launcher; NEVER DELETE Data.\n'
        'Launch logs and cautious registry recovery: Data\\TraceGuard.\n'
        'Browser integration, startup settings, Windows notifications, biometrics and OS caches may involve host state.\n'
        'This is not an official Bitwarden or PortableApps.com distribution.\n'
        'PortableApps-style installer is generated separately from this ZIP.\n',encoding='utf-8')
    print('Staged package at',root)
    return root

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--identity',required=True);p.add_argument('--downloads',required=True)
    p.add_argument('--work',required=True);p.add_argument('--launcher',required=True)
    a=p.parse_args()
    stage(pathlib.Path(a.identity),pathlib.Path(a.downloads),pathlib.Path(a.work),pathlib.Path(a.launcher))
