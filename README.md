
# PID Resolution Monitor


Dependencies will be installed by Poetry

### Prerequisite
1. Python 
2. RabbitMQ instance

### Run the Application

1. Start a Docker RabbitMQ container with management app:  
```
$ docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management
```
2. Run the main app:
```
$ python main.py
```
3. Start the Celery process, navigate to the project directory in a new terminal, activate the virtual environment, and then run:
```
$ celery -A main.celery worker -l INFO -Q pid-resolution,pidmr --autoscale=1,10
```
Or start Celery with other options:
```
$ celery -A main.celery worker -l INFO -Q pid-resolution,pidmr –pool gevent –autoscale=10,1000
$ celery -A main.celery worker --concurrency=10 -l=DEBUG --without-mingle --without-gossip --without-heartbeat
```
### Flower
[Flower](https://flower.readthedocs.io/en/latest/) is a real-time web application monitoring and administration tool for Celery.
Optionally we can monitor the tasks submitted to Celery. To start the Flower process, Navigate to the project directory in a new terminal, activate the virtual environment, and then run:
```
$ celery -A main.celery flower --port=5555
```
Once the Flower starts we can see the submitted tasks at <http://localhost:5555/tasks>.

### Test the application

Visit http://127.0.0.1:9000/docs to see the API documentation provided by [Swagger UI](https://github.com/swagger-api/swagger-ui)

The server will start at <http://localhost:9000/docs>.

### References
* [Async Architecture with FastAPI, Celery, and RabbitMQ ](https://dassum.medium.com/async-architecture-with-fastapi-celery-and-rabbitmq-c7d029030377)
* https://github.com/sumanentc/fastapi-celery-rabbitmq-application
* https://docs.celeryq.dev/en/stable/index.html
* https://flower.readthedocs.io/en/latest/
* https://stackoverflow.com/questions/21233089/how-to-use-the-shared-task-decorator-for-class-based-tasks
* http://ask.github.io/celery/userguide/groups.html#groups
