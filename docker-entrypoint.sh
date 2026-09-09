#!/bin/sh
# Static files depend on real settings (SECRET_KEY, DB env vars) which only
# exist at container runtime in ECS (from Secrets Manager / the task
# definition), not at image build time — so this runs here, not in the
# Dockerfile's build step. Idempotent, safe to run on every start.
set -e
python manage.py collectstatic --noinput
exec "$@"
