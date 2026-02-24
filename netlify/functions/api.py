import sys
import os

# Add the root directory to the sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from serverless_wsgi import handle_request
from app import app

def handler(event, context):
    return handle_request(app, event, context)
