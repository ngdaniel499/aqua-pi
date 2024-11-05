# Gunicorn configuration file for Aqua Pi Webapp

# Worker processes
workers = 3  # Adjust based on your CPU cores: (2 * num_cores) + 1
worker_class = 'sync'  # 'sync' is often better for CPU-bound tasks

# Threads per worker
threads = 1  # For CPU-bound tasks, single-threaded workers often perform better

# Binding
bind = "127.0.0.1:8000"

# Timeout settings
timeout = 300  # Increased timeout for long-running tasks
graceful_timeout = 60

# Restart workers after handling this many requests
max_requests = 10
max_requests_jitter = 5

# Preload application code before worker processes are forked
preload_app = True

# Logging
errorlog = '/home/ubuntu/aqua-pi-webapp/logs/gunicorn-error.log'
accesslog = '/home/ubuntu/aqua-pi-webapp/logs/gunicorn-access.log'
loglevel = 'info'

# Process naming
proc_name = 'gunicorn_aquapi'

# Memory optimization
worker_tmp_dir = '/dev/shm'

# Limit the number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50
