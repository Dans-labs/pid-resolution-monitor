uvicorn main:app --host 0.0.0.0 --port 9000 &
celery -A main.celery worker -l INFO -Q pid-resolution,pidmr,celery --autoscale=1,10
