# Security Policy

**Version:** 4.0  
**Last Updated:** January 2025  
**Owner:** Information Security

## Overview

This policy establishes security requirements for all systems, applications, and personnel.

## Authentication Requirements

### Password Policy

| Requirement | Value |
|-------------|-------|
| Minimum length | 12 characters |
| Complexity | Upper, lower, number, special |
| History | Cannot reuse last 12 passwords |
| Max age (standard) | No expiration with MFA |
| Max age (privileged) | 90 days |
| Lockout threshold | 5 failed attempts |
| Lockout duration | 30 minutes |

### Multi-Factor Authentication (MFA)

MFA is **required** for:
- All production system access
- Admin consoles and dashboards
- VPN and remote access
- Access to PII or financial data
- Cloud provider console access
- Source code repositories

Approved MFA methods:
- Hardware security keys (YubiKey) - preferred
- TOTP authenticator apps
- Push notifications (company-approved apps)

**Not approved:**
- SMS-based verification
- Email-based verification

## Secret Management

### Approved Solutions

| Solution | Use Case |
|----------|----------|
| HashiCorp Vault | Primary - all secrets |
| AWS Secrets Manager | AWS-native services |
| Azure Key Vault | Azure-native services |
| GCP Secret Manager | GCP-native services |

### Prohibited Practices

Secrets **must never** be stored in:
- Source code or version control
- Configuration files
- Environment variables (production)
- Container images
- CI/CD pipeline logs
- Slack/Teams messages
- Email

### Rotation Requirements

| Secret Type | Rotation Period |
|-------------|-----------------|
| Database passwords | 90 days |
| API keys | 180 days |
| Service account keys | 365 days |
| TLS certificates | Before expiration |
| SSH keys | 365 days |

## Network Security

### Segmentation

- Production networks isolated from development
- Database tier not directly accessible from internet
- Jump hosts required for production access
- VPN required for remote access

### Encryption in Transit

- TLS 1.2 minimum (TLS 1.3 preferred)
- Strong cipher suites only
- Certificate validation enforced
- HSTS enabled for web applications

## Vulnerability Management

### Scanning Requirements

| Type | Frequency |
|------|-----------|
| SAST (Static Analysis) | Every PR |
| DAST (Dynamic Analysis) | Weekly |
| Dependency scanning | Daily |
| Container scanning | Every build |
| Infrastructure scanning | Weekly |

### Remediation SLAs

| Severity | Remediation Time |
|----------|------------------|
| Critical | 24 hours |
| High | 7 days |
| Medium | 30 days |
| Low | 90 days |

## Incident Response

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| SEV1 | Active breach, data exfiltration | Immediate |
| SEV2 | Vulnerability being exploited | 1 hour |
| SEV3 | High-risk vulnerability discovered | 4 hours |
| SEV4 | Security policy violation | 24 hours |

### Reporting

Report security incidents to:
- Emergency: security-emergency@company.com
- General: security@company.com
- Anonymous: security-hotline (ext. 9999)

## Compliance

This policy supports:
- SOC 2 Type II
- ISO 27001
- PCI DSS (where applicable)
- HIPAA (where applicable)
