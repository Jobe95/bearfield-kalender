from setuptools import setup

APP = ['menuapp.py']
DATA_FILES = [
    ('', ['kalender.html', 'settings.html', 'state.json', 'notify.py', 'tasks.py',
          'icon.png', 'se.bearfieldit.deadlinenotis.plist']),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns',
    'plist': {
        'CFBundleName': 'BearField IT',
        'CFBundleDisplayName': 'BearField IT',
        'CFBundleIdentifier': 'se.bearfieldit.kalender',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0',
        'LSUIElement': True,
        'LSMinimumSystemVersion': '12.0',
        'NSHighResolutionCapable': True,
        'NSUserNotificationAlertStyle': 'banner',
    },
    'packages': ['rumps'],
    'includes': ['threading', 'http.server', 'json', 'subprocess',
                 'Foundation', 'AppKit', 'objc'],
}

setup(
    app=APP,
    name='BearField Kalender',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
