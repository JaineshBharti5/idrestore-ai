import os
import sys

import uvicorn
from pyngrok import ngrok

from app import config

PORT = 8000


def main():
    token = os.environ.get("NGROK_AUTHTOKEN")
    if not token:
        sys.exit("Add NGROK_AUTHTOKEN to backend/.env first.")
    if not config.FRONTEND_DIST.exists():
        print("Warning: frontend/dist not found. Run 'npm run build' in the frontend folder so the public URL shows the website.")
    ngrok.set_auth_token(token)
    tunnel = ngrok.connect(PORT, "http")
    print("=" * 54)
    print("YOUR PUBLIC WEBSITE URL IS LIVE!")
    print(f"URL: {tunnel.public_url}")
    print("=" * 54)
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=False)
    finally:
        ngrok.kill()


if __name__ == "__main__":
    main()
