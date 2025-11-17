#!/bin/bash
# SIGNUM API Server Startup Script

set -e

echo "🏥 SIGNUM Healthcare Provider Intelligence API"
echo "=============================================="

# Get Python version info
echo "🐍 Python version: $(python3 --version)"
echo "📁 Current directory: $(pwd)"

# Remove existing venv if it's corrupted
if [ -d ".venv" ] && [ ! -f ".venv/bin/activate" ]; then
    echo "🗑️  Removing corrupted virtual environment..."
    rm -rf .venv
fi

# Check if virtual environment exists and is valid
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
    echo "📦 Creating fresh virtual environment..."
    python3 -m venv .venv
    
    # Verify creation was successful
    if [ ! -f ".venv/bin/activate" ]; then
        echo "❌ Failed to create virtual environment"
        echo "💡 Try: python3 -m pip install --user virtualenv"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Verify activation
if [ "$VIRTUAL_ENV" = "" ]; then
    echo "❌ Failed to activate virtual environment"
    echo "💡 Trying alternative activation method..."
    
    # Try alternative activation
    export PATH="$(pwd)/.venv/bin:$PATH"
    export VIRTUAL_ENV="$(pwd)/.venv"
    
    if ! command -v python >/dev/null 2>&1; then
        echo "❌ Virtual environment still not working"
        exit 1
    fi
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"
echo "🐍 Using Python: $(which python)"

# Upgrade pip first
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "📋 Installing API dependencies..."
pip install fastapi uvicorn python-dotenv pydantic

# Install additional dependencies that might be needed
echo "📋 Installing additional dependencies..."
pip install requests pandas numpy scikit-learn duckdb typer rich

# Mark dependencies as installed
touch .venv/api_deps_installed
echo "✅ Dependencies installed"

# Create necessary directories
echo "📁 Setting up directories..."
mkdir -p provider/hospital/data
mkdir -p provider/hospital/warehouse
mkdir -p provider/hospital/reports

# Create .env file if it doesn't exist
if [ ! -f "provider/.env" ]; then
    echo "⚙️  Creating .env configuration file..."
    mkdir -p provider
    cat > provider/.env << 'EOF'
# SIGNUM API Configuration
GOOGLE_API_KEY=your_google_api_key_here
FREE_APIS_OFFLINE=0
PORT=8000
HOST=0.0.0.0
CMS_WAREHOUSE_DIR=provider/hospital/warehouse
CMS_REPORTS_DIR=provider/hospital/reports
DISABLE_AI=0
EOF
    echo "📝 Configuration file created at provider/.env"
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/provider"
echo "🐍 Python path: $PYTHONPATH"

# Test basic imports
echo "🔍 Testing basic imports..."
python -c "import sys; print('Python executable:', sys.executable)"
python -c "import fastapi; print('FastAPI version:', fastapi.__version__)"

echo ""
echo "🚀 Starting SIGNUM API Server..."
echo "📊 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python api_server.py