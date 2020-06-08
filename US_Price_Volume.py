import DB
import threading
import multiprocessing

max_threads = multiprocessing.cpu_count() * 4
vpn_event=None
db_lock = threading.Lock()
db_sem = threading.BoundedSemaphore(max_threads)
DB.fork_db_process('US', db_sem, db_lock, vpn_event)
