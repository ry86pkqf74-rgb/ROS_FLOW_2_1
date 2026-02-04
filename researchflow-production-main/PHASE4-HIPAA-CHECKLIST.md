# PHASE 4: HIPAA COMPLIANCE CHECKLIST
## ResearchFlow - Clinical Research Automation Platform

**Document Version:** 1.0  
**Last Updated:** 2026-01-29  
**Status:** Pre-Deployment  
**Target Deployment:** Production  

---

## TABLE OF CONTENTS

1. [PHI Detection & Classification](#1-phi-detection--classification)
2. [Access Control (RBAC)](#2-access-control-rbac)
3. [Audit Logging](#3-audit-logging)
4. [Data Encryption](#4-data-encryption)
5. [LLM Egress Policy](#5-llm-egress-policy)
6. [Business Associate Agreements](#6-business-associate-agreements)
7. [Incident Response](#7-incident-response)
8. [Training & Documentation](#8-training--documentation)

---

## 1. PHI DETECTION & CLASSIFICATION

### 1.1 Database Schema PHI Field Identification

This section ensures all Protected Health Information (PHI) is properly identified and mapped within database schemas.

#### Patient Demographics
- [ ] Patient ID field marked as PHI
- [ ] Full name field marked as PHI
- [ ] Date of birth field marked as PHI (or age if calculated)
- [ ] Gender/sex field documented (may not be standalone PHI)
- [ ] Address fields marked as PHI (street, city, state, ZIP)
- [ ] Telephone number fields marked as PHI
- [ ] Email address fields marked as PHI (if linked to patient)
- [ ] Emergency contact information marked as PHI
- [ ] Patient account numbers marked as PHI
- [ ] Insurance member IDs marked as PHI
- [ ] Driver's license/state ID numbers marked as PHI
- [ ] Passport numbers marked as PHI

#### Clinical Data
- [ ] Diagnosis codes (ICD-10) documented as PHI
- [ ] Treatment procedures (CPT codes) marked as PHI
- [ ] Medication names and dosages marked as PHI
- [ ] Lab test results and values marked as PHI
- [ ] Radiology/imaging reports marked as PHI
- [ ] Pathology reports marked as PHI
- [ ] Clinical notes and narratives marked as PHI
- [ ] Vital signs (when linked to patient timeline) marked as PHI
- [ ] Allergies and adverse reactions marked as PHI
- [ ] Medical history fields marked as PHI
- [ ] Psychotherapy notes marked as PHI (extra protection)

#### Contact & Provider Information
- [ ] Healthcare provider names marked as PHI
- [ ] Provider phone numbers marked as PHI
- [ ] Provider email addresses marked as PHI
- [ ] Provider locations/facilities marked as PHI
- [ ] Facility names and addresses marked as PHI
- [ ] Provider credentials and license numbers marked as PHI

#### Unique Identifiers
- [ ] Social Security Numbers (SSN) marked as PHI
- [ ] Medical record numbers (MRN) marked as PHI
- [ ] Health plan member IDs marked as PHI
- [ ] Employer identification numbers marked as PHI

### 1.2 Data Classification Policies

#### PHI Classification Levels
- [ ] Level 1 (Highly Sensitive): Direct identifiers (name, SSN, DOB, contact info)
  - [ ] Processing restricted to authorized personnel only
  - [ ] Requires explicit consent
  - [ ] Requires encryption at all times
  - [ ] Audit logging mandatory
  
- [ ] Level 2 (Sensitive): Clinical and protected information (diagnoses, medications, lab results)
  - [ ] Processing requires role-based access
  - [ ] Encryption at rest and in transit required
  - [ ] Audit logging required
  
- [ ] Level 3 (Standard): Non-sensitive research data (age groups, anonymized statistics)
  - [ ] Processing allowed with standard access controls
  - [ ] Encryption recommended
  - [ ] Audit logging recommended

#### Classification Implementation
- [ ] Database schema includes `phi_classification_level` field
- [ ] Data dictionary documents PHI status for every field
- [ ] Configuration file defines PHI field patterns
- [ ] Regular classification audits scheduled (quarterly)
- [ ] Process for reclassifying data established
- [ ] De-identification rules documented for each field type

### 1.3 Sensitive Field Markers

#### Field-Level Tagging
- [ ] All PHI fields have metadata tag: `is_phi=true`
- [ ] All PHI fields have tag: `classification_level=[1|2|3]`
- [ ] All PHI fields have tag: `requires_consent=true/false`
- [ ] All PHI fields have tag: `encryption_required=true`
- [ ] All PHI fields have tag: `audit_log_required=true`
- [ ] All PHI fields have tag: `retention_period=[days]`
- [ ] All PHI fields have tag: `anonymization_capable=true/false`
- [ ] All PHI fields documented in data dictionary with PHI label

#### Database Implementation
- [ ] PHI fields use database views with encryption triggers
- [ ] Triggers prevent direct access to PHI fields without audit
- [ ] Constraints prevent NULL values on required identifiers
- [ ] Indexes on PHI fields use encrypted indexes (if supported)
- [ ] Stored procedures validate PHI access on every query

#### Code-Level Implementation
- [ ] PHI fields defined in ORM models with `@PHI` annotation/decorator
- [ ] ORM models include PHI metadata properties
- [ ] API serializers exclude PHI from unencrypted responses
- [ ] Form validators flag PHI field inputs for special handling
- [ ] Logging filters automatically redact PHI from logs

### 1.4 Input Validation for PHI

#### Pattern Validation
- [ ] SSN format validation (XXX-XX-XXXX)
- [ ] Phone number format validation (XXX-XXX-XXXX)
- [ ] ZIP code format validation (XXXXX or XXXXX-XXXX)
- [ ] Date of birth format validation (YYYY-MM-DD)
- [ ] MRN format validation against institutional standards
- [ ] ICD-10 diagnosis code validation
- [ ] CPT procedure code validation

#### Content Validation
- [ ] Name fields reject special characters (except apostrophes, hyphens)
- [ ] Address fields validate against USPS standards
- [ ] Email fields validate proper format
- [ ] Phone numbers validate against North American Numbering Plan
- [ ] DOB validates against current date (future dates rejected)
- [ ] Gender/sex field restricted to approved values
- [ ] Clinical codes validated against current code sets

#### Security Validation
- [ ] Input length limits enforced on all PHI fields
- [ ] SQL injection prevention via parameterized queries
- [ ] Cross-site scripting (XSS) prevention via output encoding
- [ ] Command injection prevention via input sanitization
- [ ] XXE (XML External Entity) prevention for XML inputs
- [ ] File upload validation for clinical documents

#### Data Quality Validation
- [ ] Duplicate patient check on PHI entry
- [ ] Confidence scores for fuzzy matching on identifiers
- [ ] Validation rules documented in configuration file
- [ ] Validation errors logged without exposing PHI
- [ ] Rejected inputs quarantined for review
- [ ] Validation audit trail maintained

---

## 2. ACCESS CONTROL (RBAC)

### 2.1 Role Definitions

#### System Administrator Role
- [ ] Full system access including configuration
- [ ] PHI access auditable and trackable
- [ ] Cannot modify audit logs or compliance settings
- [ ] Requires multi-factor authentication (MFA)
- [ ] Session timeout: 30 minutes
- [ ] Cannot bypass security controls
- [ ] Title: "System Administrator"
- [ ] Approval authority: IT Director + Compliance Officer

#### Clinical Researcher Role
- [ ] Access to assigned patient cohorts only
- [ ] View clinical data relevant to study protocol
- [ ] Cannot access clinical notes outside study scope
- [ ] Cannot modify patient data without audit trail
- [ ] Requires MFA
- [ ] Session timeout: 60 minutes
- [ ] Title: "Clinical Researcher"
- [ ] Approval authority: Study Principal Investigator + IRB
- [ ] Restrictions:
  - [ ] Cannot access other researchers' cohorts
  - [ ] Cannot download bulk PHI (maximum 100 records per export)
  - [ ] Cannot share patient data directly

#### Data Analyst Role
- [ ] Access to de-identified and aggregated data only
- [ ] Cannot access raw PHI without explicit permission
- [ ] Can perform statistical analysis on approved datasets
- [ ] Cannot identify individual patients
- [ ] Requires MFA
- [ ] Session timeout: 60 minutes
- [ ] Title: "Data Analyst"
- [ ] Approval authority: Study PI + Data Governance Committee
- [ ] Restrictions:
  - [ ] No access to individual identifiers
  - [ ] No access to contact information
  - [ ] No export of granular data

#### Study Coordinator Role
- [ ] Access to patient enrollment and status
- [ ] Can manage appointment scheduling
- [ ] Can view contact information for participant communication
- [ ] Cannot view detailed clinical data
- [ ] Requires MFA
- [ ] Session timeout: 60 minutes
- [ ] Title: "Study Coordinator"
- [ ] Approval authority: Study PI
- [ ] Restrictions:
  - [ ] No access to diagnosis or treatment details
  - [ ] No access to medication lists
  - [ ] No access to lab results

#### Data Quality Reviewer Role
- [ ] Access to specific data quality metrics
- [ ] Can flag inconsistent or incomplete data
- [ ] View limited patient context for validation
- [ ] Cannot modify patient data
- [ ] Requires MFA
- [ ] Session timeout: 60 minutes
- [ ] Title: "Data Quality Reviewer"
- [ ] Approval authority: Study PI + QA Manager

#### Compliance Officer Role
- [ ] Access to audit logs and compliance reports
- [ ] Cannot modify clinical or patient data
- [ ] Can generate compliance reports
- [ ] Can initiate breach investigations
- [ ] Requires MFA
- [ ] Session timeout: 45 minutes
- [ ] Title: "Compliance Officer"
- [ ] Approval authority: Chief Compliance Officer

#### IT Operations Role
- [ ] System and infrastructure management access
- [ ] Encryption key management (shared responsibility)
- [ ] Backup and disaster recovery operations
- [ ] Cannot access PHI (except in emergency recovery scenarios)
- [ ] Requires MFA + Hardware token
- [ ] Session timeout: 30 minutes
- [ ] Title: "IT Operations"
- [ ] Approval authority: IT Director + Security Officer
- [ ] Emergency access restrictions:
  - [ ] Requires incident ticket and supervisor approval
  - [ ] All access automatically logged and audited
  - [ ] Review required within 24 hours

### 2.2 Permission Matrices

#### Clinical Researcher Permissions
- [ ] Read: Patient demographics (for assigned cohort)
- [ ] Read: Clinical diagnoses (for assigned cohort)
- [ ] Read: Treatment history (for assigned cohort)
- [ ] Read: Lab results (for assigned cohort)
- [ ] Read: Medication lists (for assigned cohort)
- [ ] Read: Study-specific notes
- [ ] Read: Appointment history
- [ ] Create: Study data entries
- [ ] Update: Study data entries (own entries only)
- [ ] Delete: Study data entries (own entries, recent only)
- [ ] Export: De-identified dataset exports
- [ ] Cannot: Access other cohorts
- [ ] Cannot: Modify patient master data
- [ ] Cannot: Delete data (audit trail maintained)

#### Data Analyst Permissions
- [ ] Read: De-identified datasets
- [ ] Read: Aggregated statistics
- [ ] Read: Data quality metrics
- [ ] Read: Cohort summaries
- [ ] Create: Analysis scripts
- [ ] Create: Reports and visualizations
- [ ] Cannot: Access individual patient identifiers
- [ ] Cannot: Access contact information
- [ ] Cannot: Reverse de-identification
- [ ] Cannot: Export granular data

#### Study Coordinator Permissions
- [ ] Read: Patient names and contact info (assigned cohort)
- [ ] Read: Appointment scheduling data
- [ ] Read: Enrollment status
- [ ] Create: Appointment entries
- [ ] Update: Appointment entries
- [ ] Update: Contact information (with consent)
- [ ] Create: Communication logs
- [ ] Cannot: View clinical data
- [ ] Cannot: Modify clinical data
- [ ] Cannot: Access sensitive diagnoses

#### Data Quality Reviewer Permissions
- [ ] Read: Data validation reports
- [ ] Read: Completeness metrics
- [ ] Read: Consistency checks
- [ ] View: Limited patient context (for validation only)
- [ ] Create: Data quality flags
- [ ] Update: Flag status and notes
- [ ] Cannot: Modify patient data
- [ ] Cannot: Access full clinical record
- [ ] Cannot: Export data

#### Compliance Officer Permissions
- [ ] Read: Audit logs (all)
- [ ] Read: Compliance reports
- [ ] Read: Access logs
- [ ] Read: User activity summaries (anonymized)
- [ ] Create: Incident reports
- [ ] Create: Compliance documentation
- [ ] Export: Audit logs
- [ ] Cannot: Modify clinical data
- [ ] Cannot: Access PHI (except in audit context)
- [ ] Cannot: Modify audit logs

#### IT Operations Permissions
- [ ] Manage: System configurations
- [ ] Manage: Database backups
- [ ] Manage: Infrastructure components
- [ ] View: System performance logs
- [ ] Rotate: Encryption keys
- [ ] Cannot: Access PHI (except emergency)
- [ ] Cannot: Modify audit logs
- [ ] Cannot: Bypass access controls

### 2.3 Authentication Requirements

#### Password Policy
- [ ] Minimum length: 12 characters
- [ ] Require mix of: uppercase, lowercase, numbers, special characters
- [ ] No dictionary words allowed
- [ ] No reuse of last 8 passwords
- [ ] Password expiration: 90 days
- [ ] Grace period for expiration: 14 days
- [ ] Lockout after 5 failed attempts
- [ ] Lockout duration: 30 minutes
- [ ] Password reset requires email verification
- [ ] Cannot change password more than once per day

#### Multi-Factor Authentication (MFA)
- [ ] MFA required for all user accounts
- [ ] Supported methods:
  - [ ] Time-based One-Time Password (TOTP) via authenticator app
  - [ ] Hardware security keys (FIDO2/U2F)
  - [ ] SMS-based OTP (for user convenience, lower security tier)
- [ ] MFA enforcement: Immediate (no grace period)
- [ ] Backup codes issued (10 codes, one-time use)
- [ ] Backup codes stored securely (encrypted, separate from password)
- [ ] Backup code regeneration tracked and logged
- [ ] MFA recovery procedure requires identity verification
- [ ] Support contact required for MFA lockout recovery

#### Session Management
- [ ] Session timeout: Role-based (30-60 minutes)
- [ ] Idle timeout: 30 minutes of inactivity
- [ ] Hard stop: 12 hours maximum session duration
- [ ] Session termination on logout: Immediate
- [ ] Session termination on password change: Immediate
- [ ] Session termination on MFA reset: Immediate
- [ ] Session tokens: Cryptographically secure, 256-bit minimum
- [ ] Session tokens: Regenerated on privilege escalation
- [ ] Session tokens: Stored as httpOnly, secure cookies
- [ ] Session tokens: Include CSRF protection
- [ ] Concurrent sessions: Limited to 2 per user
- [ ] Session activity tracked and logged
- [ ] Session anomalies detected (unusual IP, location, time)

#### Credential Management
- [ ] Credentials never logged in system logs
- [ ] Credentials never transmitted in URLs
- [ ] Credentials never transmitted in plain text
- [ ] API keys issued for service-to-service authentication
- [ ] API keys rotated every 90 days
- [ ] API keys scoped to minimum required permissions
- [ ] API keys stored in secure vault (not in code)
- [ ] Service account credentials managed separately
- [ ] Shared credentials prohibited
- [ ] Credential audit trail maintained

#### Authentication Failure Handling
- [ ] Failed authentication attempts logged
- [ ] Failed login count tracked per user
- [ ] Temporary account lockout after failures
- [ ] Account lockout notifications sent
- [ ] Unlock procedure requires helpdesk verification
- [ ] Repeated failures trigger security investigation
- [ ] Brute force attacks detected and mitigated
- [ ] Rate limiting implemented on login endpoint
- [ ] CAPTCHA triggered after threshold of failures

### 2.4 Session Management

#### Session Tracking
- [ ] Session ID generated on login (cryptographically random)
- [ ] Session ID stored securely on server (hashed)
- [ ] Session ID transmitted only over HTTPS
- [ ] Session ID stored in httpOnly, secure cookie
- [ ] Session metadata recorded:
  - [ ] User ID
  - [ ] Login timestamp
  - [ ] Last activity timestamp
  - [ ] User agent (browser/OS)
  - [ ] IP address
  - [ ] MFA method used
  - [ ] Session status (active/inactive/terminated)

#### Session Validation
- [ ] Session validity checked on every request
- [ ] Session expiration enforced server-side
- [ ] Idle timeout enforced automatically
- [ ] Session resurrection prevented after timeout
- [ ] Cross-site request forgery (CSRF) tokens validated
- [ ] IP address consistency checked (alert on change)
- [ ] User agent consistency checked (alert on change)

#### Session Termination
- [ ] Logout terminates session immediately
- [ ] Password change terminates all active sessions
- [ ] MFA modification terminates all active sessions
- [ ] Account deactivation terminates all sessions
- [ ] Role change may trigger session re-authentication
- [ ] Explicit session termination available to admins
- [ ] Session termination logged with reason

#### Session Recovery
- [ ] Session recovery not allowed after expiration
- [ ] "Remember me" functionality disabled (for PHI access)
- [ ] Automatic re-login prevented
- [ ] Saved credentials deleted on session timeout
- [ ] Browser cache cleared on session termination

---

## 3. AUDIT LOGGING

### 3.1 PHI Access Logging Requirements

#### What Must Be Logged
- [ ] Every SELECT query accessing PHI fields
- [ ] Every INSERT of PHI data
- [ ] Every UPDATE of PHI data
- [ ] Every DELETE of PHI data
- [ ] Every view of patient records (web UI access)
- [ ] Every download of PHI data
- [ ] Every export containing PHI
- [ ] Every share/send of PHI
- [ ] Every access to audit logs themselves
- [ ] Every encryption key operation
- [ ] Every backup operation involving PHI
- [ ] Every restore operation involving PHI

#### Logged Information
For each PHI access event, log:
- [ ] User ID (who accessed)
- [ ] User role/department (context for access)
- [ ] Timestamp with millisecond precision (when accessed)
- [ ] Timezone of timestamp
- [ ] IP address of access source
- [ ] Source application/system (if known)
- [ ] Patient ID being accessed (PHI data identifier)
- [ ] Action type (READ, CREATE, UPDATE, DELETE, EXPORT, SHARE)
- [ ] Specific fields accessed (which PHI fields)
- [ ] Amount of data accessed (rows, records, bytes)
- [ ] Query/command executed (sanitized, no values)
- [ ] Outcome (success, denied, error)
- [ ] Reason for access (study ID, task, etc., if available)
- [ ] Session ID
- [ ] Authentication method used
- [ ] System hostname
- [ ] Database connection user (if different from app user)

#### PHI Value Handling
- [ ] PHI values are NEVER logged
- [ ] Patient IDs are logged (needed for audit)
- [ ] Actual names, SSNs, addresses are NOT logged
- [ ] Clinical values are logged only as summaries
- [ ] Redaction rules applied to prevent PHI leakage
- [ ] Separate audit trail for what data was accessed (not the values)

### 3.2 User Action Tracking

#### Login/Logout Activities
- [ ] Successful login logged with timestamp
- [ ] Failed login attempts logged (without password)
- [ ] Logout logged with session duration
- [ ] Session timeout logged
- [ ] Concurrent session limit enforcement logged
- [ ] MFA success/failure logged

#### Role and Permission Changes
- [ ] Role assignment changes logged
- [ ] Permission modifications logged
- [ ] Temporary privilege escalation logged
- [ ] Access approval/denial logged
- [ ] Delegation of authority logged

#### Data Modifications
- [ ] Create operations with:
  - [ ] User ID
  - [ ] Timestamp
  - [ ] Record ID created
  - [ ] Data type (study data, note, etc.)
- [ ] Update operations with:
  - [ ] User ID
  - [ ] Timestamp
  - [ ] Record ID modified
  - [ ] Field names changed (not values)
- [ ] Delete operations with:
  - [ ] User ID
  - [ ] Timestamp
  - [ ] Record ID deleted
  - [ ] Reason for deletion (if captured)
  - [ ] Soft delete flag (not permanent)

#### Data Export Activities
- [ ] Export request logged
- [ ] Export reason/justification captured
- [ ] Data fields included in export
- [ ] Number of records exported
- [ ] Export destination (email, download, etc.)
- [ ] Export encryption confirmed
- [ ] Recipient information (if applicable)
- [ ] Export completion time

#### Research Data Access
- [ ] Cohort access by researcher logged
- [ ] Study protocol access logged
- [ ] Protocol version accessed logged
- [ ] Consent status verification logged
- [ ] Eligibility criteria review logged
- [ ] Data analysis activities logged
- [ ] Statistical report generation logged

### 3.3 Timestamp Requirements

#### Timestamp Accuracy
- [ ] All timestamps use coordinated universal time (UTC)
- [ ] System clock synchronized via NTP
- [ ] Clock sync accuracy: ±1 second
- [ ] Local time zone stored separately if needed
- [ ] Millisecond precision for all audit events
- [ ] No time skew allowed (clock tampering detection)

#### Timestamp Integrity
- [ ] Timestamps cryptographically bound to log entries
- [ ] No ability to modify timestamps post-creation
- [ ] Timestamp verification before log acceptance
- [ ] Retroactive timestamp correction prohibited
- [ ] Time gaps in logs identified and investigated

### 3.4 Log Retention Policies

#### Retention Duration
- [ ] PHI access logs: Retain 6 years
- [ ] Authentication logs: Retain 3 years
- [ ] User activity logs: Retain 3 years
- [ ] System error logs: Retain 1 year
- [ ] Configuration change logs: Retain 5 years
- [ ] Backup/restore logs: Retain 6 years
- [ ] Encryption key operation logs: Retain 6 years
- [ ] Incident investigation logs: Retain indefinitely (or per policy)
- [ ] Compliance audit logs: Retain 6 years

#### Retention Implementation
- [ ] Log rotation configured per retention policy
- [ ] Archived logs transferred to cold storage
- [ ] Retention periods enforced by system (not manual)
- [ ] No manual deletion of logs without approval
- [ ] Deletion approval requires 2 authorized individuals
- [ ] Log deletion events themselves logged
- [ ] Verification that logs deleted as scheduled
- [ ] Storage sufficient for retention period
- [ ] Cost analysis for long-term retention

#### Compliance with Legal Holds
- [ ] Retention extended for legal hold events
- [ ] Hold notices documented
- [ ] Affected logs marked as "held"
- [ ] Legal department notified when hold ends
- [ ] Forensic preservation procedures documented

### 3.5 Log Encryption

#### Encryption at Rest
- [ ] All audit logs encrypted at rest
- [ ] Encryption algorithm: AES-256 minimum
- [ ] Encryption keys managed separately from logs
- [ ] Encryption key rotation: 90 days
- [ ] Decryption requires authentication
- [ ] Decryption logged (access to logs itself is audited)

#### Encryption in Transit
- [ ] Log transmission via TLS 1.2+
- [ ] Log transmission to siem uses encrypted channel
- [ ] Log transmission to archive uses encrypted channel
- [ ] Certificate pinning for external log transmission
- [ ] No intermediate plaintext storage during transmission

#### Key Management for Logs
- [ ] Encryption keys stored in HSM (Hardware Security Module)
- [ ] Key access audit trail maintained
- [ ] Key rotation scheduled (90 days)
- [ ] Key rotation audit logged
- [ ] Old keys retained for decryption of archived logs
- [ ] Key backup procedures documented
- [ ] Key recovery procedures documented

#### Log Access Controls
- [ ] Audit log reading restricted to authorized personnel
- [ ] Compliance Officer, IT Security, IT Director can access
- [ ] Role-based access to log categories
- [ ] Sensitive logs (encryption key ops) require approval
- [ ] Log decryption access logged
- [ ] Bulk log export restricted
- [ ] Log queries audited
- [ ] Data exfiltration detection on log access

#### Log Integrity Verification
- [ ] HMAC or digital signature on log entries
- [ ] Hash chain to detect tampering
- [ ] Periodic integrity checks (daily)
- [ ] Integrity verification before log usage in audits
- [ ] Failed integrity checks trigger alert
- [ ] Integrity failures investigated immediately

---

## 4. DATA ENCRYPTION

### 4.1 Encryption at Rest (Database)

#### Encryption Implementation
- [ ] Database encryption enabled (TDE - Transparent Data Encryption)
- [ ] All PHI tables encrypted
- [ ] All PHI indexes encrypted
- [ ] Encryption algorithm: AES-256
- [ ] Encryption applied to backups
- [ ] Encryption applied to snapshots
- [ ] Encryption applied to log files
- [ ] Encryption applied to temporary files

#### Column-Level Encryption (for highest sensitivity)
- [ ] Direct identifiers encrypted at column level:
  - [ ] Patient names
  - [ ] Social Security Numbers
  - [ ] Medical record numbers
  - [ ] Contact information
- [ ] Column encryption applied regardless of TDE
- [ ] Encryption keys stored separately in HSM
- [ ] Decryption performed only when needed
- [ ] Encrypted values searchable via hashing (deterministic encryption for lookups)

#### Encryption Key Management
- [ ] Primary encryption key stored in HSM
- [ ] HSM access requires MFA
- [ ] Key access audit trail maintained
- [ ] Backup encryption keys stored separately
- [ ] Key rotation schedule: 90 days for primary key
- [ ] Key rotation: All data re-encrypted with new key
- [ ] Key rotation audit trail
- [ ] Key rotation does not cause downtime
- [ ] Old keys retained for archive decryption

#### Database Configuration
- [ ] Encryption enabled in database configuration
- [ ] Encryption enforced (cannot be disabled without audit)
- [ ] Encryption settings version controlled
- [ ] Encryption settings changes require approval
- [ ] Encryption status monitored continuously
- [ ] Encryption failures trigger alerts
- [ ] Database performance impact of encryption documented

### 4.2 Encryption in Transit (TLS/SSL)

#### TLS Configuration
- [ ] TLS 1.2 minimum (TLS 1.3 preferred)
- [ ] TLS 1.0 and 1.1 disabled
- [ ] SSL deprecated completely
- [ ] Strong cipher suites configured
- [ ] Weak ciphers disabled (DES, RC4, etc.)
- [ ] Perfect Forward Secrecy (PFS) enabled
- [ ] Cipher suite configuration:
  - [ ] AES-GCM preferred
  - [ ] ChaCha20-Poly1305 supported
  - [ ] ECDHE for key exchange
  - [ ] ECDSA or RSA-PSS for signatures

#### Certificate Management
- [ ] Valid SSL/TLS certificates installed
- [ ] Certificates issued by trusted CA
- [ ] Certificate Common Name (CN) matches domain
- [ ] Subject Alternative Name (SAN) includes all domains
- [ ] Certificate validity period: 1 year maximum
- [ ] Certificate renewal scheduled 30 days before expiration
- [ ] Certificate renewal tracked and monitored
- [ ] Expired certificates detected and alerted
- [ ] Private keys stored securely (not in codebase)
- [ ] Private key access restricted to authorized personnel
- [ ] Private key rotation on compromise
- [ ] Certificate revocation procedures documented

#### HTTPS Enforcement
- [ ] HTTPS required for all connections
- [ ] HTTP redirects to HTTPS
- [ ] Redirect uses 301 status code
- [ ] HSTS header enabled
- [ ] HSTS preload list inclusion requested
- [ ] HSTS max-age: 31536000 (1 year)
- [ ] HSTS includeSubdomains enabled
- [ ] No mixed content (HTTP resources on HTTPS pages)

#### API Encryption
- [ ] All API endpoints require HTTPS
- [ ] API keys transmitted in HTTPS only
- [ ] OAuth tokens transmitted in HTTPS only
- [ ] No credentials in URLs
- [ ] No credentials in query strings
- [ ] Credentials transmitted in request headers only
- [ ] Authorization header format: "Bearer [token]"
- [ ] API rate limiting to prevent abuse

#### Database Connection Encryption
- [ ] Database connections encrypted with TLS
- [ ] Database connection string includes SSL requirement
- [ ] Certificate verification enabled for database connections
- [ ] Database connection pool enforces encryption
- [ ] Connection timeouts configured
- [ ] Connection retry logic with backoff
- [ ] Failed connections logged

#### File Transfer Encryption
- [ ] SFTP for file transfers (not FTP)
- [ ] SCP for secure copying
- [ ] Secure file upload/download mechanisms
- [ ] File upload endpoint requires HTTPS
- [ ] File download includes Content-Security-Policy headers
- [ ] File download requires authentication
- [ ] Temporary file storage encrypted

### 4.3 Key Management

#### Key Storage
- [ ] Encryption keys stored in Hardware Security Module (HSM)
- [ ] HSM access requires MFA
- [ ] No encryption keys stored in application code
- [ ] No encryption keys in configuration files
- [ ] No encryption keys in environment variables
- [ ] No encryption keys in version control
- [ ] No encryption keys in logs
- [ ] Master key stored separately from derived keys

#### Key Access Control
- [ ] Key access restricted by role:
  - [ ] System Administrators: All keys
  - [ ] Database Administrators: Database keys only
  - [ ] Backup/Recovery: Backup encryption keys only
  - [ ] IT Operations: Key rotation only
- [ ] Key access requires approval
- [ ] Key access audit logged
- [ ] MFA required for key operations
- [ ] Key operations logged with timestamp
- [ ] Suspicious key access patterns detected

#### Key Rotation
- [ ] Primary key rotation every 90 days
- [ ] Manual rotation available on-demand
- [ ] Automatic rotation on key compromise
- [ ] Key rotation preserves data accessibility
- [ ] Key rotation does not cause application downtime
- [ ] Old keys retained for archive access
- [ ] Key rotation audit trail maintained
- [ ] Key rotation tested in non-production first
- [ ] Key rotation completion verified

#### Key Compromise Response
- [ ] Procedure documented and regularly tested
- [ ] Key compromise detected within 24 hours
- [ ] All systems using compromised key identified
- [ ] New key generated immediately
- [ ] All encrypted data re-encrypted with new key
- [ ] Incident classified and reported
- [ ] Forensic investigation performed
- [ ] Stakeholders notified if required

#### Key Backup and Recovery
- [ ] Key backup created and tested
- [ ] Backup keys stored in separate HSM
- [ ] Backup keys require multi-party authorization (M-of-N)
- [ ] Key recovery tested quarterly
- [ ] Key recovery does not expose plaintext keys
- [ ] Recovery procedure in disaster recovery plan
- [ ] Backup key storage location documented
- [ ] Backup key destruction procedure documented

### 4.4 Backup Encryption

#### Backup Encryption Configuration
- [ ] All database backups encrypted
- [ ] Encryption algorithm: AES-256 minimum
- [ ] Backup encryption keys separate from data keys
- [ ] Backup encryption happens before transmission
- [ ] Backup encryption happens before storage
- [ ] Encrypted backup validation performed
- [ ] Backup decryption tested regularly

#### Backup Key Management
- [ ] Backup encryption keys managed separately
- [ ] Backup keys rotated per rotation schedule
- [ ] Backup keys in HSM or secure vault
- [ ] Backup key access audit logged
- [ ] Recovery of backed-up data tested with backup keys
- [ ] Old backup keys retained for archive recovery
- [ ] Backup key destruction procedures documented

#### Backup Storage Security
- [ ] Backups stored on encrypted storage
- [ ] Double encryption: backup encryption + storage encryption
- [ ] Backup transmission encrypted
- [ ] Backup storage access controlled (role-based)
- [ ] Backup storage location hardened
- [ ] Backup storage monitored for unauthorized access
- [ ] Off-site backup copies encrypted
- [ ] Off-site backup transfer uses secure channel

#### Backup Retention and Destruction
- [ ] Backup retention policies documented
- [ ] Backups retained as long as data
- [ ] Backup destruction requires authorization
- [ ] Backup destruction verified (not just deletion)
- [ ] Secure destruction procedure documented
- [ ] Crypto-shredding (key destruction) documented
- [ ] Destruction audit logged

---

## 5. LLM EGRESS POLICY

### 5.1 PHI Must Never Be Sent to External AI Services

#### Prohibited External Services
These services cannot receive any PHI under any circumstances:

- [ ] OpenAI (ChatGPT, GPT-4, API)
- [ ] Anthropic Cloud (Claude API, claude.ai)
- [ ] Google Cloud AI (Vertex AI, Bard, PaLM)
- [ ] Microsoft Azure OpenAI Service
- [ ] Any cloud-based LLM service
- [ ] Any third-party LLM API
- [ ] Web-based AI tools
- [ ] Research-grade API access to LLMs
- [ ] Any SaaS AI platform

#### Enforcement Mechanisms
- [ ] Network firewall rules block external LLM APIs
- [ ] API gateway filters requests to external services
- [ ] Application code explicitly prevents API calls to external services
- [ ] Data loss prevention (DLP) system monitors for LLM API calls
- [ ] Outbound HTTPS to LLM providers blocked at firewall
- [ ] DNS filtering blocks LLM provider domains
- [ ] Proxy/VPN rules prevent bypass
- [ ] SSL inspection logs LLM provider connections
- [ ] Regular audit of outbound network connections

#### Incident Response
- [ ] Any successful PHI transmission to external service triggers incident
- [ ] Breach notification within 72 hours (per HIPAA)
- [ ] Affected individuals notified
- [ ] Department of Health & Human Services (HHS) notified if >500 individuals
- [ ] Investigation into root cause
- [ ] Corrective action plan developed
- [ ] System hardening to prevent recurrence

### 5.2 Local LLM Processing Requirements

#### Local LLM Deployment - LM Studio
- [ ] LM Studio deployed locally on secured server
- [ ] LM Studio not accessible from internet
- [ ] LM Studio access restricted to local network only
- [ ] LM Studio API available only on localhost (127.0.0.1)
- [ ] LM Studio API access requires authentication
- [ ] LM Studio API access via TLS/HTTPS
- [ ] LM Studio API calls logged locally
- [ ] LM Studio server hardened per security standards
- [ ] LM Studio updates tested before deployment
- [ ] LM Studio resource limits configured (memory, CPU)
- [ ] LM Studio performance monitored
- [ ] LM Studio crashes handled gracefully

#### LM Studio Model Selection
- [ ] Models selected are open-source
- [ ] Models selected meet clinical accuracy requirements
- [ ] Models can run on local hardware
- [ ] Model licenses reviewed for healthcare compliance
- [ ] Model outputs validated for safety
- [ ] Model known limitations documented
- [ ] Models tested before clinical use
- [ ] Model selection documented in technical specification

#### LM Studio Request/Response Handling
- [ ] Requests to LM Studio sanitized before sending
- [ ] Requests contain no direct patient identifiers
- [ ] Requests contain no direct clinical narratives with PHI
- [ ] Responses from LM Studio logged locally
- [ ] Responses stored encrypted
- [ ] Responses do not expose raw LLM output to users
- [ ] Responses cached securely (with encryption)
- [ ] Cache invalidation on data updates

### 5.3 Data Sanitization Before AI Processing

#### Pre-Processing Sanitization
- [ ] All PHI identified before LLM processing
- [ ] Patient names replaced with study IDs
- [ ] Dates shifted or aggregated to age groups
- [ ] Contact information removed completely
- [ ] Specific facility names removed
- [ ] Provider names removed
- [ ] Social security numbers removed
- [ ] Insurance information removed
- [ ] Medical record numbers replaced with study IDs
- [ ] Exact diagnosis codes generalized (to category level)
- [ ] Medication names generalized (to drug class)
- [ ] Dosages removed (kept as "prescribed")

#### Sanitization Verification
- [ ] Sanitization rules documented
- [ ] Sanitization rules tested on test data
- [ ] Sanitization rules applied consistently
- [ ] Verification that no PHI in LLM input
- [ ] Regex patterns identify remaining identifiers
- [ ] Manual review of sample sanitized inputs
- [ ] Sanitization audit trail maintained
- [ ] Failed sanitization triggers alert

#### Sanitization Configuration
- [ ] Sanitization rules version controlled
- [ ] Sanitization rules can be updated without code change
- [ ] Sanitization rules tested before deployment
- [ ] Sanitization rules rollback capability
- [ ] Different rules for different LLM tasks
- [ ] Rules documented in technical specification

#### Re-Identification Prevention
- [ ] Sanitized data cannot be re-identified
- [ ] Mapping table between original and sanitized data encrypted
- [ ] Mapping table access restricted to audit/legal needs
- [ ] No reverse engineering of sanitized data
- [ ] Combination of attributes cannot identify individuals
- [ ] Age groups wide enough to prevent identification
- [ ] Multiple individuals per anonymized identifier
- [ ] Quasi-identifiers removed (zip code, gender, age combination)

### 5.4 Audit Trail for AI Interactions

#### What to Log
- [ ] Every call to local LLM
- [ ] User ID requesting LLM processing
- [ ] Timestamp of request
- [ ] Patient/record ID being processed (anonymized ID only)
- [ ] Type of LLM task (summarization, extraction, analysis)
- [ ] Input data (sanitized - no PHI values)
- [ ] Output from LLM (sanitized)
- [ ] LLM model used and version
- [ ] Processing time
- [ ] Any errors or exceptions
- [ ] Storage location of results
- [ ] Subsequent use of LLM output

#### Audit Log Storage
- [ ] LLM audit logs stored separately from system logs
- [ ] LLM logs encrypted at rest
- [ ] LLM logs encrypted in transit
- [ ] LLM logs not transmitted off-site
- [ ] LLM logs retained for 6 years
- [ ] LLM log access restricted to Compliance, IT Security

#### Audit Log Integrity
- [ ] LLM audit logs cryptographically signed
- [ ] Tampering detection enabled
- [ ] Hash chain to detect modifications
- [ ] Integrity verification before usage
- [ ] Failed integrity checks trigger alert
- [ ] Regular spot-checks of LLM logs

#### Prohibited LLM Practices
- [ ] No training of external models on ResearchFlow data
- [ ] No fine-tuning of LLMs using patient data
- [ ] No use of LLM output as ground truth without verification
- [ ] No automatic actions based solely on LLM output
- [ ] LLM output always reviewed by human
- [ ] Clinical decisions not delegated to LLM

#### LLM Performance Monitoring
- [ ] Accuracy metrics tracked
- [ ] Bias detection in LLM outputs
- [ ] Drift detection in LLM performance over time
- [ ] Failure modes documented
- [ ] Known limitations communicated to users
- [ ] Retraining/updating of models monitored

---

## 6. BUSINESS ASSOCIATE AGREEMENTS

### 6.1 Third-Party Service Checklist

#### Cloud Infrastructure Providers
- [ ] Cloud provider BAA in place
- [ ] Scope of services covered by BAA
- [ ] Subcontractor disclosures received
- [ ] Data location and residency requirements
- [ ] Encryption requirements specified
- [ ] Access control requirements specified
- [ ] Audit logging requirements specified
- [ ] Incident response procedures agreed
- [ ] Data breach notification timeline (24 hours minimum)
- [ ] Termination data handling procedures
- [ ] Provider certifications (SOC 2, ISO 27001, etc.)

#### Database Service Providers
- [ ] Database vendor BAA in place
- [ ] Managed database encryption included
- [ ] Automated backup encryption included
- [ ] Access control enforcement
- [ ] Audit logging included
- [ ] Monitoring and alerting included
- [ ] Disaster recovery capabilities documented
- [ ] Data retention policies aligned
- [ ] Breach notification procedures

#### Email and Communication
- [ ] Email provider BAA in place
- [ ] Email encryption at rest
- [ ] Email encryption in transit
- [ ] Secure email configuration (TLS enforcement)
- [ ] Access controls on shared mailboxes
- [ ] Retention policies configured
- [ ] Data loss prevention (DLP) rules
- [ ] Incident notification procedures

#### Identity and Access Management (IAM)
- [ ] IAM vendor BAA in place
- [ ] MFA provider agreement
- [ ] Single Sign-On (SSO) configuration
- [ ] User provisioning/deprovisioning procedures
- [ ] API access controls
- [ ] Audit logging of access events
- [ ] Incident response procedures
- [ ] Data residency requirements

#### Backup and Disaster Recovery
- [ ] Backup provider BAA in place
- [ ] Backup encryption standards
- [ ] Backup test/restore procedures documented
- [ ] Retention policies aligned with HIPAA
- [ ] Off-site backup location specified
- [ ] Disaster recovery procedures tested
- [ ] RTO (Recovery Time Objective) defined
- [ ] RPO (Recovery Point Objective) defined
- [ ] Backup restoration audit logged

#### Monitoring and Logging
- [ ] SIEM/Monitoring vendor BAA in place
- [ ] Log collection and retention
- [ ] Log encryption at rest
- [ ] Log encryption in transit
- [ ] Search and analysis capabilities
- [ ] Alerting configuration
- [ ] Forensic analysis capabilities
- [ ] Integration with security tools

#### Security Assessment Vendors
- [ ] Vulnerability scanning vendor BAA
- [ ] Penetration testing agreement in place
- [ ] Scope of testing defined
- [ ] Findings handling procedure
- [ ] Findings storage and retention
- [ ] Non-disclosure agreement signed
- [ ] Incident handling during testing
- [ ] Remediation tracking

#### Compliance and Legal Services
- [ ] Legal counsel agreement (privilege maintained)
- [ ] Compliance consulting agreement
- [ ] Regular compliance reviews scheduled
- [ ] Risk assessments conducted
- [ ] Policy development assistance
- [ ] Training and awareness programs
- [ ] Incident response support available

### 6.2 BAA Requirements

#### Mandatory BAA Components
- [ ] Clear definition of permitted uses and disclosures
- [ ] Permitted uses limited to specific research purposes
- [ ] Subcontracting restrictions specified
- [ ] Term and termination provisions
- [ ] Required security safeguards listed:
  - [ ] Administrative safeguards
  - [ ] Physical safeguards
  - [ ] Technical safeguards
- [ ] Breach notification requirements:
  - [ ] Notice within 24 hours of discovery
  - [ ] Contents of breach notification
  - [ ] Method of notification
  - [ ] Cost responsibility for notification
- [ ] Access management requirements
- [ ] Encryption requirements
- [ ] Audit control requirements
- [ ] Data integrity requirements
- [ ] Transmission security requirements

#### Use and Disclosure Limitations
- [ ] Uses limited to specified research only
- [ ] Disclosures limited to minimum necessary
- [ ] Receiving party identified in BAA
- [ ] No secondary use without authorization
- [ ] No marketing/selling of data
- [ ] No de-identification allowed without approval
- [ ] No data linkage with other data sources
- [ ] No use in treatment, payment, operations (TPO) context
- [ ] Return or destruction of data on termination

#### Subcontractor Management
- [ ] All subcontractors identified in BAA
- [ ] Subcontractors bound by equivalent terms
- [ ] Subcontractor BAAs required
- [ ] Subcontractor compliance monitoring
- [ ] Right to audit subcontractors
- [ ] Subcontractor breach notification
- [ ] Prohibited subcontractors:
  - [ ] Unsecured internet connectivity providers
  - [ ] Non-US based providers (unless approved)
  - [ ] Providers without SOC 2 Type II (for PHI processing)

#### Security Standards Specification
- [ ] Administrative Safeguards:
  - [ ] Security management process
  - [ ] Workforce security procedures
  - [ ] Information access management
  - [ ] Security awareness training (annual)
  - [ ] Security incident procedures
  - [ ] Sanction policy for violations
  - [ ] Workforce authentication procedures
- [ ] Physical Safeguards:
  - [ ] Facility access controls
  - [ ] Workstation security
  - [ ] Workstation use policies
  - [ ] Device/media controls
- [ ] Technical Safeguards:
  - [ ] Access controls
  - [ ] Audit controls
  - [ ] Integrity controls
  - [ ] Transmission security

#### Termination and Data Handling
- [ ] Termination procedures specified
- [ ] Notice period: 30 days minimum
- [ ] Data return within 30 days of termination
- [ ] Data destruction alternative
- [ ] Destruction certification required
- [ ] Survival clauses for:
  - [ ] Confidentiality obligations (2 years post-termination)
  - [ ] Breach notification (perpetual)
  - [ ] Audit rights (2 years post-termination)
- [ ] Transition support period
- [ ] Emergency access procedures
- [ ] Liabilities and indemnification

### 6.3 Vendor Compliance Verification

#### Initial Vendor Evaluation
- [ ] Vendor security documentation reviewed
- [ ] Vendor certifications verified:
  - [ ] SOC 2 Type II (preferred)
  - [ ] ISO 27001
  - [ ] HITRUST CSF
  - [ ] FedRAMP (for cloud)
- [ ] Vendor references checked
- [ ] Security audit report reviewed
- [ ] Compliance statement obtained
- [ ] Risk assessment performed
- [ ] Approval by IT Security and Compliance

#### Ongoing Vendor Compliance
- [ ] Annual compliance audit conducted
- [ ] Vendor self-assessments reviewed
- [ ] Compliance metrics tracked
- [ ] Incident reports reviewed
- [ ] Security updates monitored
- [ ] Compliance violations tracked and resolved
- [ ] Regular vendor reviews (annual)
- [ ] Compliance report generated

#### Vendor Risk Management
- [ ] Risk score assigned to each vendor
- [ ] High-risk vendors subject to more oversight
- [ ] Vendor criticality assessment (critical/important/standard)
- [ ] Contingency plans for critical vendors
- [ ] Alternative vendor options identified
- [ ] Vendor transition procedures documented
- [ ] Disaster recovery scenarios tested

#### Audit Rights
- [ ] BAA includes unlimited audit rights
- [ ] Right to audit on-demand
- [ ] Right to conduct security assessments
- [ ] Right to receive audit reports (vendor's own audits)
- [ ] Right to inspect facilities
- [ ] Right to interview staff
- [ ] Right to review logs
- [ ] Audit costs covered by vendor

---

## 7. INCIDENT RESPONSE

### 7.1 Breach Notification Procedures

#### Breach Detection
- [ ] Monitoring system identifies suspicious activity
- [ ] Users can report suspected breaches
- [ ] Audit log review detects unauthorized access
- [ ] Data loss prevention (DLP) system alerts
- [ ] Intrusion detection system (IDS) alerts
- [ ] System anomaly detection triggers
- [ ] Phishing/social engineering reports
- [ ] Third-party breach notifications

#### Breach Confirmation
- [ ] Incident response team activated
- [ ] Preliminary investigation within 24 hours
- [ ] Determination: breach or false alarm
- [ ] Scope of breach assessed
- [ ] Affected systems isolated (if needed)
- [ ] Evidence preserved for forensics
- [ ] Incident severity assigned
- [ ] Decision to escalate documented

#### Incident Team Composition
- [ ] Chief Information Security Officer (lead)
- [ ] Chief Compliance Officer
- [ ] Legal Counsel
- [ ] Risk Manager
- [ ] IT Operations Lead
- [ ] Database Administrator
- [ ] Communications Officer
- [ ] Incident responder (forensics)
- [ ] Affected Department Head

#### Required Notifications
- [ ] HHS Office for Civil Rights (OCR) notified:
  - [ ] If breach affects >500 residents of a state
  - [ ] Notification within 60 days of discovery
  - [ ] Detailed information on breach
  - [ ] Mitigation measures documented
  
- [ ] Affected Individuals notified:
  - [ ] Within 72 hours of discovery (California AB 1808)
  - [ ] Without unreasonable delay (HIPAA minimum)
  - [ ] Method: written notice at last known address
  - [ ] Alternative method if address invalid
  - [ ] Notice includes:
    - [ ] What happened (plain language)
    - [ ] What data was exposed (categories, not specifics)
    - [ ] What they should do
    - [ ] What organization is doing
    - [ ] Contact information for questions
    - [ ] Free credit monitoring offered (if financial data)
    
- [ ] Media notified (if >500 individuals in state):
  - [ ] Same timeframe as individual notification
  - [ ] Prominent media in state
  - [ ] Summary of breach
  - [ ] Organization response
  - [ ] Contact information
  
- [ ] Workforce notification:
  - [ ] Affected employees notified
  - [ ] Investigation findings shared (appropriate level)
  - [ ] Support resources provided
  - [ ] Retraining offered (if negligence factor)

#### Notification Content Standards
- [ ] Plain language (avoid technical jargon)
- [ ] Concise summary of facts
- [ ] Dates of breach and discovery
- [ ] Types of data exposed
- [ ] Mitigation steps taken
- [ ] Mitigation steps individuals should take
- [ ] Credit monitoring offered (if appropriate)
- [ ] Contact information for questions
- [ ] Website with additional information
- [ ] Toll-free phone number

#### Documentation Requirements
- [ ] Breach log created (if not existing incident)
- [ ] Incident documentation includes:
  - [ ] Date breach discovered
  - [ ] Date breach likely occurred
  - [ ] Description of breach
  - [ ] Cause (intentional/unintentional)
  - [ ] Data elements involved
  - [ ] Number of individuals affected
  - [ ] Mitigation measures taken
  - [ ] Copies of notices sent
  - [ ] Investigation findings

### 7.2 Timeline Requirements

#### Discovery to Notification (72 hours maximum)
- [ ] Hour 0-4: Incident reported and documented
- [ ] Hour 4-12: Preliminary assessment completed
- [ ] Hour 12-24: Scope of breach determined
- [ ] Hour 24-48: Legal review completed
- [ ] Hour 48-72: Notification sent to individuals/HHS

#### Specific Milestones
- [ ] Within 24 hours of discovery:
  - [ ] Incident team convened
  - [ ] Initial response plan developed
  - [ ] Affected systems isolated (if ongoing risk)
  - [ ] Evidence gathered for forensics
  
- [ ] Within 48 hours of discovery:
  - [ ] Investigation substantially complete
  - [ ] Scope clearly defined
  - [ ] Root cause identified
  - [ ] Legal counsel consulted
  - [ ] Notifications drafted
  
- [ ] Within 72 hours of discovery:
  - [ ] Notifications sent to individuals
  - [ ] HHS notified (if >500 individuals)
  - [ ] Media notification (if required)
  - [ ] Forensic investigation begun
  - [ ] Communication plan in place

#### Forensic Investigation (7-30 days)
- [ ] Detailed forensic analysis conducted
- [ ] Root cause analysis completed
- [ ] System vulnerabilities identified
- [ ] Responsible parties identified
- [ ] Systemic issues addressed
- [ ] Lessons learned documented
- [ ] Corrective actions planned
- [ ] Corrective actions implemented

#### Follow-Up Activities (30-90 days)
- [ ] Corrective actions implemented
- [ ] System hardening completed
- [ ] Staff retraining conducted
- [ ] Monitoring enhanced
- [ ] Incident report finalized
- [ ] Board/leadership briefed
- [ ] Communication with individuals (if applicable)
- [ ] Credit monitoring service activated (if appropriate)

### 7.3 Documentation Requirements

#### Required Documentation
- [ ] Incident ticket with full details
- [ ] Timeline of discovery and response
- [ ] Preliminary incident report
- [ ] Forensic investigation report
- [ ] Root cause analysis document
- [ ] Scope assessment (number of individuals, data elements)
- [ ] Notification templates (draft and final)
- [ ] Copies of actual notifications sent
- [ ] Proof of notification (delivery confirmation)
- [ ] Legal review and approval documentation
- [ ] Communications log (internal and external)
- [ ] Corrective action plan document
- [ ] Implementation tracking of corrective actions
- [ ] Follow-up monitoring plan
- [ ] Final incident report
- [ ] Lessons learned document

#### Record Retention
- [ ] Incident documentation retained indefinitely
- [ ] Forensic evidence retained per legal hold
- [ ] Notifications retained per legal hold
- [ ] Investigation reports retained per legal hold
- [ ] Corrective action status tracked
- [ ] Annual incident summary report
- [ ] Pattern analysis from incident trending

#### Incident Classification
- [ ] Confidentiality breach:
  - [ ] Unauthorized access to PHI
  - [ ] Data exposure
  - [ ] Loss of device with PHI
  
- [ ] Integrity breach:
  - [ ] Unauthorized modification of data
  - [ ] Data corruption
  - [ ] Loss of data
  
- [ ] Availability breach:
  - [ ] Unauthorized deletion
  - [ ] System downtime affecting access
  - [ ] Denial of service
  
- [ ] Not a breach:
  - [ ] Authorized access
  - [ ] Accidental exposure to authorized parties
  - [ ] Data protected by encryption/hashing
  - [ ] Aggregate/de-identified data

#### Breach Log
- [ ] Running log of all breaches maintained
- [ ] Log includes:
  - [ ] Discovery date
  - [ ] Incident ID
  - [ ] Classification
  - [ ] Number of individuals
  - [ ] Resolution status
  - [ ] Notification status
  
- [ ] Breach log reviewed quarterly
- [ ] Pattern analysis conducted
- [ ] Trends identified and reported
- [ ] Systemic issues escalated

---

## 8. TRAINING & DOCUMENTATION

### 8.1 Staff Training Requirements

#### Initial Training (Before Access)
All personnel with PHI access must complete:

- [ ] HIPAA Privacy Rule training (1 hour)
  - [ ] What is PHI
  - [ ] Permitted uses
  - [ ] Minimum necessary principle
  - [ ] Patient rights
  - [ ] Penalties for violations
  
- [ ] HIPAA Security Rule training (1 hour)
  - [ ] Administrative safeguards
  - [ ] Physical safeguards
  - [ ] Technical safeguards
  - [ ] Risk assessment
  - [ ] Incident response
  
- [ ] Breach Notification Rule training (30 minutes)
  - [ ] What constitutes a breach
  - [ ] Notification requirements
  - [ ] Timeline
  - [ ] Individual vs. organizational responsibility
  
- [ ] ResearchFlow-specific training (2 hours)
  - [ ] System overview
  - [ ] Permitted use cases
  - [ ] Access controls and login
  - [ ] Data classification
  - [ ] Audit logging
  - [ ] Encryption overview
  - [ ] Best practices
  
- [ ] Role-specific training
  - [ ] Researcher: cohort selection, protocol compliance, data access
  - [ ] Coordinator: participant management, contact protocols
  - [ ] Analyst: de-identification, analysis workflows
  - [ ] Admin: user management, system maintenance
  - [ ] IT Ops: infrastructure, backups, disaster recovery
  
- [ ] Security awareness training (30 minutes)
  - [ ] Password hygiene
  - [ ] Phishing detection
  - [ ] Social engineering
  - [ ] Device security
  - [ ] Public WiFi risks
  - [ ] Incident reporting
  
- [ ] Documentation acknowledgment
  - [ ] Sign acknowledgment of HIPAA requirements
  - [ ] Sign acknowledgment of sanctions policy
  - [ ] Sign acknowledgment of security policy
  - [ ] Confirm understanding of role-specific requirements

#### Annual Refresher Training
- [ ] HIPAA refresher (1 hour) - covers updates/changes
- [ ] ResearchFlow updates (1 hour) - new features, policy changes
- [ ] Security awareness update (30 minutes) - evolving threats
- [ ] Incident response procedures (30 minutes) - lessons learned
- [ ] Compliance review (30 minutes) - audit findings, improvements
- [ ] Documentation acknowledgment of annual completion

#### Incident-Triggered Training
- [ ] Retraining triggered by:
  - [ ] User involved in breach/violation
  - [ ] Unauthorized access attempt
  - [ ] Failed audit finding
  - [ ] Security incident in user's area
  
- [ ] Retraining scope:
  - [ ] Individual retraining (most common)
  - [ ] Team retraining (if systemic issue)
  - [ ] Organization-wide retraining (if major incident)
  
- [ ] Completion tracked and documented

#### Training Delivery Methods
- [ ] Online training platform (LMS)
- [ ] Live webinar instruction
- [ ] In-person classroom training
- [ ] Hands-on lab sessions
- [ ] Documentation and reference materials
- [ ] Video demonstrations
- [ ] Q&A sessions
- [ ] Role-specific workshops

#### Training Completion Tracking
- [ ] Training completion rate tracked
- [ ] Non-completion escalated to manager
- [ ] Training records maintained
- [ ] Training completion date documented
- [ ] Training exam results tracked
- [ ] Remediation for failing users
- [ ] Training effectiveness assessed
- [ ] Training updates based on feedback

#### Training for Contractors/Vendors
- [ ] Contractors complete same training
- [ ] Training completed before access granted
- [ ] Completion verification required
- [ ] Contractors sign HIPAA agreement
- [ ] Periodic refresher training required
- [ ] Training documentation retained
- [ ] Access revoked immediately upon termination

### 8.2 Policy Documentation

#### Core Policies Required
- [ ] Information Security Policy
  - [ ] Objectives and scope
  - [ ] Roles and responsibilities
  - [ ] Risk assessment procedures
  - [ ] Compliance monitoring
  - [ ] Sanction procedures
  - [ ] Review schedule (annually)
  
- [ ] Access Control Policy
  - [ ] User provisioning/deprovisioning
  - [ ] Role definitions
  - [ ] Permission assignment rules
  - [ ] Authentication requirements
  - [ ] Session management
  - [ ] Emergency access procedures
  
- [ ] Encryption Policy
  - [ ] What data requires encryption
  - [ ] Encryption standards and algorithms
  - [ ] Key management procedures
  - [ ] Encryption testing requirements
  - [ ] Encryption failure response
  
- [ ] Audit and Logging Policy
  - [ ] What must be logged
  - [ ] Log retention requirements
  - [ ] Log review procedures
  - [ ] Log integrity verification
  - [ ] Suspicious activity response
  
- [ ] Data Classification Policy
  - [ ] Classification levels defined
  - [ ] Classification rules
  - [ ] Handling requirements per level
  - [ ] Reclassification procedures
  - [ ] De-classification requirements
  
- [ ] Backup and Recovery Policy
  - [ ] Backup schedule
  - [ ] Backup encryption
  - [ ] Backup retention
  - [ ] Recovery procedures
  - [ ] Recovery testing schedule
  - [ ] RTO/RPO definitions
  
- [ ] Incident Response Policy
  - [ ] Incident definition
  - [ ] Reporting procedures
  - [ ] Investigation procedures
  - [ ] Communication plan
  - [ ] Timeline requirements
  - [ ] Documentation requirements
  
- [ ] User Conduct Policy
  - [ ] Acceptable use
  - [ ] Prohibited uses
  - [ ] Monitoring procedures
  - [ ] Sanction procedures
  - [ ] Termination procedures
  
- [ ] Breach Notification Policy
  - [ ] Breach definition
  - [ ] Discovery procedures
  - [ ] Assessment procedures
  - [ ] Notification timeline
  - [ ] Notification recipients
  - [ ] Notification content
  
- [ ] Third-Party Management Policy
  - [ ] Vendor selection criteria
  - [ ] BAA requirements
  - [ ] Due diligence procedures
  - [ ] Ongoing monitoring
  - [ ] Contract termination
  - [ ] Data handling on termination
  
- [ ] Device Security Policy
  - [ ] Approved devices
  - [ ] Encryption requirements
  - [ ] Mobile device management (MDM)
  - [ ] Lost device procedures
  - [ ] Device disposal procedures
  - [ ] Remote wipe capability
  
- [ ] Physical Security Policy
  - [ ] Facility access controls
  - [ ] Badge access systems
  - [ ] Visitor management
  - [ ] Workstation security
  - [ ] Clean desk policy
  - [ ] Secure disposal of documents

#### Policy Format and Standards
- [ ] Policy document includes:
  - [ ] Title and policy number
  - [ ] Effective date
  - [ ] Owner (responsible officer)
  - [ ] Review date
  - [ ] Approval signatures
  - [ ] Change history
  - [ ] Scope and applicability
  - [ ] Detailed procedures
  - [ ] Roles and responsibilities
  - [ ] Exceptions and approvals
  - [ ] Related documents/policies
  - [ ] Definitions of key terms
  
- [ ] Policy language:
  - [ ] Clear and understandable
  - [ ] Specific and measurable
  - [ ] Enforceable
  - [ ] Current and up-to-date
  - [ ] Available to all staff
  
- [ ] Policy accessibility:
  - [ ] Published on intranet/wiki
  - [ ] Distributed to all staff
  - [ ] Available in training materials
  - [ ] Easily searchable
  - [ ] Version control maintained
  - [ ] Change notifications sent

#### Policy Review and Updates
- [ ] Policies reviewed annually (minimum)
- [ ] Reviews triggered by:
  - [ ] Regulatory changes
  - [ ] Incident findings
  - [ ] Audit recommendations
  - [ ] System changes
  - [ ] Best practice updates
  - [ ] Compliance failures
  
- [ ] Review process:
  - [ ] Policy owner initiates review
  - [ ] Stakeholders provide input
  - [ ] Legal counsel reviews
  - [ ] Compliance officer approves
  - [ ] Leadership approval
  - [ ] Staff notification of changes
  - [ ] Updated training delivered
  - [ ] Compliance acknowledgment collected
  
- [ ] Version control:
  - [ ] Version numbers tracked
  - [ ] Change log maintained
  - [ ] Previous versions retained
  - [ ] Effective date clearly marked
  - [ ] Deprecation date for old versions

### 8.3 Access to Compliance Resources

#### Documentation Repository
- [ ] Central location for all compliance documents
- [ ] Organized by category
- [ ] Version control maintained
- [ ] Search functionality available
- [ ] Access permissions set appropriately
- [ ] Regular backups maintained

#### HIPAA Reference Materials
- [ ] Office for Civil Rights (OCR) guidance documents
- [ ] HIPAA Rule summaries (Privacy, Security, Breach Notification)
- [ ] FAQs and interpretations
- [ ] Links to HHS.gov official resources
- [ ] Case law summaries of relevance
- [ ] Best practices from industry peers
- [ ] Standards organizations (NIST, HITRUST)

#### ResearchFlow Documentation
- [ ] System architecture documentation
- [ ] Data flow diagrams (showing encryption points)
- [ ] Security control implementation details
- [ ] User guides for each role
- [ ] FAQ document
- [ ] Known limitations documentation
- [ ] Contact information for support

#### Compliance Reporting
- [ ] Regular compliance audit reports
- [ ] Incident summary reports (anonymized)
- [ ] Risk assessment reports
- [ ] Vendor compliance reports
- [ ] Training completion metrics
- [ ] Policy acknowledgment tracking
- [ ] Security metrics and dashboards

#### Communication Channels
- [ ] Compliance email distribution list
- [ ] Monthly compliance newsletter
- [ ] Compliance intranet site
- [ ] Helpdesk for policy questions
- [ ] Compliance officer contact information
- [ ] Anonymous reporting hotline
- [ ] Incident reporting procedures

#### Ongoing Support
- [ ] Compliance office hours (open sessions)
- [ ] Policy interpretation assistance
- [ ] Training schedule and registration
- [ ] Refresher materials available
- [ ] Updates on regulatory changes
- [ ] Resources for specific roles
- [ ] Escalation procedures for concerns

---

## APPROVAL AND SIGN-OFF

### Pre-Deployment Verification

This checklist must be completed before ResearchFlow is deployed to production.

#### Final Verification Steps
- [ ] All sections reviewed and approved
- [ ] All checkboxes completed or documented as exceptions
- [ ] Documentation complete and accessible
- [ ] Training completed for all personnel
- [ ] Third-party BAAs signed
- [ ] Security assessment completed
- [ ] Penetration testing completed
- [ ] Incident response plan tested
- [ ] Disaster recovery tested
- [ ] Compliance officer sign-off obtained
- [ ] CISO sign-off obtained
- [ ] Legal counsel sign-off obtained
- [ ] Executive leadership approval

#### Sign-Off Authority
- [ ] _____________________________ (Chief Compliance Officer)
  Date: _______________
  
- [ ] _____________________________ (Chief Information Security Officer)
  Date: _______________
  
- [ ] _____________________________ (Legal Counsel)
  Date: _______________
  
- [ ] _____________________________ (Chief Executive Officer / Research Director)
  Date: _______________

#### Post-Deployment Monitoring
- [ ] Quarterly compliance audit scheduled
- [ ] Annual policy review scheduled
- [ ] Incident metrics tracked
- [ ] Audit log monitoring active
- [ ] User access review quarterly
- [ ] Third-party compliance verification quarterly
- [ ] Risk assessment update annually

---

## REVISION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-29 | Compliance Team | Initial comprehensive checklist for PHASE 4 deployment |

---

**Document Classification:** Confidential - For Internal Use Only  
**Distribution:** Compliance Office, IT Security, Senior Leadership  
**Next Review Date:** 2027-01-29
