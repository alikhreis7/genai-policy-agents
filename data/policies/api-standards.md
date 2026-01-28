# API Standards & Guidelines

**Version:** 3.0  
**Last Updated:** January 2025  
**Owner:** Platform Engineering

## Overview

This document defines standards for API design, security, and operations across all services.

## API Gateway Requirements

### External APIs

All **external-facing APIs** must route through the API Gateway:

- Rate limiting (default: 1000 req/min per client)
- Authentication verification
- Request/response logging
- DDoS protection
- SSL/TLS termination

### Internal Service Communication

Internal services **may** communicate directly when:

1. **Using Service Mesh** (Istio/Linkerd)
   - Mutual TLS (mTLS) is enforced
   - Service-to-service authentication
   - Traffic encrypted in transit

2. **High-Frequency Data Pipelines**
   - Documented performance requirements
   - Architecture review approval
   - Monitoring in place

3. **Real-Time Streaming**
   - Between approved services only
   - Kafka/Pulsar with authentication

### Never Bypass Gateway

The following **must always** use the API Gateway:

- Any traffic involving PII
- Authentication/authorization flows
- External partner integrations
- Public API endpoints
- Mobile application backends

## API Versioning

All APIs must implement versioning:

### Preferred: URL Path Versioning
```
GET /api/v1/users
GET /api/v2/users
```

### Acceptable: Header Versioning
```
Accept-Version: v1
Accept-Version: v2
```

### Deprecation Policy

1. Announce deprecation **6 months** before removal
2. Provide migration guide and timeline
3. Monitor usage metrics
4. Send direct notification to known consumers
5. Maintain backward compatibility during transition

## Authentication Standards

### User-Context APIs
- OAuth 2.0 with PKCE for web/mobile
- JWT tokens with appropriate claims
- Access token lifetime: 1 hour maximum
- Refresh token lifetime: 30 days maximum

### Service-to-Service
- mTLS preferred
- API keys with rotation (180 days)
- Service accounts with least privilege

## Rate Limiting

| Tier | Requests/Minute | Burst |
|------|----------------|-------|
| Free | 100 | 20 |
| Standard | 1,000 | 100 |
| Premium | 10,000 | 500 |
| Internal | 50,000 | 1,000 |

## Error Handling

All APIs must return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [...],
    "request_id": "abc-123"
  }
}
```

## Documentation Requirements

All APIs must have:
- OpenAPI 3.0 specification
- Authentication examples
- Error code documentation
- Rate limit information
- Changelog
