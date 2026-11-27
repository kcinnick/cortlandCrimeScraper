"""Start a loopback-only, read-only preview with explicit local configuration."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path('.env.local'))
    parser.add_argument('--environment', choices=['development', 'test', 'production'], default='development')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535')
    if args.env_file.exists():
        load_dotenv(args.env_file, override=True)
    os.environ['DATABASE_ENV'] = args.environment
    os.environ['APP_READ_ONLY'] = '1'
    from flask_app.app import app
    app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()

