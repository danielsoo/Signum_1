# 🚀 AWS Deployment Guide for SIGNUM Healthcare API

Complete guide to deploy the SIGNUM Healthcare Provider Intelligence Platform API on AWS Cloud.

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Options](#architecture-options)
4. [Deployment Option A: EC2 (Recommended for Starting)](#deployment-option-a-ec2)
5. [Deployment Option B: Elastic Beanstalk](#deployment-option-b-elastic-beanstalk)
6. [Deployment Option C: ECS/Fargate (Production)](#deployment-option-c-ecs-fargate)
7. [Dataset Upload Strategy](#dataset-upload-strategy)
8. [Environment Configuration](#environment-configuration)
9. [Cost Estimation](#cost-estimation)
10. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🎯 Overview

SIGNUM is a FastAPI-based healthcare provider intelligence platform that requires:
- **Python Runtime**: Python 3.9+
- **Database**: DuckDB (embedded, file-based)
- **Data Storage**: ~500MB+ hospital datasets (CSV files)
- **API Server**: FastAPI with Uvicorn
- **External APIs**: Google Places API (optional), NPPES (free)

---

## ✅ Prerequisites

### 1. AWS Account Setup
- Active AWS account with billing enabled
- AWS CLI installed and configured
- IAM user with appropriate permissions:
  - EC2 full access
  - S3 full access
  - CloudWatch read access
  - (Optional) Elastic Beanstalk, ECS permissions

### 2. Local Development Environment
- Python 3.9+ installed
- Git installed
- SSH key pair generated

### 3. API Keys (if applicable)
- Google Places API key (optional, for enhanced features)
- Store in AWS Secrets Manager or Parameter Store

---

## 🏗️ Architecture Options

### Option A: EC2 Instance (Simplest)
**Best for**: Initial deployment, testing, low-medium traffic
- **Pros**: Simple, full control, easy debugging
- **Cons**: Manual scaling, manual updates
- **Cost**: ~$10-30/month (t3.small - t3.medium)

### Option B: Elastic Beanstalk (Managed)
**Best for**: Quick production deployment, automatic scaling
- **Pros**: Auto-scaling, load balancing, monitoring
- **Cons**: Less control, slightly higher cost
- **Cost**: ~$20-50/month (with auto-scaling)

### Option C: ECS/Fargate (Containerized)
**Best for**: Large-scale production, microservices
- **Pros**: Highly scalable, containerized, modern
- **Cons**: Complex setup, requires Docker knowledge
- **Cost**: ~$30-100/month (depending on scale)

---

## 🖥️ Deployment Option A: EC2

### Step 1: Launch EC2 Instance

```bash
# 1. Log into AWS Console
# 2. Navigate to EC2 → Launch Instance

# Configuration:
# - Name: signum-api-server
# - AMI: Ubuntu Server 22.04 LTS
# - Instance type: t3.small (2 vCPU, 2 GB RAM) or t3.medium for better performance
# - Key pair: Create new or use existing
# - Network: Default VPC
# - Security group: Create new with following rules:
#   - SSH (22) - Your IP only
#   - HTTP (80) - Anywhere
#   - HTTPS (443) - Anywhere
#   - Custom TCP (8000) - Anywhere (for FastAPI)
# - Storage: 20 GB gp3 SSD minimum (30 GB recommended)
```

### Step 2: Connect to EC2 Instance

```bash
# Download your .pem key and set permissions
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
```

### Step 3: Install Dependencies on EC2

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install system dependencies
sudo apt install -y git curl wget unzip build-essential

# Install nginx (reverse proxy)
sudo apt install -y nginx

# Verify installations
python3.11 --version
pip3 --version
git --version
```

### Step 4: Upload Project Files

#### Method 1: Git Clone (Recommended)
```bash
# On EC2 instance
cd /home/ubuntu
git clone https://github.com/yourusername/Signum_1.git
cd Signum_1
```

#### Method 2: SCP Upload from Local Machine
```bash
# From your local machine
cd /Users/harshmaheshwari/development
tar -czf signum.tar.gz Signum_1/ \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc'

scp -i your-key.pem signum.tar.gz ubuntu@<ec2-ip>:/home/ubuntu/

# On EC2, extract
ssh -i your-key.pem ubuntu@<ec2-ip>
cd /home/ubuntu
tar -xzf signum.tar.gz
```

### Step 5: Upload Hospital Dataset to S3

```bash
# From local machine - create S3 bucket
aws s3 mb s3://signum-hospital-data

# Upload dataset
cd /Users/harshmaheshwari/development/Signum_1
aws s3 sync hospitals_current_data/ s3://signum-hospital-data/hospitals_current_data/

# Verify upload
aws s3 ls s3://signum-hospital-data/hospitals_current_data/
```

### Step 6: Download Dataset on EC2

```bash
# On EC2 instance
cd /home/ubuntu/Signum_1

# Install AWS CLI if not present
sudo apt install -y awscli

# Configure AWS credentials (use IAM role or access keys)
aws configure
# Enter: Access Key, Secret Key, Region (e.g., us-east-1)

# Download dataset from S3
aws s3 sync s3://signum-hospital-data/hospitals_current_data/ hospitals_current_data/

# Verify download
ls -lh hospitals_current_data/
```

### Step 7: Setup Python Environment

```bash
cd /home/ubuntu/Signum_1

# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements-api.txt

# Verify installation
python -c "import fastapi; import uvicorn; print('✅ Dependencies installed')"
```

### Step 8: Configure Environment Variables

```bash
# Create .env file
cd /home/ubuntu/Signum_1
nano .env

# Add the following (modify as needed):
```

```env
# .env file
GOOGLE_API_KEY=your_google_api_key_here_if_applicable
WAREHOUSE_DIR=/home/ubuntu/Signum_1/provider/hospital/warehouse
DATA_DIR=/home/ubuntu/Signum_1/hospitals_current_data
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

```bash
# Save and exit (Ctrl+X, Y, Enter)
chmod 600 .env  # Secure the file
```

### Step 9: Load Hospital Data into DuckDB

```bash
cd /home/ubuntu/Signum_1
source .venv/bin/activate

# Run data loading script
python load_data.py

# This will:
# - Load CSV files from hospitals_current_data/
# - Transform and validate data
# - Create DuckDB database in provider/hospital/warehouse/

# Verify database creation
ls -lh provider/hospital/warehouse/
```

### Step 10: Test API Locally

```bash
# Start API server (test)
cd /home/ubuntu/Signum_1
source .venv/bin/activate
python api_server.py

# In another terminal, test
curl http://localhost:8000/health
curl http://localhost:8000/docs

# If successful, stop server (Ctrl+C)
```

### Step 11: Setup Systemd Service (Production)

```bash
# Create systemd service file
sudo nano /etc/systemd/system/signum-api.service
```

```ini
[Unit]
Description=SIGNUM Healthcare API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Signum_1
Environment="PATH=/home/ubuntu/Signum_1/.venv/bin"
ExecStart=/home/ubuntu/Signum_1/.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Save and exit

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable signum-api

# Start service
sudo systemctl start signum-api

# Check status
sudo systemctl status signum-api

# View logs
sudo journalctl -u signum-api -f
```

### Step 12: Configure Nginx Reverse Proxy

```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/signum-api
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or use EC2 public IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

```bash
# Save and exit

# Enable site
sudo ln -s /etc/nginx/sites-available/signum-api /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Enable nginx on boot
sudo systemctl enable nginx
```

### Step 13: Setup SSL with Let's Encrypt (Optional but Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Follow prompts
# - Enter email
# - Agree to terms
# - Choose redirect option (2 - redirect HTTP to HTTPS)

# Auto-renewal is setup automatically
# Test renewal
sudo certbot renew --dry-run
```

### Step 14: Test Production API

```bash
# Test from local machine
curl http://<ec2-public-ip>/health
curl http://<ec2-public-ip>/api/v1/hospitals/search?query=Mayo

# Or visit in browser
http://<ec2-public-ip>/docs
```

---

## 🌐 Deployment Option B: Elastic Beanstalk

### Step 1: Prepare Application

```bash
cd /Users/harshmaheshwari/development/Signum_1

# Create application.py (entry point for EB)
cat > application.py << 'EOF'
from api_server import app

# Elastic Beanstalk expects 'application' variable
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=8000)
EOF
```

### Step 2: Create .ebextensions Configuration

```bash
mkdir -p .ebextensions

# Create configuration file
cat > .ebextensions/01_packages.config << 'EOF'
packages:
  yum:
    git: []
    gcc: []
    
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: application:application
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current:$PYTHONPATH"
EOF

# Create data download configuration
cat > .ebextensions/02_data_download.config << 'EOF'
commands:
  01_download_data:
    command: |
      aws s3 sync s3://signum-hospital-data/hospitals_current_data/ /var/app/current/hospitals_current_data/
    leader_only: true
  02_create_warehouse:
    command: |
      mkdir -p /var/app/current/provider/hospital/warehouse
    leader_only: true
  03_load_data:
    command: |
      source /var/app/venv/*/bin/activate && python load_data.py
    leader_only: true
EOF
```

### Step 3: Create requirements.txt for EB

```bash
# EB expects requirements.txt at root
cp requirements-api.txt requirements.txt
```

### Step 4: Initialize and Deploy

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init -p python-3.11 signum-api --region us-east-1

# Create environment
eb create signum-api-prod \
  --instance-type t3.small \
  --envvars GOOGLE_API_KEY=your_key_here

# Deploy
eb deploy

# Open in browser
eb open

# Check status
eb status

# View logs
eb logs
```

### Step 5: Configure Auto-Scaling

```bash
# Edit configuration
eb config

# Update auto-scaling settings:
# - MinSize: 1
# - MaxSize: 4
# - Trigger: CPU > 70% or Requests > 1000/min
```

---

## 🐳 Deployment Option C: ECS/Fargate

### Step 1: Create Dockerfile

```bash
cd /Users/harshmaheshwari/development/Signum_1

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-api.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy application code
COPY . .

# Create warehouse directory
RUN mkdir -p /app/provider/hospital/warehouse

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
EOF
```

### Step 2: Create docker-compose.yml (for testing)

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - WAREHOUSE_DIR=/app/provider/hospital/warehouse
    volumes:
      - ./hospitals_current_data:/app/hospitals_current_data
      - ./provider/hospital/warehouse:/app/provider/hospital/warehouse
    restart: unless-stopped
```

### Step 3: Build and Push to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name signum-api --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t signum-api .

# Tag image
docker tag signum-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/signum-api:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/signum-api:latest
```

### Step 4: Create ECS Cluster

```bash
# Using AWS CLI
aws ecs create-cluster --cluster-name signum-cluster --region us-east-1
```

### Step 5: Create Task Definition

```json
{
  "family": "signum-api-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "signum-api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/signum-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "WAREHOUSE_DIR",
          "value": "/app/provider/hospital/warehouse"
        }
      ],
      "secrets": [
        {
          "name": "GOOGLE_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:google-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/signum-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Step 6: Create Service

```bash
aws ecs create-service \
  --cluster signum-cluster \
  --service-name signum-api-service \
  --task-definition signum-api-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

---

## 📦 Dataset Upload Strategy

### Strategy 1: S3 Storage (Recommended)

#### Advantages:
- Durable, scalable
- Easy to update
- Version control
- Can serve multiple instances

#### Implementation:

```bash
# 1. Create S3 bucket
aws s3 mb s3://signum-hospital-data --region us-east-1

# 2. Enable versioning
aws s3api put-bucket-versioning \
  --bucket signum-hospital-data \
  --versioning-configuration Status=Enabled

# 3. Upload data
cd /Users/harshmaheshwari/development/Signum_1
aws s3 sync hospitals_current_data/ s3://signum-hospital-data/hospitals_current_data/

# 4. Set lifecycle policy (optional - for cost optimization)
cat > lifecycle.json << 'EOF'
{
  "Rules": [
    {
      "Id": "Archive old versions",
      "Status": "Enabled",
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket signum-hospital-data \
  --lifecycle-configuration file://lifecycle.json

# 5. Create IAM role for EC2/ECS to access S3
# Attach policy: AmazonS3ReadOnlyAccess to your instance role
```

### Strategy 2: EBS Volume (For EC2)

```bash
# 1. Create EBS volume (100 GB)
aws ec2 create-volume \
  --volume-type gp3 \
  --size 100 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=signum-data}]'

# 2. Attach to EC2 instance
aws ec2 attach-volume \
  --volume-id vol-1234567890abcdef0 \
  --instance-id i-1234567890abcdef0 \
  --device /dev/sdf

# 3. On EC2, mount volume
sudo mkfs -t ext4 /dev/sdf
sudo mkdir /mnt/data
sudo mount /dev/sdf /mnt/data
sudo chown ubuntu:ubuntu /mnt/data

# 4. Upload data
scp -r hospitals_current_data ubuntu@<ec2-ip>:/mnt/data/
```

### Strategy 3: EFS (Elastic File System) - For Multiple Instances

```bash
# 1. Create EFS
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=signum-efs

# 2. Mount on EC2
sudo apt-get install -y amazon-efs-utils
sudo mkdir /mnt/efs
sudo mount -t efs fs-12345678:/ /mnt/efs

# 3. Upload data to EFS
cp -r hospitals_current_data /mnt/efs/
```

---

## ⚙️ Environment Configuration

### 1. AWS Secrets Manager (Recommended for Production)

```bash
# Store Google API key
aws secretsmanager create-secret \
  --name signum/google-api-key \
  --secret-string "your-api-key-here" \
  --region us-east-1

# Retrieve in code (update api_server.py)
```

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
# GOOGLE_API_KEY = get_secret('signum/google-api-key')
```

### 2. AWS Systems Manager Parameter Store (Free)

```bash
# Store parameters
aws ssm put-parameter \
  --name /signum/google-api-key \
  --value "your-api-key" \
  --type SecureString

# Retrieve
aws ssm get-parameter \
  --name /signum/google-api-key \
  --with-decryption
```

### 3. Environment Variables (.env file)

```bash
# On EC2: /home/ubuntu/Signum_1/.env
GOOGLE_API_KEY=your_key_here
WAREHOUSE_DIR=/home/ubuntu/Signum_1/provider/hospital/warehouse
DATA_DIR=/home/ubuntu/Signum_1/hospitals_current_data
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*
```

---

## 💰 Cost Estimation

### EC2 Option (Monthly)
| Resource | Specification | Cost |
|----------|--------------|------|
| EC2 Instance | t3.small (2 vCPU, 2GB) | $15 |
| EBS Storage | 30 GB gp3 | $2.40 |
| S3 Storage | 1 GB data | $0.02 |
| Data Transfer | 10 GB/month | $0.90 |
| **Total** | | **~$18/month** |

### Elastic Beanstalk (Monthly)
| Resource | Specification | Cost |
|----------|--------------|------|
| EC2 Instance | t3.small x 2 (auto-scaling) | $30 |
| Load Balancer | Application LB | $16 |
| EBS Storage | 60 GB | $4.80 |
| **Total** | | **~$51/month** |

### ECS Fargate (Monthly)
| Resource | Specification | Cost |
|----------|--------------|------|
| Fargate (0.5 vCPU, 1 GB) | 2 tasks, 24/7 | $35 |
| Load Balancer | Application LB | $16 |
| Data Transfer | 10 GB | $0.90 |
| **Total** | | **~$52/month** |

### Additional Costs (All Options)
- **Domain Name**: ~$12/year
- **SSL Certificate**: Free (Let's Encrypt)
- **CloudWatch Logs**: ~$0.50/month
- **S3 Requests**: ~$0.05/month

---

## 📊 Monitoring & Maintenance

### 1. CloudWatch Monitoring

```bash
# Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name signum-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 2. Log Aggregation

```bash
# Install CloudWatch agent on EC2
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure to ship logs
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### 3. Backup Strategy

```bash
# Backup DuckDB database to S3 daily
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /tmp/warehouse_backup_${DATE}.tar.gz -C /home/ubuntu/Signum_1/provider/hospital warehouse/
aws s3 cp /tmp/warehouse_backup_${DATE}.tar.gz s3://signum-backups/
rm /tmp/warehouse_backup_${DATE}.tar.gz
EOF

chmod +x /home/ubuntu/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup.sh") | crontab -
```

### 4. Update Process

```bash
# Update application code
cd /home/ubuntu/Signum_1
git pull origin main
source .venv/bin/activate
pip install -r requirements-api.txt

# Restart service
sudo systemctl restart signum-api

# Check status
sudo systemctl status signum-api
```

---

## 🔒 Security Best Practices

### 1. Security Group Configuration
- **Port 22 (SSH)**: Only your IP or bastion host
- **Port 80/443 (HTTP/S)**: 0.0.0.0/0
- **Port 8000**: Only from Load Balancer (if using)

### 2. IAM Roles
- Create dedicated IAM role for EC2/ECS
- Grant minimum permissions (S3 read, Secrets Manager read)
- No hardcoded credentials

### 3. API Security
- Enable CORS properly (restrict origins in production)
- Add API key authentication
- Rate limiting
- HTTPS only

### 4. Data Security
- Encrypt EBS volumes
- Enable S3 bucket encryption
- Use VPC endpoints for S3 access
- Regular security updates

---

## 🚀 Quick Start Commands

### Complete EC2 Deployment Script

```bash
#!/bin/bash
# Save as deploy_ec2.sh and run on EC2 instance

set -e

echo "🚀 SIGNUM API Deployment Script"

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx awscli

# Clone repository
cd /home/ubuntu
git clone https://github.com/yourusername/Signum_1.git
cd Signum_1

# Setup Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-api.txt

# Download dataset from S3
aws s3 sync s3://signum-hospital-data/hospitals_current_data/ hospitals_current_data/

# Load data
python load_data.py

# Create systemd service
sudo tee /etc/systemd/system/signum-api.service > /dev/null <<EOF
[Unit]
Description=SIGNUM Healthcare API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Signum_1
Environment="PATH=/home/ubuntu/Signum_1/.venv/bin"
ExecStart=/home/ubuntu/Signum_1/.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable signum-api
sudo systemctl start signum-api

echo "✅ Deployment complete!"
echo "🌐 API running at http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
```

---

## 📚 Additional Resources

- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Production](https://www.uvicorn.org/deployment/)
- [DuckDB Best Practices](https://duckdb.org/docs/guides/index)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

---

## 🆘 Troubleshooting

### Common Issues

1. **Port 8000 not accessible**
   ```bash
   # Check security group allows port 8000
   # Check service is running: sudo systemctl status signum-api
   # Check firewall: sudo ufw status
   ```

2. **Out of memory**
   ```bash
   # Increase instance size or add swap
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **DuckDB errors**
   ```bash
   # Ensure warehouse directory exists and is writable
   mkdir -p provider/hospital/warehouse
   chmod 755 provider/hospital/warehouse
   ```

4. **Data download fails**
   ```bash
   # Check IAM role permissions
   aws sts get-caller-identity
   # Verify S3 bucket access
   aws s3 ls s3://signum-hospital-data/
   ```

---

## 📝 Checklist

Before going live:
- [ ] EC2 instance launched with appropriate size
- [ ] Security groups configured
- [ ] Python environment setup
- [ ] Dataset uploaded to S3
- [ ] Dataset downloaded and loaded into DuckDB
- [ ] API tested locally
- [ ] Systemd service configured
- [ ] Nginx reverse proxy setup
- [ ] SSL certificate installed (if using domain)
- [ ] CloudWatch monitoring enabled
- [ ] Backup strategy implemented
- [ ] API documentation accessible (/docs)
- [ ] Cost alerts configured
- [ ] Security best practices applied

---

**Last Updated**: November 2025
**Version**: 1.0
**Author**: SIGNUM Development Team
