# 🚀 SIGNUM AWS Quick Start Guide

**Get your SIGNUM Healthcare API running on AWS in 30 minutes!**

---

## 🎯 What You'll Deploy

A production-ready FastAPI server that provides:
- Hospital search and analytics
- Risk analysis and quality metrics  
- Multi-source data integration (CMS, NPPES, Google Places)
- Interactive API documentation
- RESTful JSON API

---

## 📋 Prerequisites (5 minutes)

### 1. AWS Account
- Create free tier account at [aws.amazon.com](https://aws.amazon.com)
- Add payment method (you'll stay within free tier for testing)

### 2. Local Tools
```bash
# Install AWS CLI (macOS)
brew install awscli

# Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Format (json)
```

### 3. Get Your Files Ready
- Your code: `/Users/harshmaheshwari/development/Signum_1/`
- Your data: `hospitals_current_data/` folder with CSV files

---

## 🏃‍♂️ Quick Deployment (3 Simple Steps)

### Step 1: Upload Dataset to S3 (5 minutes)

```bash
# From your local machine
cd /Users/harshmaheshwari/development/Signum_1

# Create S3 bucket
aws s3 mb s3://signum-hospital-data-$(whoami) --region us-east-1

# Upload your CSV files
aws s3 sync hospitals_current_data/ s3://signum-hospital-data-$(whoami)/hospitals_current_data/

# Verify (should show ~40+ files)
aws s3 ls s3://signum-hospital-data-$(whoami)/hospitals_current_data/ --recursive | wc -l
```

**✅ Data uploaded! Estimated cost: $0.01/month**

---

### Step 2: Launch EC2 Instance (10 minutes)

#### A. Launch Instance via AWS Console

1. Go to [AWS EC2 Console](https://console.aws.amazon.com/ec2)
2. Click **"Launch Instance"**
3. Configure:
   - **Name**: `signum-api-server`
   - **AMI**: Ubuntu Server 22.04 LTS (free tier eligible)
   - **Instance type**: `t3.small` (or `t2.micro` for free tier)
   - **Key pair**: Create new → Download `.pem` file → Save it!
   - **Network**: Default VPC
   - **Storage**: 20 GB gp3
4. **Security Group** - Add these rules:
   ```
   SSH     (22)   - My IP (for security)
   HTTP    (80)   - Anywhere
   HTTPS   (443)  - Anywhere  
   Custom  (8000) - Anywhere (for API)
   ```
5. Click **"Launch Instance"**

#### B. Create IAM Role for S3 Access

1. Go to [IAM Console](https://console.aws.amazon.com/iam)
2. Roles → Create Role
3. Select **AWS Service** → **EC2**
4. Add permission: `AmazonS3ReadOnlyAccess`
5. Name: `signum-ec2-s3-role`
6. Create role
7. Back to EC2 → Select your instance → Actions → Security → Modify IAM role → Attach `signum-ec2-s3-role`

**✅ Instance running! Estimated cost: $15/month**

---

### Step 3: Deploy Application (15 minutes)

#### A. Connect to EC2

```bash
# Set permissions on your key (from Downloads folder)
chmod 400 ~/Downloads/your-key.pem

# Get your instance IP from AWS Console
# Connect via SSH
ssh -i ~/Downloads/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

#### B. Upload and Run Deployment Script

**Option 1: Automated Deployment (Recommended)**

```bash
# On your LOCAL machine, upload deployment script
scp -i ~/Downloads/your-key.pem \
  /Users/harshmaheshwari/development/Signum_1/deploy_ec2.sh \
  ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/

# Upload entire project
scp -i ~/Downloads/your-key.pem -r \
  /Users/harshmaheshwari/development/Signum_1 \
  ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/

# On EC2 instance (after SSH)
cd /home/ubuntu
chmod +x deploy_ec2.sh

# Edit S3 bucket name in script
nano deploy_ec2.sh
# Change: S3_BUCKET="signum-hospital-data-$(whoami)"
# Save: Ctrl+X, Y, Enter

# Run deployment
./deploy_ec2.sh
```

The script will:
- ✅ Install all dependencies (Python, Nginx, etc.)
- ✅ Download dataset from S3
- ✅ Create virtual environment
- ✅ Install Python packages
- ✅ Load data into DuckDB
- ✅ Configure systemd service
- ✅ Setup Nginx reverse proxy
- ✅ Start the API

**Option 2: Manual Deployment (Step-by-step)**

```bash
# On EC2 instance
cd /home/ubuntu/Signum_1

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx awscli

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements-api.txt

# Download data from S3
aws s3 sync s3://signum-hospital-data-$(whoami)/hospitals_current_data/ hospitals_current_data/

# Load data
python load_data.py

# Start API (test)
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Visit: http://YOUR_EC2_IP:8000/docs
```

---

## ✅ Verify Deployment

### Test Endpoints

```bash
# From your local machine
export EC2_IP="YOUR_EC2_PUBLIC_IP"

# Health check
curl http://$EC2_IP:8000/health

# Search hospitals
curl "http://$EC2_IP:8000/api/v1/hospitals/search?query=Mayo&limit=5"

# API documentation
open http://$EC2_IP:8000/docs
```

Expected responses:
```json
// Health check
{"status":"healthy","timestamp":"2025-11-05T..."}

// Hospital search
[
  {
    "facility_id": "100001",
    "facility_name": "MAYO CLINIC HOSPITAL...",
    "state": "AZ",
    "overall_rating": 5.0,
    ...
  }
]
```

---

## 🎨 Access Your API

Once deployed, your API is available at:

| Endpoint | URL | Description |
|----------|-----|-------------|
| **API Docs** | `http://YOUR_EC2_IP:8000/docs` | Interactive Swagger UI |
| **ReDoc** | `http://YOUR_EC2_IP:8000/redoc` | Alternative documentation |
| **Health** | `http://YOUR_EC2_IP:8000/health` | Service health status |
| **Search** | `http://YOUR_EC2_IP:8000/api/v1/hospitals/search` | Hospital search |
| **Details** | `http://YOUR_EC2_IP:8000/api/v1/hospitals/{id}` | Hospital details |
| **Risk** | `http://YOUR_EC2_IP:8000/api/v1/hospitals/{id}/risk` | Risk analysis |

---

## 🎯 Common Use Cases

### 1. Search Hospitals by Name

```bash
curl "http://YOUR_EC2_IP:8000/api/v1/hospitals/search?query=Cleveland%20Clinic&limit=10"
```

### 2. Search by Location

```bash
curl "http://YOUR_EC2_IP:8000/api/v1/hospitals/search?state=CA&city=Los%20Angeles&limit=20"
```

### 3. Search by Quality Rating

```bash
curl "http://YOUR_EC2_IP:8000/api/v1/hospitals/search?min_rating=4&limit=50"
```

### 4. Get Hospital Details

```bash
curl "http://YOUR_EC2_IP:8000/api/v1/hospitals/100001"
```

### 5. Get Risk Analysis

```bash
curl "http://YOUR_EC2_IP:8000/api/v1/hospitals/100001/risk"
```

---

## 🔧 Management Commands

### Check Service Status
```bash
sudo systemctl status signum-api
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u signum-api -f

# Last 100 lines
sudo journalctl -u signum-api -n 100
```

### Restart Service
```bash
sudo systemctl restart signum-api
```

### Stop Service
```bash
sudo systemctl stop signum-api
```

### Update Application
```bash
cd /home/ubuntu/Signum_1
git pull  # if using git
source .venv/bin/activate
pip install -r requirements-api.txt
sudo systemctl restart signum-api
```

---

## 💰 Cost Breakdown

### Free Tier (First 12 Months)
- **EC2 t2.micro**: 750 hours/month FREE
- **S3 Storage**: 5 GB FREE
- **Data Transfer**: 100 GB/month FREE

### After Free Tier (Monthly)
- **EC2 t3.small**: ~$15
- **EBS 20 GB**: ~$2
- **S3 1 GB**: ~$0.02
- **Data Transfer**: ~$1 (10GB)
- **Total**: ~$18/month

### Cost Optimization Tips
- Use `t2.micro` for testing (free tier)
- Upgrade to `t3.small` for production
- Stop instance when not in use (keeps data, no EC2 charges)
- Use reserved instances for 40% savings (1-year commitment)

---

## 🔐 Security Best Practices

### 1. Secure SSH Access
```bash
# Edit security group to only allow YOUR IP
# AWS Console → EC2 → Security Groups → Edit inbound rules
# SSH (22): My IP (not 0.0.0.0/0)
```

### 2. Update System Regularly
```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Configure Firewall
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8000/tcp # API
sudo ufw enable
```

### 4. Add SSL Certificate (Production)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

### 5. Restrict CORS (Production)
```bash
# Edit .env file
nano /home/ubuntu/Signum_1/.env

# Change:
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Restart service
sudo systemctl restart signum-api
```

---

## 🐛 Troubleshooting

### API won't start
```bash
# Check logs
sudo journalctl -u signum-api -n 50

# Common fixes:
source /home/ubuntu/Signum_1/.venv/bin/activate
pip install -r requirements-api.txt
sudo systemctl restart signum-api
```

### Can't connect from browser
```bash
# Check security group allows port 8000
# Check service is running
sudo systemctl status signum-api

# Check if port is listening
sudo lsof -i :8000
```

### Data loading failed
```bash
# Check CSV files exist
ls /home/ubuntu/Signum_1/hospitals_current_data/*.csv | wc -l

# Re-download from S3
aws s3 sync s3://signum-hospital-data-$(whoami)/hospitals_current_data/ \
  /home/ubuntu/Signum_1/hospitals_current_data/

# Re-run data loading
cd /home/ubuntu/Signum_1
source .venv/bin/activate
python load_data.py
```

### Out of memory
```bash
# Check memory usage
free -h

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📚 Next Steps

### 1. Custom Domain
- Register domain (Namecheap, GoDaddy, Route53)
- Point A record to EC2 IP
- Setup SSL with Let's Encrypt

### 2. API Authentication
- Implement API keys
- Add rate limiting
- Setup user accounts

### 3. Monitoring
- Enable CloudWatch metrics
- Setup alerts for downtime
- Configure log aggregation

### 4. Scale Up
- Auto-scaling groups
- Load balancer
- RDS for database (instead of DuckDB)
- ElastiCache for caching

### 5. CI/CD Pipeline
- GitHub Actions
- Automated testing
- Blue-green deployment

---

## 📖 Documentation

- **Full Deployment Guide**: `AWS_DEPLOYMENT_GUIDE.md`
- **Deployment Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **API Documentation**: `API_DOCUMENTATION.md`
- **Project Overview**: `README.md`

---

## 🆘 Get Help

### Command Reference
```bash
# Service management
sudo systemctl {start|stop|restart|status} signum-api

# Logs
sudo journalctl -u signum-api -f
sudo journalctl -u signum-api -n 100
sudo journalctl -u signum-api --since "1 hour ago"

# Nginx
sudo systemctl status nginx
sudo nginx -t  # test configuration

# System
df -h          # disk usage
free -h        # memory usage
htop           # processes
```

### Support Resources
- AWS Support: [aws.amazon.com/support](https://aws.amazon.com/support)
- FastAPI Docs: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- DuckDB Docs: [duckdb.org/docs](https://duckdb.org/docs)

---

## ✨ Success!

You now have a production-ready healthcare API running on AWS! 🎉

**Test it**: `http://YOUR_EC2_IP:8000/docs`

**Share it**: Your API is publicly accessible (add auth in production)

**Monitor it**: `sudo journalctl -u signum-api -f`

**Scale it**: See `AWS_DEPLOYMENT_GUIDE.md` for advanced options

---

*Last Updated: November 2025*
*Estimated Setup Time: 30-45 minutes*
*Difficulty: Beginner-Friendly*
