"""Bounded WSGI server configuration; application release gates stay enforced."""
bind = '0.0.0.0:8000'
workers = 1
worker_class = 'sync'
timeout = 30
graceful_timeout = 30
keepalive = 2
preload_app = False
accesslog = None  # URLs can contain private case references or login parameters.
errorlog = '-'
capture_output = False
forwarded_allow_ips = ''
secure_scheme_headers = {}
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 4094
worker_tmp_dir = '/tmp'
