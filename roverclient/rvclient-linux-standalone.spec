# -*- mode: python -*-

block_cipher = None


a = Analysis(['rvclient.py'],
              pathex=['../rovercommons', '/home/tonton/work/Code/perso/roverpi/roverclient'],
             binaries=None,
             datas=[('guidata/*.txt','guidata'),('configs/config_remote.txt','configs')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='rvclient-linux-standalone',
          debug=False,
          strip=False,
          upx=True,
          console=False )
