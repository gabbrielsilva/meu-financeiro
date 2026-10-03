#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.deploy.txt
python -c "from pathlib import Path; import certifi, shutil; Path('.local').mkdir(exist_ok=True); shutil.copyfile(certifi.where(), '.local/ca-bundle.pem')"
python scripts/check_database_tls.py
python manage.py check --deploy
python manage.py collectstatic --noinput
python manage.py migrate --noinput
