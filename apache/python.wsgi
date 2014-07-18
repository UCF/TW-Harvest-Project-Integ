#!/usr/bin/python
import os
import sys
import logging
from logging import handlers
from logging import Formatter

parent = lambda f: os.path.dirname(f)
appname = os.path.basename(parent(parent(__file__)))
path_to_parent = parent(parent(parent(__file__)))
sys.path.append(os.path.join(path_to_parent, appname))
import settings
from webhook import app as application
log_handler = handlers.TimedRotatingFileHandler(settings.LOG_LOCATION, when=settings.LOG_ROTATE, interval=1, backupCount=3)
log_handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]', datefmt="%d-%m-%Y %H:%M:%S"))
log_handler.setLevel(settings.LOG_LVL)
application.logger.setLevel(settings.LOG_LVL)
application.logger.addHandler(log_handler)
