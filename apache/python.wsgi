#!/usr/bin/python
import os
import sys
import site

site.addsitedir('/var/www/apps/TW-Harvest-Project-Integ/lib/python2.6/site-packages')

if '/usr/lib64/python2.6/site-packages' in sys.path:
        sys.path.remove('/usr/lib64/python2.6/site-packages')
if '/usr/lib/python2.6/site-packages' in sys.path:
        sys.path.remove('/usr/lib/python2.6/site-packages')

parent = lambda f: os.path.dirname(f)
appname = os.path.basename(parent(parent(__file__)))
path_to_parent = parent(parent(parent(__file__)))
sys.path.append(os.path.join(path_to_parent, appname))
from webhook import app as application
