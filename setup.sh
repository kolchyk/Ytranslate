#!/bin/bash

# Setup script for Heroku deployment
# This script runs after apt dependencies are installed

# Ensure ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: ffmpeg not found in PATH"
fi

echo "Setup complete!"
