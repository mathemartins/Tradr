nbs:
	jupyter notebook

c-worker:
	celery -A tradr worker -l INFO

c-beat:
	celery -A tradr beat

c-beat-and-worker:
	celery -A tradr worker -l INFO --beat

.PHONY: nbs c-worker c-beat c-beat-and-worker