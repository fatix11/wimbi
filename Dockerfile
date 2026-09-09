# Runs the Django app under granian (already in requirements.txt, previously
# unconfigured — see aws_migration.md). No frontend build stage: Wimbi has
# no separate frontend, HTMX/Tailwind/Chart.js load from CDN in templates
# (ADR-010), so this image is the whole app.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary avoids needing libpq-dev/build-essential here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# collectstatic needs real settings (SECRET_KEY, DB env vars), which only
# exist at container runtime in ECS — not at image build time — so it runs
# via the entrypoint on every start, not as a build step.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["granian", "--interface", "wsgi", "--host", "0.0.0.0", "--port", "8000", "config.wsgi:application"]
