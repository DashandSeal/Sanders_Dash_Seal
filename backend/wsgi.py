"""Owner-selected Python transactional service, composed with existing platform."""
import os
from core_platform.deployment import load_application

application = load_application(None,
    transaction_db=os.environ.get('SQLITE_DB_PATH', '/app/data/sds_production.db'))
