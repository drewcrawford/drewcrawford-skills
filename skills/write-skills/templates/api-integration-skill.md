---
name: api-name-client
description: Interact with [API Name] for [main operations]. Use when working with [service name], [specific operations], or when user mentions [trigger keywords].
allowed-tools: WebFetch, Read, Write, Bash
---

# [API Name] Integration

Professional [API name] client for [primary use case].

## Authentication

### API Key Authentication
```bash
export API_KEY=your_key_here
```

### OAuth 2.0 Authentication
```bash
export CLIENT_ID=your_client_id
export CLIENT_SECRET=your_client_secret
```

## Configuration

### Base Configuration
- Base URL: `https://api.example.com/v1`
- Rate Limit: X requests per minute
- Timeout: 30 seconds
- Retry Policy: 3 attempts with exponential backoff

## Core Operations

### Resource Management
- Create resources
- Read/retrieve resources
- Update resources
- Delete resources
- List/search resources

### Specific Features
- [Feature 1 description]
- [Feature 2 description]
- [Feature 3 description]

## API Endpoints

### [Resource Type 1]
- `GET /resources` - List all resources
- `GET /resources/{id}` - Get specific resource
- `POST /resources` - Create new resource
- `PUT /resources/{id}` - Update resource
- `DELETE /resources/{id}` - Delete resource

### [Resource Type 2]
- `GET /other-resources` - List resources
- `POST /other-resources` - Create resource

## Request Examples

### Create Resource
```bash
curl -X POST https://api.example.com/v1/resources \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example",
    "type": "standard"
  }'
```

### Get Resource
```bash
curl https://api.example.com/v1/resources/123 \
  -H "Authorization: Bearer $API_KEY"
```

## Response Handling

### Success Response
```json
{
  "status": "success",
  "data": {
    "id": "123",
    "name": "Example"
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Description of error"
  }
}
```

## Error Codes

| Code | Description | Action |
|------|-------------|--------|
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Verify API credentials |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify resource exists |
| 429 | Rate Limited | Implement backoff |
| 500 | Server Error | Retry with backoff |

## Best Practices

1. **Rate Limiting**
   - Implement exponential backoff
   - Track request counts
   - Use bulk operations when available

2. **Error Handling**
   - Always check response status
   - Parse error messages
   - Implement retry logic

3. **Security**
   - Never hardcode credentials
   - Use environment variables
   - Rotate keys regularly

## Python Client Example

```python
import requests
import os
from typing import Dict, Any

class APIClient:
    def __init__(self):
        self.base_url = "https://api.example.com/v1"
        self.api_key = os.environ.get("API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def get_resource(self, resource_id: str) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/resources/{resource_id}")
        response.raise_for_status()
        return response.json()

    def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.post(f"{self.base_url}/resources", json=data)
        response.raise_for_status()
        return response.json()
```

## Testing

### Test Environment
- Base URL: `https://sandbox.api.example.com/v1`
- Test Credentials: Available in developer portal
- Rate Limits: Relaxed for testing

### Integration Tests
1. Authentication flow
2. CRUD operations
3. Error handling
4. Rate limit handling
5. Webhook delivery