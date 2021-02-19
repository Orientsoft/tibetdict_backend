from celery import Celery
from config import BROKER_URL,RESULT_BACKEND

celery_app = Celery()


class Config:
    broker_url = BROKER_URL
    result_backend = RESULT_BACKEND


celery_app.config_from_object(Config)


if __name__ == '__main__':
    task = celery_app.send_task('worker:origin_stat', args=['0d9af3a871b711eb964f080027ce4314'], queue='tibetan',
                                routing_key='tibetan')
    print(task)
