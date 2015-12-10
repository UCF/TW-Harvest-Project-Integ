import logging

DEBUG = False
LOG_LVL = logging.DEBUG
LOG_LOCATION = ''
LOG_ROTATE = 'midnight'
LOG_TEXT_FMT = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
LOG_DATE_FMT = '%Y-%m-%d %H:%M:%S' 

# the base url for teamwork (include ending slash)
TEAMWORK_BASE_URL = 'http://foo.teamworkpm.net/'

# teamwork api user/pass (password can be anything)
TEAMWORK_USER = ''
TEAMWORK_PASS = ''

# the base url for harvest (include ending slash)
HARVEST_BASE_URL = 'https://foo.harvestapp.com/'

# harvest api user/password
HARVEST_USER = ''
HARVEST_PASS = ''

# Teamwork project name format
TEAMWORK_PROJECT_NAME_SCHEME = '^[0-9]{4}-[A-Z]+-[0-9]+ .*$'

# Teamwork database config
DATABASE = {
  'drivername':   '',
  'host':         '',
  'port':         '',
  'username':     '',
  'password':     '',
  'database':     ''
}
