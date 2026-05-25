"""
THE INNER CITADEL — celery_config.py (stub — Celery not used)
FastAPI BackgroundTasks replaced Celery. No Redis needed.
Kept so existing imports don't crash.
"""
import os
CELERY_BROKER_URL    = os.getenv("CELERY_BROKER_URL",    "memory://")
CELERY_RESULT_BACKEND= os.getenv("CELERY_RESULT_BACKEND","cache+memory://")
