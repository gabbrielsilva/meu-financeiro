#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.deploy.txt
python manage.py check --deploy
python manage.py collectstatic --noinput
python manage.py migrate --noinput
