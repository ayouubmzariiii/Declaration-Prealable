import sys
import os

# Add the root directory to the sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from serverless_wsgi import handle_request
from app import app

def handler(event, context):
    # Strip the Netlify function prefix from the path so Flask receives the intended route
    path = event.get('path', '')
    if path.startswith('/.netlify/functions/api'):
        new_path = path.replace('/.netlify/functions/api', '', 1)
        event['path'] = new_path if new_path else '/'
    
    return handle_request(app, event, context)
