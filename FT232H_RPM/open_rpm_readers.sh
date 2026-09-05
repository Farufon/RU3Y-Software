#!/bin/bash

# Define the base command (adjust path if needed)
CMD0="./rpm_reader_static --index 0 --poles 8 --ratio 8.0 --window 0.05"
CMD1="./rpm_reader_static --index 1 --poles 8 --ratio 8.0 --window 0.05"

# Get the working directory (adjust if needed)
WORKDIR=$(pwd)

# Open CMD0 in new Terminal window
osascript <<EOF
tell application "Terminal"
    do script "cd \"$WORKDIR\"; $CMD0"
end tell
EOF

# Open CMD1 in another new Terminal window
osascript <<EOF
tell application "Terminal"
    do script "cd \"$WORKDIR\"; $CMD1"
end tell
EOF