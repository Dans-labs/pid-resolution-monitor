PORT=${PORT:-8080}
uvicorn main:app --host 0.0.0.0 --port "$PORT" &
celery -A main.celery worker -l INFO -Q pid-resolution,pidmr,celery --autoscale=1,10
