import time
from rq import Queue
from redis import Redis
from tasks import count_words_at_url
redis_conn = Redis()
queue = Queue(connection=redis_conn)
job = queue.enqueue(count_words_at_url, 'https://khashtamov.com/')
print(job.result)   
time.sleep(4)
print(job.result)
