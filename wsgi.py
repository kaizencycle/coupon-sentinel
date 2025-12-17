import sys
import os

# Add the project root to the python path
# This ensures 'backend' module can be found regardless of how the app is started
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also handle Render's specific directory structure
render_src = "/opt/render/project/src"
if os.path.isdir(render_src) and render_src not in sys.path:
    sys.path.insert(0, render_src)

from backend.app import app

# Expose 'app' for WSGI/ASGI servers (uvicorn wsgi:app)
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
