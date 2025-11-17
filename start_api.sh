#!/bin/bash
# SIGNUM API Server Startup Script

set -e

echo "🏥 SIGNUM Healthcare Provider Intelligence API"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if requirements are installed
if [ ! -f ".venv/api_deps_installed" ]; then
    echo "📋 Installing API dependencies..."
    pip install --upgrade pip
    pip install -r requirements-api.txt
    touch .venv/api_deps_installed
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Check if .env file exists
if [ ! -f "provider/.env" ]; then
    echo "⚙️  Creating .env configuration file..."
    mkdir -p provider
    cat > provider/.env << EOF
# SIGNUM API Configuration
# ======================

# Google Places API (optional)
GOOGLE_API_KEY=your_google_api_key_here

# Feature flags
FREE_APIS_OFFLINE=0

# API server settings
PORT=8000
HOST=0.0.0.0

# Warehouse and reports directories
CMS_WAREHOUSE_DIR=provider/hospital/warehouse
CMS_REPORTS_DIR=provider/hospital/reports

# Disable AI features if needed (for testing without full setup)
DISABLE_AI=0
EOF
    echo "📝 Configuration file created at provider/.env"
    echo "💡 Edit provider/.env to configure API keys and settings"
fi

# Check if we have any hospital data
if [ ! -d "provider/hospital/data" ]; then
    echo "📁 Creating hospital data directory..."
    mkdir -p provider/hospital/data
    echo "📋 Place CMS hospital ZIP files in provider/hospital/data/"
fi

if [ ! -d "provider/hospital/warehouse" ]; then
    echo "📁 Creating warehouse directory..."
    mkdir -p provider/hospital/warehouse
fi

if [ ! -d "provider/hospital/reports" ]; then
    echo "📁 Creating reports directory..."
    mkdir -p provider/hospital/reports
fi

# Check Python path
echo "🐍 Checking Python environment..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)/provider"

# Start the API server
echo ""
echo "🚀 Starting SIGNUM API Server..."
echo "📊 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python api_server.py
