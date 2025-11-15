#!/bin/bash
# SIGNUM API - AWS EC2 Deployment Script
# Complete automated deployment for Ubuntu 22.04 LTS
# Version: 1.0
# Last Updated: November 2025

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/home/ubuntu/Signum_1"
S3_BUCKET="signum-hospital-data"  # Change this to your bucket name
PYTHON_VERSION="3.11"
APP_PORT="8000"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Header
echo "=============================================="
echo "   🏥 SIGNUM API Deployment Script"
echo "   AWS EC2 - Ubuntu 22.04 LTS"
echo "=============================================="
echo ""

# Check if running as ubuntu user
if [ "$USER" != "ubuntu" ]; then
    warn "This script should be run as 'ubuntu' user"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: System Update
log "📦 Step 1/10: Updating system packages..."
sudo apt update -qq
sudo apt upgrade -y -qq
log "✅ System updated"

# Step 2: Install System Dependencies
log "🔧 Step 2/10: Installing system dependencies..."
sudo apt install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    nginx \
    awscli \
    htop \
    vim \
    > /dev/null 2>&1
log "✅ System dependencies installed"

# Verify installations
python${PYTHON_VERSION} --version || error "Python installation failed"
git --version || error "Git installation failed"
nginx -v 2>&1 || error "Nginx installation failed"

# Step 3: Clone/Setup Application
log "📂 Step 3/10: Setting up application directory..."
if [ -d "$APP_DIR" ]; then
    warn "Directory $APP_DIR already exists"
    read -p "Remove and re-clone? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$APP_DIR"
        log "Creating fresh application directory..."
        mkdir -p "$APP_DIR"
    fi
else
    mkdir -p "$APP_DIR"
fi

cd "$APP_DIR" || error "Cannot access $APP_DIR"
log "✅ Application directory ready: $APP_DIR"

# Step 4: Python Virtual Environment
log "🐍 Step 4/10: Creating Python virtual environment..."
if [ -d "$APP_DIR/.venv" ]; then
    warn "Virtual environment already exists, removing..."
    rm -rf "$APP_DIR/.venv"
fi

python${PYTHON_VERSION} -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
log "✅ Virtual environment created"

# Step 5: Install Python Dependencies
log "📚 Step 5/10: Installing Python dependencies..."
if [ ! -f "$APP_DIR/requirements-api.txt" ]; then
    warn "requirements-api.txt not found, creating basic requirements..."
    cat > "$APP_DIR/requirements-api.txt" << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
python-dotenv==1.0.0
httpx==0.25.2
requests==2.31.0
pandas>=1.5.0
numpy>=1.24.0
duckdb>=0.9.0
structlog==23.2.0
EOF
fi

pip install -r requirements-api.txt -q
log "✅ Python dependencies installed"

# Step 6: Configure AWS CLI
log "☁️  Step 6/10: Configuring AWS CLI..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    warn "AWS credentials not configured"
    echo "Please configure AWS credentials manually:"
    echo "  aws configure"
    echo "Or ensure EC2 instance has IAM role with S3 access"
    read -p "Press Enter to continue..."
else
    log "✅ AWS credentials configured"
fi

# Step 7: Download Dataset from S3
log "📊 Step 7/10: Downloading hospital dataset from S3..."
mkdir -p "$APP_DIR/hospitals_current_data"

echo "Checking S3 bucket: s3://$S3_BUCKET/hospitals_current_data/"
if aws s3 ls "s3://$S3_BUCKET/hospitals_current_data/" > /dev/null 2>&1; then
    log "Downloading dataset... (this may take a few minutes)"
    aws s3 sync "s3://$S3_BUCKET/hospitals_current_data/" "$APP_DIR/hospitals_current_data/" --quiet
    
    # Verify download
    FILE_COUNT=$(ls -1 "$APP_DIR/hospitals_current_data/"*.csv 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -gt 0 ]; then
        log "✅ Downloaded $FILE_COUNT CSV files"
    else
        error "No CSV files downloaded from S3"
    fi
else
    warn "Cannot access S3 bucket: s3://$S3_BUCKET"
    warn "Please ensure:"
    warn "  1. Bucket exists and contains data"
    warn "  2. EC2 instance has S3 read permissions"
    warn "  3. Bucket name is correct in script"
    read -p "Press Enter to skip and continue..."
fi

# Step 8: Setup Environment Variables
log "⚙️  Step 8/10: Creating environment configuration..."
cat > "$APP_DIR/.env" << EOF
# SIGNUM API Configuration
# Generated: $(date)

# Data Paths
WAREHOUSE_DIR=$APP_DIR/provider/hospital/warehouse
DATA_DIR=$APP_DIR/hospitals_current_data

# Server Configuration
API_HOST=0.0.0.0
API_PORT=$APP_PORT
LOG_LEVEL=INFO

# CORS Settings
CORS_ORIGINS=*

# External API Keys (update as needed)
GOOGLE_API_KEY=

# Database
DUCKDB_PATH=$APP_DIR/provider/hospital/warehouse/hospital_data.duckdb
EOF

chmod 600 "$APP_DIR/.env"
log "✅ Environment file created: $APP_DIR/.env"

# Step 9: Load Data into DuckDB
log "💾 Step 9/10: Loading data into DuckDB..."
mkdir -p "$APP_DIR/provider/hospital/warehouse"

if [ -f "$APP_DIR/load_data.py" ]; then
    log "Running load_data.py..."
    source "$APP_DIR/.venv/bin/activate"
    python "$APP_DIR/load_data.py" || warn "Data loading had issues, check logs"
    
    # Verify database creation
    if [ -f "$APP_DIR/provider/hospital/warehouse/hospital_data.duckdb" ]; then
        DB_SIZE=$(du -h "$APP_DIR/provider/hospital/warehouse/hospital_data.duckdb" | cut -f1)
        log "✅ DuckDB database created: $DB_SIZE"
    else
        warn "DuckDB database not found, but continuing..."
    fi
else
    warn "load_data.py not found, skipping data loading"
    warn "You will need to load data manually before starting the API"
fi

# Step 10: Create Systemd Service
log "🚀 Step 10/10: Creating systemd service..."
sudo tee /etc/systemd/system/signum-api.service > /dev/null << EOF
[Unit]
Description=SIGNUM Healthcare API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port $APP_PORT --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl enable signum-api
log "✅ Systemd service created and enabled"

# Configure Nginx (Optional)
log "🌐 Configuring Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/signum-api > /dev/null << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:$APP_PORT/docs;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:$APP_PORT/redoc;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/signum-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx || warn "Nginx configuration issue"
log "✅ Nginx configured"

# Create backup script
log "💾 Creating backup script..."
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/backups"
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/warehouse_backup_${DATE}.tar.gz \
    -C /home/ubuntu/Signum_1/provider/hospital warehouse/
# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR/warehouse_backup_${DATE}.tar.gz s3://signum-backups/
# Keep only last 7 backups
ls -t $BACKUP_DIR/warehouse_backup_*.tar.gz | tail -n +8 | xargs rm -f 2>/dev/null || true
EOF
chmod +x /home/ubuntu/backup.sh
log "✅ Backup script created: /home/ubuntu/backup.sh"

# Start the service
log "🎬 Starting SIGNUM API service..."
sudo systemctl start signum-api
sleep 3

# Check status
if sudo systemctl is-active --quiet signum-api; then
    log "✅ Service is running!"
else
    error "Service failed to start. Check logs: sudo journalctl -u signum-api -n 50"
fi

# Get instance IP
INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "UNKNOWN")

# Final Summary
echo ""
echo "=============================================="
echo "   ✅ DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "📊 Service Information:"
echo "   Status:      $(sudo systemctl is-active signum-api)"
echo "   Port:        $APP_PORT"
echo "   IP Address:  $INSTANCE_IP"
echo ""
echo "🌐 Access Points:"
echo "   API:         http://$INSTANCE_IP:$APP_PORT"
echo "   Health:      http://$INSTANCE_IP:$APP_PORT/health"
echo "   Docs:        http://$INSTANCE_IP:$APP_PORT/docs"
echo "   ReDoc:       http://$INSTANCE_IP:$APP_PORT/redoc"
echo ""
echo "📝 Useful Commands:"
echo "   Check status:  sudo systemctl status signum-api"
echo "   View logs:     sudo journalctl -u signum-api -f"
echo "   Restart:       sudo systemctl restart signum-api"
echo "   Stop:          sudo systemctl stop signum-api"
echo ""
echo "🔐 Security Checklist:"
echo "   ⚠️  Update .env with actual API keys"
echo "   ⚠️  Configure security group to restrict SSH (port 22)"
echo "   ⚠️  Set up SSL certificate for production"
echo "   ⚠️  Configure CORS origins in .env"
echo ""
echo "📚 Documentation:"
echo "   AWS Guide:     $APP_DIR/AWS_DEPLOYMENT_GUIDE.md"
echo "   Checklist:     $APP_DIR/DEPLOYMENT_CHECKLIST.md"
echo ""
echo "🎉 SIGNUM API is ready to use!"
echo "=============================================="
