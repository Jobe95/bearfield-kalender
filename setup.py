from setuptools import setup

APP = ['menuapp.py']
DATA_FILES = [
    ('', ['kalender.html', 'settings.html', 'state.json', 'notify.py', 'tasks.py']),
]
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'BearField Kalender',
        'CFBundleDisplayName': 'BearField Kalender',
        'CFBundleIdentifier': 'se.bearfieldit.kalender',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0',
        'LSUIElement': True,          # Bakgrundsapp — ingen ikon i Dock
        'LSMinimumSystemVersion': '12.0',
        'NSHighResolutionCapable': True,
    },
    'packages': ['rumps'],
    'includes': ['threading', 'http.server', 'json', 'subprocess'],
}

setup(
    app=APP,
    name='BearField Kalender',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
