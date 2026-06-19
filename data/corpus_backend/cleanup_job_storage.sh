#!/bin/bash

# Path to your job storage directory
JOB_STORAGE_DIR="/mnt/data/corpus_backend/job_storage"

# Number of days to keep files before deleting
DAYS_TO_KEEP=1

# Use 'find' to locate and delete files older than DAYS_TO_KEEP
# -type f: Only find files (not directories)
# -mtime +${DAYS_TO_KEEP}: Find files modified more than N days ago
# -delete: A safe and efficient way to delete the found files
find "${JOB_STORAGE_DIR}" -type f -mtime +${DAYS_TO_KEEP} -delete

# Log the action
echo "Cleanup of ${JOB_STORAGE_DIR} completed on $(date)" >> /mnt/data/corpus_backend/cleanup.log
