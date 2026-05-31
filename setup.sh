#!/bin/bash

echo "==================================="
echo "  DFish Setup Script v2.1.0"
echo "==================================="

# Update and install Python
if [ -d "/data/data/com.termux" ]; then
    pkg update -y && pkg upgrade -y
    pkg install python -y
else
    sudo apt update -y
    sudo apt install python3 python3-pip -y
fi

# Install dependencies
pip install -r requirements.txt

# Request storage permission (Termux only)
if [ -d "/data/data/com.termux" ]; then
    termux-setup-storage
fi

# Make main script executable
chmod +x DFish.py

echo ""
echo "Installation complete!"
echo "Run: python DFish.py"
