#!/bin/bash

# $1 is the video pi IP address, $2 is the buffer directory, $3 is the external HD directory, $4 is a video sync boolean
if [ "$4" = "True" ]; then
  echo ""
  echo "Transferring Raspberry Pi video"
  rsync -av --progress --remove-source-files "pi@$1:$2/" "$3"
  if [ $? -ne 0 ]; then
    echo "Error: Failed to sync video files" >&2
    exit 1
  fi

  rsync -av --progress --remove-source-files "pi@$1:~/video/*.log" "$3"
  if [ $? -ne 0 ]; then
    echo "Error: Failed to sync log files" >&2
    exit 1
  fi

else
  echo ""
  echo "No Raspberry Pi video to save"
fi

echo "Transferring buffer files"
echo "rsync -arvz --progress --remove-source-files $2 $3"
rsync -arvz --progress --remove-source-files "$2" "$3"
if [ $? -ne 0 ]; then
  echo "Error: Failed to sync buffer files" >&2
  exit 1
fi

echo "File transfer completed successfully."
