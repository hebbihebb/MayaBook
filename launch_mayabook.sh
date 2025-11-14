#!/bin/bash
# MayaBook Launcher for Linux
# Double-click this file to launch the application

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Try to find Python in conda environment first, then fall back to system python3
if [ -f "$HOME/miniconda3/bin/python" ]; then
    PYTHON="$HOME/miniconda3/bin/python"
elif [ -f "$HOME/anaconda3/bin/python" ]; then
    PYTHON="$HOME/anaconda3/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    zenity --error --text="Python 3 is not installed.\nPlease install Python 3 to run MayaBook." --title="MayaBook Error" 2>/dev/null || \
    notify-send "MayaBook Error" "Python 3 is not installed" || \
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

echo "Using Python: $PYTHON"
$PYTHON --version

# Check if app.py exists
if [ ! -f "app.py" ]; then
    zenity --error --text="app.py not found in:\n$SCRIPT_DIR" --title="MayaBook Error" 2>/dev/null || \
    notify-send "MayaBook Error" "app.py not found" || \
    echo "ERROR: app.py not found"
    exit 1
fi

# Launch the application
$PYTHON app.py

# Keep terminal open if there was an error
if [ $? -ne 0 ]; then
    echo ""
    echo "Press Enter to close..."
    read
fi
