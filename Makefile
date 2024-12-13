nbs:
	jupyter notebook

c-worker:
	celery -A tradr worker -l INFO --pool=solo

c-beat:
	celery -A tradr beat

c-beat-and-worker:
	celery -A tradr worker -l INFO --beat --pool=solo

.PHONY: nbs c-worker c-beat c-beat-and-worker