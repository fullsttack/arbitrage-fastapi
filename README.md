# arbitrage-fastapi



celery -A config worker --loglevel=info --concurrency=1


celery -A config beat --loglevel=info --scheduler=celery.beat:PersistentScheduler