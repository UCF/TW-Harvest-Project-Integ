try:
    from settings_local import *
except ImportError:
    raise Exception(
        'Local settings file was not found. ' +
        'Ensure settings_local.py exists in project root.'
    )
