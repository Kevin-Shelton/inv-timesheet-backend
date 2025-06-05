#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set environment variables if .env file exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Run the Flask application
cd src
python main.py

