#!/bin/bash

# $1 is the video pi IP address, $2 is the buffer directory, $3 is the external HD directory
rsync -av --progress --remove-source-files "pi@$1:$2/ $3"
rsync -av --progress --remove-source-files "pi@$1:~/video/*.log $3"
rsync -arvz --progress --remove-source-files "$2/ $3"
