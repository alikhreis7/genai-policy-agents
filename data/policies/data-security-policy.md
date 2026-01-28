# Data Security Policy

**Version:** 2.1  
**Last Updated:** January 2025  
**Owner:** Security Team

## Overview

This policy defines requirements for handling, storing, and transmitting data across all systems and applications.

## Data Classification

All data must be classified according to sensitivity:

| Classification | Description | Examples |
|---------------|-------------|----------|
| **PUBLIC** | Information that can be freely shared | Marketing materials, public docs |
| **INTERNAL** | Business information for internal use | Internal wikis, meeting notes |
| **CONFIDENTIAL** | Sensitive data requiring access controls | Financial reports, contracts |
| **RESTRICTED** | Highly sensitive data with strict controls | PII, health records, credentials |

## PII Handling Requirements

Personal Identifiable Information (PII) includes any data that can identify an individual:
- Full name, email address, phone number
- Social Security Number, passport number
- Financial account numbers
- Health information
- Biometric data

### Storage Requirements

PII **MUST** be stored according to these requirements:

1. **Approved Data Stores Only**
   - PostgreSQL with encryption enabled
   - MongoDB Enterprise with field-level encryption
   - AWS DynamoDB with encryption at rest
   - Azure CosmosDB with encryption

2. **Encryption at Rest**
   - Minimum AES-256 encryption
   - Keys managed through approved KMS

3. **Access Controls**
   - Role-based access control (RBAC) required
   - All access must be logged and auditable
   - Regular access reviews (quarterly minimum)

### Prohibited Practices

The following are **strictly prohibited** for PII:

- Storage in general-purpose caches (Redis, Memcached)
- Logging PII in application logs
- Storing PII in spreadsheets or shared drives
- Transmitting PII over unencrypted channels
- Storing PII in code repositories

### Caching Exceptions

PII may be cached **only** when ALL conditions are met:
1. Cache is dedicated to PII handling (isolated)
2. Encryption at rest is enabled
3. Access controls are enforced
4. TTL is set appropriately (max 24 hours)
5. Security team approval obtained

## Data Retention

| Data Type | Retention Period | Disposal Method |
|-----------|-----------------|-----------------|
| User PII | Duration of account + 30 days | Secure deletion |
| Transaction logs | 7 years | Archive then delete |
| Session data | 24 hours | Automatic expiration |
| Audit logs | 3 years | Secure archive |

## Incident Response

Data breaches involving PII must be reported within **24 hours** to:
- Security Team: security@company.com
- Legal Team: legal@company.com
- Data Protection Officer

## Compliance

This policy supports compliance with:
- GDPR (General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- SOC 2 Type II
- ISO 27001
