#!/bin/bash
# Setup script for SIGNUM API systemd service

echo "🔧 Setting up SIGNUM API as a systemd service..."

# Copy service file to systemd directory
echo "📋 Copying service file..."
sudo cp signum-api.service /etc/systemd/system/

# Reload systemd to recognize the new service
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service to start on boot
echo "✅ Enabling service to start on boot..."
sudo systemctl enable signum-api

# Start the service
echo "🚀 Starting SIGNUM API service..."
sudo systemctl start signum-api

# Wait a moment for the service to start
sleep 3

# Check service status
echo ""
echo "📊 Service Status:"
sudo systemctl status signum-api --no-pager

echo ""
echo "✅ Setup complete!"
echo ""
echo "Useful commands:"
echo "  - Check status:        sudo systemctl status signum-api"
echo "  - View logs:           sudo journalctl -u signum-api -f"
echo "  - Restart service:     sudo systemctl restart signum-api"
echo "  - Stop service:        sudo systemctl stop signum-api"
echo "  - Disable auto-start:  sudo systemctl disable signum-api"
