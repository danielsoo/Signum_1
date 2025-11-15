# Quick Systemd Setup Guide

## Step 1: SSH to your EC2 instance
```bash
ssh -i ~/Downloads/api-server.pem ubuntu@<YOUR_CURRENT_IP>
```

## Step 2: Create the systemd service file
```bash
cd /home/ubuntu/Signum_1

cat > signum-api.service << 'EOF'
[Unit]
Description=SIGNUM Healthcare Provider Intelligence API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Signum_1
Environment="PATH=/home/ubuntu/Signum_1/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/ubuntu/Signum_1/.venv/bin/python /home/ubuntu/Signum_1/api_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=signum-api

[Install]
WantedBy=multi-user.target
EOF
```

## Step 3: Install and start the service
```bash
# Copy service file to systemd
sudo cp signum-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable signum-api

# Start the service
sudo systemctl start signum-api

# Check status
sudo systemctl status signum-api
```

## Step 4: Configure AWS Security Group
1. Go to AWS Console → EC2 → Instances
2. Select your instance (i-062170c84dd287071)
3. Click on the **Security** tab
4. Click on the security group link
5. Click **Edit inbound rules**
6. Click **Add rule**:
   - Type: **Custom TCP**
   - Port range: **8000**
   - Source: **0.0.0.0/0**
   - Description: **SIGNUM API Server**
7. Click **Save rules**

## Step 5: Test your API
```bash
# From your Mac (after security group is configured)
curl http://<YOUR_IP>:8000/health

# Or open in browser
http://<YOUR_IP>:8000/docs
```

---

## Useful Commands

### View logs in real-time
```bash
sudo journalctl -u signum-api -f
```

### Restart the service
```bash
sudo systemctl restart signum-api
```

### Stop the service
```bash
sudo systemctl stop signum-api
```

### Check service status
```bash
sudo systemctl status signum-api
```

### Disable auto-start on boot
```bash
sudo systemctl disable signum-api
```

---

## What This Does

✅ **Runs API automatically** when server starts
✅ **Restarts automatically** if it crashes (every 10 seconds)
✅ **Runs in background** - no need to keep SSH open
✅ **Logs to systemd journal** - easy to view with `journalctl`
✅ **Zero extra cost** - uses your existing EC2 resources

---

## Current Setup Summary

- **Instance Type**: t3.small (2GB RAM)
- **Instance ID**: i-062170c84dd287071
- **Database**: DuckDB at `/home/ubuntu/Signum_1/provider/hospital/warehouse/hospital.duckdb`
- **Data**: 721,818 metrics rows, 5,381 hospitals
- **API Port**: 8000
- **Rate Limiting**: Enabled (slowapi, in-memory)

---

## Cost Reminder

- **Year 1**: $0/month (free tier - 750 hours/month of t3.small)
- **After Year 1**: ~$16.70/month for t3.small running 24/7
- **To minimize costs**: Stop instance when not in use (but systemd won't auto-start)
