# 🚀 SIGNUM AWS - Quick Reference Card

**One-page cheat sheet for deploying and managing your SIGNUM API**

---

## 📦 Pre-Deployment (Local Machine)

```bash
# 1. Upload dataset to S3
aws s3 mb s3://signum-hospital-data --region us-east-1
aws s3 sync hospitals_current_data/ s3://signum-hospital-data/hospitals_current_data/

# 2. Package code for upload
cd /Users/harshmaheshwari/development/Signum_1
tar -czf signum.tar.gz --exclude='.venv' --exclude='__pycache__' .

# 3. Upload to EC2
scp -i your-key.pem signum.tar.gz ubuntu@EC2_IP:/home/ubuntu/
scp -i your-key.pem deploy_ec2.sh ubuntu@EC2_IP:/home/ubuntu/
```

---

## 🖥️ EC2 Instance Setup

```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@EC2_IP

# Extract and deploy
cd /home/ubuntu
tar -xzf signum.tar.gz
chmod +x deploy_ec2.sh
./deploy_ec2.sh
```

---

## 🔧 Service Management

```bash
# Start
sudo systemctl start signum-api

# Stop
sudo systemctl stop signum-api

# Restart
sudo systemctl restart signum-api

# Status
sudo systemctl status signum-api

# Enable on boot
sudo systemctl enable signum-api

# Disable
sudo systemctl disable signum-api
```

---

## 📊 Logs & Monitoring

```bash
# Real-time logs
sudo journalctl -u signum-api -f

# Last 100 lines
sudo journalctl -u signum-api -n 100

# Logs since 1 hour ago
sudo journalctl -u signum-api --since "1 hour ago"

# Error logs only
sudo journalctl -u signum-api -p err

# Check system resources
htop
free -h
df -h
```

---

## 🌐 API Endpoints

| Endpoint | URL |
|----------|-----|
| Health | `http://EC2_IP:8000/health` |
| Docs | `http://EC2_IP:8000/docs` |
| Search | `http://EC2_IP:8000/api/v1/hospitals/search?query=Mayo` |
| Details | `http://EC2_IP:8000/api/v1/hospitals/{id}` |
| Risk | `http://EC2_IP:8000/api/v1/hospitals/{id}/risk` |

---

## 🔄 Update Application

```bash
# Pull latest code
cd /home/ubuntu/Signum_1
git pull  # or upload new files

# Update dependencies
source .venv/bin/activate
pip install -r requirements-api.txt

# Restart service
sudo systemctl restart signum-api
```

---

## 💾 Backup & Restore

```bash
# Manual backup
/home/ubuntu/backup.sh

# Restore from backup
cd /home/ubuntu/Signum_1/provider/hospital
tar -xzf /home/ubuntu/backups/warehouse_backup_YYYYMMDD_HHMMSS.tar.gz

# Backup to S3
aws s3 cp /home/ubuntu/backups/warehouse_backup_*.tar.gz s3://signum-backups/
```

---

## 🐛 Quick Troubleshooting

### Service won't start
```bash
sudo journalctl -u signum-api -n 50
source /home/ubuntu/Signum_1/.venv/bin/activate
pip install -r requirements-api.txt
```

### Can't connect to API
```bash
sudo systemctl status signum-api
sudo lsof -i :8000
curl http://localhost:8000/health
```

### Out of disk space
```bash
df -h
sudo apt clean
rm -rf ~/.cache/*
```

### Out of memory
```bash
free -h
# Add swap:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 🔒 Security Quick Fixes

```bash
# Update security group (AWS Console)
# SSH (22): Your IP only
# HTTP (80): 0.0.0.0/0
# HTTPS (443): 0.0.0.0/0
# API (8000): 0.0.0.0/0

# Update firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw enable

# Secure .env file
chmod 600 /home/ubuntu/Signum_1/.env
```

---

## 🔑 Environment Variables

Edit: `/home/ubuntu/Signum_1/.env`

```bash
WAREHOUSE_DIR=/home/ubuntu/Signum_1/provider/hospital/warehouse
DATA_DIR=/home/ubuntu/Signum_1/hospitals_current_data
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=*
GOOGLE_API_KEY=your_key_here
```

After editing: `sudo systemctl restart signum-api`

---

## 📈 Performance Tuning

```bash
# Increase workers (in systemd service)
sudo nano /etc/systemd/system/signum-api.service
# Change: --workers 2  to  --workers 4
sudo systemctl daemon-reload
sudo systemctl restart signum-api

# Enable caching in Nginx
sudo nano /etc/nginx/sites-available/signum-api
# Add caching directives
sudo nginx -t
sudo systemctl restart nginx
```

---

## 💰 Cost Monitoring

```bash
# Check EC2 instance details
aws ec2 describe-instances --instance-ids i-xxxxx

# Monitor S3 usage
aws s3 ls s3://signum-hospital-data --recursive --summarize

# Set billing alert (AWS Console)
# CloudWatch → Billing → Create Alarm → When > $20
```

---

## 🎯 Common Commands

```bash
# Check Python version
python3 --version

# Activate virtual environment
source /home/ubuntu/Signum_1/.venv/bin/activate

# Test API locally
curl http://localhost:8000/health

# Get EC2 public IP
curl http://169.254.169.254/latest/meta-data/public-ipv4

# Download from S3
aws s3 sync s3://signum-hospital-data/hospitals_current_data/ hospitals_current_data/

# System update
sudo apt update && sudo apt upgrade -y
```

---

## 📞 Emergency Contacts

| Issue | Command |
|-------|---------|
| Service down | `sudo systemctl restart signum-api` |
| High CPU | `htop` → Kill process → Restart service |
| Disk full | `df -h` → Clean logs → `sudo apt clean` |
| Memory leak | Restart instance (AWS Console) |
| Can't SSH | Check security group, key permissions |

---

## 📚 Documentation Files

- `QUICK_START_AWS.md` - Beginner guide
- `AWS_DEPLOYMENT_GUIDE.md` - Complete reference
- `DEPLOYMENT_CHECKLIST.md` - Validation checklist
- `DEPLOYMENT_SUMMARY.md` - Package overview
- `API_DOCUMENTATION.md` - API usage
- `deploy_ec2.sh` - Automated deployment

---

**Save this file for quick reference! 🔖**

*Last Updated: November 2025*
