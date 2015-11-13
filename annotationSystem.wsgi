#import sys
#from sys import os

#sys.path.insert(0, os.path.dirname('/var/www/annotationSystem2/server.py'))
#application=app
#from app import app as application
#from werkzeug.debug import DebuggedApplication
import sys
sys.path.insert(0,'/var/www/annotationSystem2')
from server import app as application
#application = DebuggedApplication(app, True)
