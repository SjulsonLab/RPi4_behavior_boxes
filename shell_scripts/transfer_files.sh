#!/bin/bash

# $1 is the buffer directory, $2 is the external HD directory, $3 is the video pi IP address
# check to see if the correct number of arguments are provided
if [ "$#" -lt 2 ]; then
  echo "Script has at least 2 arguments" >&2
  echo "Usage: $0 <buffer_directory> <external_hd_directory> <video_pi_ip>" >&2
  exit 1
fi

if [ "$#" -eq 3 ]; then
  echo ""
  echo "Transferring Raspberry Pi video"
  rsync -av --progress --remove-source-files "pi@$3:$1/" "$2"
  if [ $? -ne 0 ]; then
    echo "Error: Failed to sync video files" >&2
    exit 1
  fi

## if you are saving the log files and videos in the same directory, skip this step ##
#  rsync -av --progress --remove-source-files "pi@$3:~/video/*.log" "$2"
#  if [ $? -ne 0 ]; then
#    echo "Error: Failed to sync log files" >&2
#    exit 1
#  fi

else
  echo ""
  echo "Skipping Raspberry Pi video transfer"
fi

echo "Transferring buffer files"
echo "rsync -arvz --progress --remove-source-files $1/ $2"
rsync -arvz --progress --remove-source-files "$1/" "$2"
if [ $? -ne 0 ]; then
  echo "Error: Failed to sync buffer files" >&2
  exit 1
fi

echo "File transfer completed successfully."
exit 0
