FROM python:3.12-slim

ARG BASE_DIR=/home/resolution
ARG PORT=9000

ENV PORT=${PORT}
ENV BASE_DIR=${BASE_DIR}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 -s /bin/bash resolution

WORKDIR $BASE_DIR

COPY pyproject.toml .
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root

COPY . $BASE_DIR/app/
RUN mkdir -p ${BASE_DIR}/logs \
    && touch ${BASE_DIR}/logs/prm.log \
    && chown -R resolution:resolution ${BASE_DIR}

USER resolution

WORKDIR $BASE_DIR/app

ENTRYPOINT ["bash", "./run.sh"]