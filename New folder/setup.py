from setuptools import setup

APP = ['SearchTask_v0.1.py']
OPTIONS = {
    'argv_emulation': True,
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
)
