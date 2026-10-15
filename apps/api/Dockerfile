# Build from the REPO ROOT so the seed corpus, migration, ABIs and deployments are included:
#   docker build -f apps/api/Dockerfile -t sci-api .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY apps/api/app apps/api/app
COPY apps/api/demo_forms apps/api/demo_forms
COPY data data
COPY supabase supabase
COPY packages/shared/abis.json packages/shared/abis.json
COPY contracts/deployments contracts/deployments

WORKDIR /srv/apps/api
ENV DATA_DIR=/srv/apps/api/.data
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
