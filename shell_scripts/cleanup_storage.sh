#!/bin/sh
#
# Delete empty subdirectories left behind after storage transfers.
#
# Data contract:
# - Inputs:
#   - Optional flag: --dry-run or -n, which reports removable directories without
#     deleting them.
#   - Required argument: target directory path. The target directory must already
#     exist and must be a directory.
# - Output:
#   - Prints deleted directories, or dry-run candidates, to stdout.
#   - Returns 0 on success and nonzero on invalid input or cleanup errors.
# - Units:
#   - Filesystem paths are interpreted by the local shell/filesystem.

set -u

usage() {
    # Print command-line usage.
    #
    # Data contract:
    # - Inputs: none.
    # - Output: usage text written to stdout.
    cat <<'EOF'
Usage: cleanup_storage.sh [--dry-run|-n] <directory>

Delete empty subdirectories inside <directory>, preserving <directory> itself.

Options:
  --dry-run, -n  Print empty directories that would be removed without deleting.
  --help, -h     Show this help text.
EOF
}

fail() {
    # Print an error and exit.
    #
    # Data contract:
    # - Inputs:
    #   - $1: error message string.
    # - Output: error text written to stderr, exits with status 1.
    echo "Error: $1" >&2
    exit 1
}

dry_run=0
target_dir=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run|-n)
            dry_run=1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            fail "Unknown option: $1"
            ;;
        *)
            if [ -n "$target_dir" ]; then
                fail "Expected exactly one directory argument"
            fi
            target_dir=$1
            ;;
    esac
    shift
done

if [ -z "$target_dir" ]; then
    usage
    fail "Missing directory argument"
fi

# Normalize trailing slashes while preserving the filesystem root sentinel.
while [ "$target_dir" != "/" ] && [ "${target_dir%/}" != "$target_dir" ]; do
    target_dir=${target_dir%/}
done

if [ "$target_dir" = "/" ]; then
    fail "Refusing to clean filesystem root"
fi

if [ ! -e "$target_dir" ]; then
    fail "Target directory does not exist: $target_dir"
fi

if [ ! -d "$target_dir" ]; then
    fail "Target is not a directory: $target_dir"
fi

if [ "$dry_run" -eq 1 ]; then
    echo "Dry run: empty directories that would be removed under: $target_dir"
    find "$target_dir" -depth -type d -empty ! -path "$target_dir" -print
    exit 0
fi

echo "Deleting empty directories under: $target_dir"
find "$target_dir" -depth -type d -empty ! -path "$target_dir" -print -exec rmdir {} \;
