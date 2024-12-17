#!/bin/bash

# $1 is the video pi IP address, $2 is the buffer directory, $3 is the external HD directory, $4 is a video sync boolean
if [ "$4" = "True" ]; then
  echo "Transferring Raspberry Pi video"
  rsync -av --progress --remove-source-files "pi@$1:$2/ $3"
  rsync -av --progress --remove-source-files "pi@$1:~/video/*.log $3"
else
  echo "No Raspberry Pi video to save"
fi

echo "Transferring buffer files"
rsync -arvz --progress --remove-source-files "$2/ $3/"
