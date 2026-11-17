"""Start local prototype. In production, use managed identity, TLS and secret storage."""
from pathlib import Path
import os, secrets, sys
import uvicorn
if __name__ == '__main__':
    if not os.getenv('SCS_API_TOKEN'):
        print('Set SCS_API_TOKEN to a private random token first; example:')
        print(f'export SCS_API_TOKEN={secrets.token_urlsafe(32)}')
        sys.exit(1)
    os.environ.setdefault('SCS_DB_PATH',str(Path(__file__).resolve().parent/'state'/'secretary.sqlite3'))
    uvicorn.run('app.main:app', host='127.0.0.1', port=8765, reload=False)