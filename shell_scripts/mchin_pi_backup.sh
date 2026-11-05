#!/bin/bash
# For use with behavior Pis. Can also be used with the ephys Pi, but the workflow there is different.

rm -r /mnt/sda/test*
rsync --dry-run -aP --remove-source-files /mnt/sda/  mchin1@mchin1.hpc.einsteinmed.edu:~/contextProjectData/


