"""Read-only setup check; this is a utility, not the student pipeline solution."""
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
url = os.getenv('DATABASE_URL')
if not url:
    sys.exit('DATABASE_URL missing: copy starter/.env.example to starter/.env first.')

row = None
try:
    import psycopg
    with psycopg.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_setting('server_version'), extversion FROM pg_extension WHERE extname = 'vector'")
            row = cursor.fetchone()
except Exception:
    try:
        import pg8000.native
        parsed = urlsplit(url)
        conn = pg8000.native.Connection(
            user=parsed.username or 'day6',
            password=parsed.password or 'day6_local_only',
            host=parsed.hostname or '127.0.0.1',
            port=parsed.port or 55433,
            database=parsed.path.lstrip('/') or 'day6_lab'
        )
        res = conn.run("SELECT current_database(), current_setting('server_version'), extversion FROM pg_extension WHERE extname = 'vector'")
        if res:
            row = res[0]
        conn.close()
    except Exception as e:
        sys.exit(f'Database connection failed: {e}. Check Docker, port and DATABASE_URL in starter/.env.')

if not row:
    sys.exit('Connected, but pgvector extension is missing. See starter/README.md.')

print(f'Database: {row[0]} | PostgreSQL: {row[1]} | pgvector: {row[2]}')
print('Setup OK. Pipeline functions still need to be implemented.')
