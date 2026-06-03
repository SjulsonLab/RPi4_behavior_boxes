#!/bin/sh

# Function to display usage
usage() {
    echo "=========================================="
    echo "  Lab Folder Creator Script"
    echo "=========================================="
    echo ""
    echo "USAGE:"
    echo "  $0 <name> <description>"
    echo "  $0 [OPTIONS] <name> <description>"
    echo ""
    echo "EXAMPLES:"
    echo "  # Basic usage (no options)"
    echo "  $0 mouse15 hippocampus_recording"
    echo "  $0 experiment01 \"memory encoding task\""
    echo ""
    echo "  # With options"
    echo "  $0 -d 20241210 rat08 cortex_recording"
    echo "  $0 -p ~/research -c mouse16 \"visual stimuli\""
    echo ""
    echo "OPTIONS:"
    echo "  -d, --date DATE     Use custom date (format: YYYYMMDD)"
    echo "  -p, --path PATH     Specify parent directory (default: current)"
    echo "  -c, --content       Add sample content to text file"
    echo "  -h, --help         Display this help message"
    echo ""
    echo "CREATES:"
    echo "  Folder: <name>_<yyyymmdd>_<description>/"
    echo "  Text file: <name>_<yyyymmdd>.txt"
    echo "  Subfolders: ephys/raw/, rpi/, teensy/"
    echo ""
    echo "=========================================="
    exit 0
}

# Default values
custom_date=""
parent_dir="."
add_content=false

# Parse command line options
while [ $# -gt 0 ]; do
    case $1 in
        -d|--date)
            custom_date="$2"
            shift 2
            ;;
        -p|--path)
            parent_dir="$2"
            shift 2
            ;;
        -c|--content)
            add_content=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -?*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            # First non-option argument is name, second is description
            if [ -z "$name" ]; then
                name="$1"
            elif [ -z "$description" ]; then
                description="$1"
            else
                echo "Error: Too many arguments"
                usage
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$name" ] || [ -z "$description" ]; then
    echo "Error: Missing required arguments"
    usage
fi

# Validate name (no special characters, no spaces)
if echo "$name" | grep -qE '[^a-zA-Z0-9_-]'; then
    echo "Error: Name can only contain letters, numbers, hyphens, and underscores"
    exit 1
fi

# Validate description (no slashes)
if echo "$description" | grep -q '[/\\]'; then
    echo "Error: Description cannot contain slashes"
    exit 1
fi

# Validate parent directory
if [ ! -d "$parent_dir" ]; then
    echo "Error: Parent directory '$parent_dir' does not exist"
    exit 1
fi

# Get date string
if [ -n "$custom_date" ]; then
    # Validate date format (YYYYMMDD)
    if echo "$custom_date" | grep -qvE '^[0-9]{8}$'; then
        echo "Error: Date must be in YYYYMMDD format"
        exit 1
    fi
    date_str="$custom_date"
else
    date_str=$(date +"%Y%m%d")
fi

# Create folder name (replace spaces in description with underscores)
clean_description=$(echo "$description" | tr ' ' '_')
folder_name="${name}_${date_str}_${clean_description}"
full_path="$parent_dir/$folder_name"

# Create text file name
text_file="${name}_${date_str}.txt"
text_file_path="$full_path/$text_file"

# Check if folder already exists
if [ -d "$full_path" ]; then
    echo "Error: Folder '$folder_name' already exists in '$parent_dir'"
    exit 1
fi

echo "Creating folder structure: $folder_name"

# Create main folder
mkdir -p "$full_path"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create main folder"
    exit 1
fi

# Create empty text file in main folder
echo "Creating text file: $text_file"
if [ "$add_content" = true ]; then
    # Create file with sample content
    cat > "$text_file_path" << EOF
Experiment: $name
Date: $date_str
Description: $description
Created: $(date)

Notes:
---------------
1. 
2. 
3. 

Files to add:
-------------
- ephys/raw/: Raw electrophysiology data
- rpi/: Raspberry Pi configuration and logs
- teensy/: Teensy microcontroller treadmill logs
EOF
    echo "Added sample content to $text_file"
else
    # Create empty file
    touch "$text_file_path"
fi

# Create subfolders
echo "Creating subfolders..."
mkdir -p "$full_path/ephys/raw"
mkdir -p "$full_path/rpi"
mkdir -p "$full_path/teensy"

# Verify creation
if [ -d "$full_path/ephys/raw" ] && [ -d "$full_path/rpi" ] && [ -d "$full_path/teensy" ] && [ -f "$text_file_path" ]; then
    echo "Success! Folder structure created:"
    
    # Try to use tree command if available
    if command -v tree >/dev/null 2>&1; then
        tree "$full_path" --dirsfirst
    else
        echo "$folder_name/"
        echo "├── $text_file"
        echo "├── ephys/"
        echo "│   └── raw/"
        echo "├── rpi/"
        echo "└── teensy/"
    fi
    
    echo ""
    echo "Full path: $full_path"
    
    # Display text file info
    echo ""
    echo "Text file created: $text_file_path"
    lines=$(wc -l < "$text_file_path" 2>/dev/null || echo "0")
    bytes=$(wc -c < "$text_file_path" 2>/dev/null || echo "0")
    echo "File size: $lines lines, $bytes bytes"
    
    # Create a README file with folder info (optional)
    cat > "$full_path/README.txt" << EOF
Project Structure
=================

Main Folder: $folder_name
Created: $(date)

Contents:
1. $text_file - Main experiment notes
2. ephys/raw/ - Raw electrophysiology recordings
3. rpi/ - Raspberry Pi related files (configs, logs)
4. teensy/ - Teensy microcontroller treadmill logs

Metadata:
- Experiment ID: $name
- Date: $date_str
- Description: $description
EOF
    echo "README file created: $full_path/README.txt"
    
else
    echo "Error: Some items were not created properly"
    exit 1
fi

echo ""
echo "Done!"
