"""
Broker settings
"""
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/0"

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# keep results for 45mins then auto‑expire - governs cleanup of Redis record
# doesn't govern cleanup of temp files stored server-side
result_expires = 2700
task_soft_time_limit = 900   # 15‑min soft timeout
task_time_limit = 1800        # 30‑min hard timeout
