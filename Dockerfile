FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -o Acquire::http::No-Cache=True \
    && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ARG USER=appuser
ARG UID=1000
RUN adduser --system --uid ${UID} --no-create-home ${USER}
USER ${USER}

EXPOSE 8000