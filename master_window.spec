# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['master_window.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'torch', 'torchvision', 'torchaudio', 'tensorflow', 'keras', 'jax', 'spacy', 'thinc', 'langcodes', 'numba', 'llvmlite', 'sympy', 'nltk', 'transformers', 'librosa', 'soundfile', 'pyarrow', 'fsspec', 'OpenGL', 'pygame', 'IPython', 'notebook', 'nbformat', 'nbconvert', 'jupyterlab', 'faiss_cpu', 'rapidfuzz', 'tests', '*.tests', 'matplotlib.tests'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='master_window',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['DFA.ico'],
)
