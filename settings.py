# POST keys stored for easy updating
EVENT      = 'event'
OBJECT_ID  = 'objectId'
ACCOUNT_ID = 'accountId'
USER_ID    = 'userId'

# API post events
PROJECT_CREATED = 'PROJECT.CREATED'
PROJECT_UPDATED = 'PROJECT.UPDATED'

# API request keys
ID       = 'id'
PROJECT  = 'project'
PROJECTS = 'projects'
COMPANY  = 'company'
NAME     = 'name'
PHONE    = 'phone'

# Status codes
SUCCESS_CODE = 200

# API request/post types
REQ_TYPE = '.json'
POST_CONTENT_HEADER = 'Content-Type'
POST_CONTENT_TYPE = 'application/json'

# API request/post locations
URL_PROJECTS = 'projects/'
URL_COMPANY = 'companies/'

# regex matching
PROJ_NAME_PATTERN = "^[0-9]*-[A-Z]*-[0-9]* .*$"

try:
    from settings_local import *
except ImportError:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'Local settings file was not found. ' +
        'Ensure settings_local.py exists in project root.'
    )