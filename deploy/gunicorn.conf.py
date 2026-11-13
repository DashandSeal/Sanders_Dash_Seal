"""
Module: deploy.gunicorn.conf
Architectural Layer: Hardened WSGI Process Manager Engine
Design Standard: Platinum Blue Diamond Standard (Resource-Constrained Optimization)
Description: Optimizes thread allocations and network sockets for high-throughput
             Stripe webhook traffic running exclusively on Always Free infrastructure.
"""

import multiprocessing

# Network Socket Binding Bounds
# Match loopback parameters cleanly with the upstream proxy definitions in nginx.conf
bind = "127.0.0.1:8000"
backlog = 2048

# Dynamic Worker Micro-Allocation Pool Optimization
# Formula: (2 * CPU_Cores) + 1 capped defensively for Always Free constraints
workers = min((multiprocessing.cpu_count() * 2) + 1, 3)
worker_class = "sync"
threads = 2

# Anti-Slowloris Keepalive Gateways
# Synchronized with Nginx proxy_read_timeout and client_body_timeout variables
timeout = 30
keepalive = 4

# Payload Transfer Optimization Boundaries
max_requests = 1200
max_requests_jitter = 50
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Security Infrastructure Isolation
preload_app = True
user = 10001
group = 10001

# Clean Zero-Disk Performance Telemetry
# Suppresses verbose disk writing sweeps to prevent file system wear
accesslog = None
errorlog = "-"
loglevel = "warning"

def on_starting(server):
    """Sovereign initialization banner confirming active governance enforcement."""
    print("💎 [Platinum Core Engine]: Initializing Sanders Dash & Seal WSGI Worker Runtime...")
    print(f"⚡ [Resource Pool Allocations]: Active Workers: {workers} | Worker Threads: {threads}")
