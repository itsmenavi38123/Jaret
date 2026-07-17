# Admin APIs curl Reference

Use these curl templates to test or interact with the newly implemented and updated admin endpoints. All endpoints require a valid admin JWT token in the `Authorization` header.

## 1. "Needs Your Eyes" Dashboard & Feeds

### Get Needs Your Eyes Data
Retrieve the summary stats, failures list, and corrections list.
```bash
curl -X GET "http://localhost:8000/admin/needs-your-eyes" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

---

## 2. Failure Resolutions

### Resolve Memory failure
Resolve a memory write failure that landed in the queue after retry.
```bash
curl -X POST "http://localhost:8000/admin/needs-your-eyes/failures/<FAILURE_ID>/resolve?type=memory" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

### Resolve Document failure
Resolve a failed document extraction.
```bash
curl -X POST "http://localhost:8000/admin/needs-your-eyes/failures/<DOCUMENT_ID>/resolve?type=document" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

---

## 3. Correction Verifications

### Approve Correction / Verify Capture
Approve a low-confidence write or verify an owner correction.
```bash
curl -X POST "http://localhost:8000/admin/needs-your-eyes/corrections/<MEMORY_ID>/approve" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

### Reject / Mark Outdated
Reject a low-confidence write or mark an owner correction outdated.
```bash
curl -X POST "http://localhost:8000/admin/needs-your-eyes/corrections/<MEMORY_ID>/reject" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

---

## 4. Customers Listing with Connection Health Filters (Updated)

### Filter by Broken Connections
List all customers with at least one broken connection.
```bash
curl -X GET "http://localhost:8000/admin/customers?connection=broken&page=1&per_page=10" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

### Filter by Healthy Connections
List all customers where all connected integrations are healthy.
```bash
curl -X GET "http://localhost:8000/admin/customers?connection=healthy&page=1&per_page=10" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```

### Get All Connections (No filter)
List all customers regardless of connection health.
```bash
curl -X GET "http://localhost:8000/admin/customers?connection=connected&page=1&per_page=10" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
     -H "Accept: application/json"
```
