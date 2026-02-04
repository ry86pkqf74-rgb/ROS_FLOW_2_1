# Production Environment Setup Guide
# Phase 3 Enterprise Hardening - Complete Configuration

## 🎯 Overview

This guide provides comprehensive instructions for setting up the production environment for the enterprise-ready AI Bridge with Phase 3 hardening features.

---

## 📋 Prerequisites

### **System Requirements**
- **OS**: Linux (Ubuntu 20.04+ or CentOS 8+) or macOS
- **Docker**: 24.0+ with Docker Compose 2.20+
- **Memory**: 8GB+ RAM (16GB+ recommended for production)
- **Storage**: 100GB+ SSD storage
- **Network**: HTTPS/TLS 1.3 capable load balancer

### **Required Services**
- PostgreSQL 15+ (primary database)
- Redis 7+ (caching and sessions)
- SMTP server (for notifications)
- SSL/TLS certificates

### **Optional but Recommended**
- External secret management (HashiCorp Vault, AWS Secrets Manager, etc.)
- External monitoring (New Relic, Datadog, etc.)
- Remote backup storage (AWS S3, Google Cloud Storage, etc.)

---

## 🔧 Step 1: Environment Configuration

### **1.1 Copy Production Environment Template**
```bash
cp .env.production.complete .env.production
```

### **1.2 Configure Critical Secrets**

**⚠️ CRITICAL**: Update all `CHANGE_ME` values in `.env.production`:

```bash
# Generate secure passwords and keys
openssl rand -base64 32  # For database passwords
openssl rand -hex 32     # For encryption keys
openssl rand -base64 64  # For JWT secrets
```

### **1.3 Essential Configuration Updates**

**Database Configuration:**
```bash
# Strong PostgreSQL password
POSTGRES_PASSWORD=your_super_secure_db_password_here

# Strong Redis password
REDIS_PASSWORD=your_secure_redis_password_here
```

**Security Configuration:**
```bash
# JWT Secrets (must be different)
JWT_SECRET=your_64_char_jwt_secret_here
JWT_REFRESH_SECRET=your_different_64_char_refresh_secret_here

# Encryption key for sensitive data
ENCRYPTION_KEY=your_32_char_encryption_key_here

# Backup encryption key
BACKUP_ENCRYPTION_KEY=your_32_char_backup_encryption_key_here
```

**AI Service Configuration:**
```bash
# OpenAI API Key
OPENAI_API_KEY=sk-your_openai_api_key_here

# Anthropic Claude API Key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_api_key_here
```

### **1.4 Domain and CORS Configuration**
```bash
# Update for your production domain
CORS_ORIGIN=https://app.yourdomain.com,https://admin.yourdomain.com
```

---

## 🔐 Step 2: SSL/TLS Certificate Setup

### **2.1 Obtain SSL Certificates**

**Option A: Let's Encrypt (Recommended for most cases)**
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Copy certificates to Docker volume
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /path/to/ssl/certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /path/to/ssl/private/
```

**Option B: Commercial Certificate**
```bash
# Place your commercial certificates
cp your-certificate.crt /path/to/ssl/certs/researchflow.crt
cp your-private-key.key /path/to/ssl/private/researchflow.key
```

### **2.2 Update Certificate Paths in Environment**
```bash
TLS_CERT_PATH=/etc/ssl/certs/researchflow.crt
TLS_KEY_PATH=/etc/ssl/private/researchflow.key
```

---

## 💾 Step 3: Database Setup

### **3.1 PostgreSQL Production Configuration**

**Create production database:**
```sql
CREATE DATABASE researchflow_prod;
CREATE USER researchflow_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE researchflow_prod TO researchflow_user;
```

**Optimize PostgreSQL for production:**
```bash
# Add to postgresql.conf
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 1GB
```

### **3.2 Redis Configuration**
```bash
# redis.conf production settings
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

---

## 🚀 Step 4: Docker Production Deployment

### **4.1 Create Production Docker Compose Override**
```yaml
# docker-compose.prod.override.yml
version: '3.8'

services:
  orchestrator:
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./backups:/app/backups
      - ./ssl:/etc/ssl
    
  worker:
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    
  postgres:
    restart: unless-stopped
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./backups:/backups
    
  redis:
    restart: unless-stopped
    volumes:
      - redis_prod_data:/data

volumes:
  postgres_prod_data:
  redis_prod_data:
```

### **4.2 Deploy with Production Configuration**
```bash
# Build and deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.override.yml up -d --build

# Verify all services are running
docker-compose ps
```

---

## 📊 Step 5: Validation and Testing

### **5.1 Health Check Validation**
```bash
# Core health checks
curl https://yourdomain.com/health
curl https://api.yourdomain.com/api/health

# Phase 3 system health
curl https://api.yourdomain.com/api/recovery/status
curl https://api.yourdomain.com/api/backup/status
curl https://api.yourdomain.com/api/security/status
curl https://api.yourdomain.com/api/compliance/status
```

### **5.2 Phase 3 Feature Testing**
```bash
# Test error recovery
curl -X POST https://api.yourdomain.com/api/recovery/test-retry

# Test backup system
curl -X POST https://api.yourdomain.com/api/backup/test

# Test security system
curl -X POST https://api.yourdomain.com/api/security/test

# Test compliance system
curl -X POST https://api.yourdomain.com/api/compliance/test
```

### **5.3 Security Validation**
```bash
# Verify TLS 1.3 is enabled
echo | openssl s_client -connect yourdomain.com:443 -tls1_3 2>/dev/null | grep "Protocol"

# Test rate limiting
for i in {1..10}; do curl -w "%{http_code}\n" -o /dev/null -s https://api.yourdomain.com/api/security/status; done
```

---

## 🔧 Step 6: Operational Configuration

### **6.1 Log Management**
```bash
# Create log directories
mkdir -p /var/log/researchflow/{application,audit,security,backup}

# Set up log rotation
sudo tee /etc/logrotate.d/researchflow << EOF
/var/log/researchflow/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 www-data www-data
}
EOF
```

### **6.2 Backup Configuration**
```bash
# Create backup directories
mkdir -p /var/backups/researchflow/{full,incremental,metadata}

# Set up backup rotation script
sudo tee /usr/local/bin/cleanup-old-backups.sh << 'EOF'
#!/bin/bash
find /var/backups/researchflow -name "*.backup" -mtime +90 -delete
EOF

sudo chmod +x /usr/local/bin/cleanup-old-backups.sh

# Add to crontab
echo "0 3 * * 0 /usr/local/bin/cleanup-old-backups.sh" | sudo crontab -
```

### **6.3 Monitoring Setup**
```bash
# Install monitoring tools (optional)
sudo apt-get install htop iotop netstat-nat

# Create monitoring script
sudo tee /usr/local/bin/researchflow-monitor.sh << 'EOF'
#!/bin/bash
echo "$(date): ResearchFlow System Status" >> /var/log/researchflow/monitor.log
docker-compose ps >> /var/log/researchflow/monitor.log
curl -s http://localhost:3001/health >> /var/log/researchflow/monitor.log
echo "---" >> /var/log/researchflow/monitor.log
EOF

sudo chmod +x /usr/local/bin/researchflow-monitor.sh

# Run every 5 minutes
echo "*/5 * * * * /usr/local/bin/researchflow-monitor.sh" | sudo crontab -
```

---

## 🚨 Step 7: Security Hardening

### **7.1 Firewall Configuration**
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### **7.2 System Hardening**
```bash
# Disable unused services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Set secure file permissions
sudo chmod 600 .env.production
sudo chown root:docker docker-compose.yml

# Configure automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

---

## ✅ Step 8: Production Checklist

### **Pre-Deployment Checklist**
- [ ] All `CHANGE_ME` values updated in `.env.production`
- [ ] SSL certificates installed and configured
- [ ] Database passwords are strong and unique
- [ ] JWT secrets are properly configured
- [ ] CORS origins match your production domains
- [ ] Backup directories created and permissions set
- [ ] Log rotation configured
- [ ] Firewall rules applied
- [ ] Monitoring scripts installed

### **Post-Deployment Validation**
- [ ] All health checks return 200 OK
- [ ] Phase 3 systems report operational status
- [ ] TLS 1.3 is enabled and working
- [ ] Rate limiting is functional
- [ ] Backup system creates test backups successfully
- [ ] Audit logging is working
- [ ] Error recovery mechanisms respond correctly

---

## 🆘 Troubleshooting

### **Common Issues**

**Services won't start:**
```bash
# Check Docker logs
docker-compose logs orchestrator
docker-compose logs worker
docker-compose logs postgres

# Check environment variables
docker-compose config
```

**Database connection issues:**
```bash
# Test database connectivity
docker exec -it postgres psql -U postgres -d researchflow_prod -c "SELECT version();"
```

**SSL/TLS issues:**
```bash
# Verify certificate validity
openssl x509 -in /path/to/cert.crt -text -noout

# Test TLS connection
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

### **Performance Issues**
```bash
# Check system resources
docker stats
htop
df -h

# Review Phase 3 system metrics
curl https://api.yourdomain.com/api/metrics
```

---

## 🎯 Next Steps

Once production environment is set up:

1. **Load Testing** - Run performance validation
2. **Monitoring Setup** - Configure dashboards and alerts
3. **Team Training** - Onboard development team
4. **Backup Testing** - Verify disaster recovery procedures
5. **Security Audit** - Conduct penetration testing

The Phase 3 enterprise-hardened AI Bridge is now ready for production deployment! 🚀