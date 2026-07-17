---
name: automation-name
description: Automate [task type] including [specific operations]. Use when setting up automation, creating workflows, or when user mentions [trigger keywords].
allowed-tools: Read, Write, Edit, Bash, TodoWrite
---

# [Task] Automation

Intelligent automation for [primary use case].

## Automation Capabilities

### Supported Triggers
- Time-based (cron schedules)
- Event-based (file changes, webhooks)
- Condition-based (thresholds, patterns)
- Manual triggers

### Supported Actions
- [Action category 1]
- [Action category 2]
- [Action category 3]
- [Action category 4]

## Workflow Components

### 1. Trigger Configuration
Define when automation runs:
```yaml
triggers:
  schedule:
    cron: "0 0 * * *"  # Daily at midnight
  file_watch:
    path: "/data/input"
    pattern: "*.csv"
  webhook:
    url: "/webhook/trigger"
    secret: "${WEBHOOK_SECRET}"
```

### 2. Input Processing
Handle various input sources:
- Files and directories
- API responses
- Database queries
- Message queues

### 3. Core Logic
Execute main automation tasks:
```python
def process_automation(trigger_data):
    # Validate input
    validated = validate_input(trigger_data)

    # Execute main logic
    result = execute_workflow(validated)

    # Handle output
    return format_output(result)
```

### 4. Output Handling
Deliver results to destinations:
- File systems
- APIs/webhooks
- Databases
- Notification services

## Implementation Examples

### Example 1: File Processing Automation
```bash
#!/bin/bash
# Automated file processing workflow

# Configuration
INPUT_DIR="/data/input"
OUTPUT_DIR="/data/output"
ARCHIVE_DIR="/data/archive"

# Process new files
for file in "$INPUT_DIR"/*.csv; do
    if [ -f "$file" ]; then
        # Process file
        python process.py "$file" -o "$OUTPUT_DIR"

        # Archive original
        mv "$file" "$ARCHIVE_DIR/$(date +%Y%m%d)_$(basename "$file")"

        # Log completion
        echo "$(date): Processed $(basename "$file")" >> process.log
    fi
done
```

### Example 2: API Sync Automation
```python
import schedule
import time
import requests
from datetime import datetime

class APISyncAutomation:
    def __init__(self):
        self.source_api = "https://source.api.com"
        self.target_api = "https://target.api.com"
        self.last_sync = None

    def sync_data(self):
        """Sync data between APIs"""
        try:
            # Fetch from source
            source_data = self.fetch_source_data()

            # Transform data
            transformed = self.transform_data(source_data)

            # Push to target
            self.push_to_target(transformed)

            self.last_sync = datetime.now()
            print(f"Sync completed at {self.last_sync}")

        except Exception as e:
            self.handle_error(e)

    def run(self):
        """Schedule and run automation"""
        schedule.every(30).minutes.do(self.sync_data)

        while True:
            schedule.run_pending()
            time.sleep(1)
```

## Configuration Management

### Environment Configuration
```env
# Automation settings
AUTOMATION_ENV=production
LOG_LEVEL=INFO
MAX_RETRIES=3
TIMEOUT_SECONDS=300

# External services
API_KEY=your-api-key
DATABASE_URL=postgresql://localhost/db
NOTIFICATION_WEBHOOK=https://hooks.slack.com/xxx
```

### Workflow Configuration
```yaml
workflow:
  name: "Data Processing Pipeline"
  version: "1.0.0"

  steps:
    - name: "Extract"
      type: "file_read"
      config:
        path: "${INPUT_PATH}"
        format: "csv"

    - name: "Transform"
      type: "data_transform"
      config:
        operations:
          - deduplicate
          - normalize
          - validate

    - name: "Load"
      type: "database_write"
      config:
        connection: "${DATABASE_URL}"
        table: "processed_data"
```

## Error Handling and Recovery

### Retry Logic
```python
from retrying import retry

@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000
)
def resilient_operation():
    """Operation with automatic retry"""
    # Your automation logic here
    pass
```

### Error Notifications
```python
def notify_error(error, context):
    """Send error notifications"""
    message = {
        "error": str(error),
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "severity": "high"
    }

    # Send to monitoring service
    send_to_monitoring(message)

    # Send email alert
    send_email_alert(message)

    # Log to file
    log_error(message)
```

## Monitoring and Observability

### Metrics Collection
- Execution time
- Success/failure rate
- Data processed
- Resource usage
- Error frequency

### Health Checks
```python
def health_check():
    """Verify automation system health"""
    checks = {
        "database": check_database_connection(),
        "api": check_api_availability(),
        "disk_space": check_disk_space(),
        "memory": check_memory_usage()
    }

    return all(checks.values())
```

### Logging Strategy
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

## Deployment Options

### Cron Job
```bash
# Add to crontab
0 */6 * * * /usr/bin/python3 /path/to/automation.py
```

### Systemd Service
```ini
[Unit]
Description=Automation Service
After=network.target

[Service]
Type=simple
User=automation
WorkingDirectory=/opt/automation
ExecStart=/usr/bin/python3 automation.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Container Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "automation.py"]
```

## Best Practices

1. **Idempotency**
   - Ensure operations can be safely repeated
   - Check state before modifying
   - Use unique identifiers

2. **Scalability**
   - Design for parallel execution
   - Implement queue-based processing
   - Use connection pooling

3. **Security**
   - Store secrets securely
   - Implement access controls
   - Audit automation actions

4. **Maintainability**
   - Version control configurations
   - Document workflows
   - Implement comprehensive testing