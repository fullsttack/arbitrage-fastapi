# arbitrage-fastapi



# Terminal 1: Celery Worker
celery -A config worker --loglevel=info

# Terminal 2: Celery Beat  
celery -A config beat --loglevel=info



