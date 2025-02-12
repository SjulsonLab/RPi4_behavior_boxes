#!/bin/bash

# Check if the folder path is provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <folder_path>"
  exit 1
fi

# Make all files in the specified folder executable
for file in "$1"/*; do
  if [ -f "$file" ]; then
    chmod +x "$file"
    echo "Made $file executable"
  fi
done
