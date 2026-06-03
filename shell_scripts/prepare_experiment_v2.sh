#!/bin/sh

usage() {
    echo "=========================================="
    echo "  Lab Experiment Folder Creator v2"
    echo "=========================================="
    echo ""
    echo "USAGE:"
    echo "  $0 <subject> <tag>"
    echo "  $0 [OPTIONS] <subject> <tag>"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 CT020 latent_inference"
    echo "  $0 -d 20260603 -p /mnt/sda CT020 latent_inference"
    echo "  $0 -p /mnt/sda -c CT020 \"latent inference\""
    echo ""
    echo "OPTIONS:"
    echo "  -d, --date DATE     Use custom date (format: YYYYMMDD)"
    echo "  -p, --path PATH     Specify top folder (default: current directory)"
    echo "  -c, --content       Add sample content to notes file"
    echo "  -h, --help          Display this help message"
    echo ""
    echo "CREATES:"
    echo "  Folder: <top_folder>/<subject>/<subject>_<yyyymmdd>_<tag>/"
    echo "  Text file: <subject>_<yyyymmdd>.txt"
    echo "  Subfolders: ephys/raw/, rpi/, teensy/"
    echo ""
    echo "=========================================="
    exit 0
}

custom_date=""
top_folder="."
add_content=false

while [ $# -gt 0 ]; do
    case $1 in
        -d|--date)
            custom_date="$2"
            shift 2
            ;;
        -p|--path)
            top_folder="$2"
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
            if [ -z "$subject" ]; then
                subject="$1"
            elif [ -z "$tag" ]; then
                tag="$1"
            else
                echo "Error: Too many arguments"
                usage
            fi
            shift
            ;;
    esac
done

if [ -z "$subject" ] || [ -z "$tag" ]; then
    echo "Error: Missing required arguments"
    usage
fi

if echo "$subject" | grep -qE '[^a-zA-Z0-9_-]'; then
    echo "Error: Subject can only contain letters, numbers, hyphens, and underscores"
    exit 1
fi

if echo "$tag" | grep -q '[/\\]'; then
    echo "Error: Tag cannot contain slashes"
    exit 1
fi

if [ ! -d "$top_folder" ]; then
    echo "Error: Top folder '$top_folder' does not exist"
    exit 1
fi

if [ -n "$custom_date" ]; then
    if echo "$custom_date" | grep -qvE '^[0-9]{8}$'; then
        echo "Error: Date must be in YYYYMMDD format"
        exit 1
    fi
    date_str="$custom_date"
else
    date_str=$(date +"%Y%m%d")
fi

clean_tag=$(echo "$tag" | tr ' ' '_')
subject_dir="$top_folder/$subject"
session_name="${subject}_${date_str}_${clean_tag}"
session_dir="$subject_dir/$session_name"
text_file="${subject}_${date_str}.txt"
text_file_path="$session_dir/$text_file"

if [ -d "$session_dir" ]; then
    echo "Error: Session folder '$session_name' already exists in '$subject_dir'"
    exit 1
fi

echo "Creating subject folder if needed: $subject_dir"
mkdir -p "$subject_dir"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create subject folder"
    exit 1
fi

echo "Creating session folder structure: $session_name"
mkdir -p "$session_dir/ephys/raw"
mkdir -p "$session_dir/rpi"
mkdir -p "$session_dir/teensy"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create session subfolders"
    exit 1
fi

echo "Creating text file: $text_file"
if [ "$add_content" = true ]; then
    cat > "$text_file_path" << EOF
Experiment: $subject
Date: $date_str
Tag: $clean_tag
Created: $(date)

Notes:
---------------
1.
2.
3.

Files to add:
-------------
- ephys/raw/: Raw electrophysiology data
- rpi/: Raspberry Pi behavior-box files, logs, and session metadata
- teensy/: Teensy microcontroller treadmill logs
EOF
    echo "Added sample content to $text_file"
else
    touch "$text_file_path"
fi

cat > "$session_dir/README.txt" << EOF
Project Structure
=================

Subject: $subject
Session: $session_name
Created: $(date)

Contents:
1. $text_file - Main experiment notes
2. ephys/raw/ - Raw electrophysiology recordings
3. rpi/ - Raspberry Pi behavior-box files, logs, and session metadata
4. teensy/ - Teensy microcontroller treadmill logs

Metadata:
- Subject: $subject
- Date: $date_str
- Tag: $clean_tag
EOF

if [ -d "$session_dir/ephys/raw" ] && [ -d "$session_dir/rpi" ] && [ -d "$session_dir/teensy" ] && [ -f "$text_file_path" ] && [ -f "$session_dir/README.txt" ]; then
    echo "Success! Folder structure created:"
    if command -v tree >/dev/null 2>&1; then
        tree "$subject_dir" --dirsfirst
    else
        echo "$subject/"
        echo "  $session_name/"
        echo "    $text_file"
        echo "    README.txt"
        echo "    ephys/"
        echo "      raw/"
        echo "    rpi/"
        echo "    teensy/"
    fi

    echo ""
    echo "Full path: $session_dir"
    echo "Raspberry Pi output parent: $session_dir/rpi"
else
    echo "Error: Some items were not created properly"
    exit 1
fi

echo ""
echo "Done!"
