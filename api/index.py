import os
import sys

# Add the root directory (one level up) to the sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Vercel needs the Flask 'app' object to route correctly
# There is no need for WSGI handlers in Vercel like in Netlify, 
# Vercel's python builder handles standard app objects automatically.
