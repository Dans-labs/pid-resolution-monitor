FROM python:3.12-slim

ARG BASE_DIR
ENV BASE_DIR=${BASE_DIR}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd -m resolution

WORKDIR $BASE_DIR

COPY pyproject.toml .
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install

USER resolution

RUN mkdir -p $BASE_DIR/logs \
    && touch $BASE_DIR/logs/prm.log

WORKDIR $BASE_DIR/app
COPY . .

ENTRYPOINT ["bash", "./run.sh"]