#!/usr/bin/python
import os
import sys

parent = lambda f: os.path.dirname(f)
appname = os.path.basename(parent(parent(__file__)))
path_to_parent = parent(parent(parent(__file__)))
sys.path.append(os.path.join(path_to_parent, appname))
from webhook import app as application
