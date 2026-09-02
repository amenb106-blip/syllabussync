import os
import sys

# Vercel runs this file as the serverless entry point. The Flask app lives at
# the project root, so make that folder importable before loading it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401
