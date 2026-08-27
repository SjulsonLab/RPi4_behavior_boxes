import subprocess
from pathlib import Path


SCRIPT = Path("shell_scripts/cleanup_storage.sh")


def run_cleanup_storage(*args):
    """Run the storage cleanup script.

    Data contract:
    - Inputs:
      - `*args`: command-line string arguments passed after the script path.
    - Output:
      - `subprocess.CompletedProcess` with captured text stdout/stderr.
    """
    return subprocess.run(
        ["sh", str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def test_cleanup_storage_deletes_nested_empty_directories(tmp_path):
    """Delete empty directories below the target while preserving the target root.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts nested empty directories are removed and the target remains.
    """
    target = tmp_path / "storage"
    empty_leaf = target / "subject" / "session" / "rpi"
    empty_leaf.mkdir(parents=True)

    result = run_cleanup_storage(str(target))

    assert result.returncode == 0, result.stderr
    assert target.is_dir()
    assert not empty_leaf.exists()
    assert not (target / "subject").exists()


def test_cleanup_storage_keeps_non_empty_directories(tmp_path):
    """Do not delete directories containing files.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts non-empty directories remain after cleanup.
    """
    target = tmp_path / "storage"
    non_empty_dir = target / "subject" / "session" / "rpi"
    empty_sibling = target / "subject" / "session" / "teensy"
    non_empty_dir.mkdir(parents=True)
    empty_sibling.mkdir(parents=True)
    (non_empty_dir / "session.log").write_text("data\n")

    result = run_cleanup_storage(str(target))

    assert result.returncode == 0, result.stderr
    assert non_empty_dir.is_dir()
    assert (non_empty_dir / "session.log").is_file()
    assert not empty_sibling.exists()
    assert (target / "subject" / "session").is_dir()


def test_cleanup_storage_dry_run_leaves_empty_directories(tmp_path):
    """Dry-run mode should report empty directories without deleting them.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts dry-run reports candidates and leaves directories in place.
    """
    target = tmp_path / "storage"
    empty_leaf = target / "subject" / "session" / "rpi"
    empty_leaf.mkdir(parents=True)

    result = run_cleanup_storage("--dry-run", str(target))

    assert result.returncode == 0, result.stderr
    assert str(empty_leaf) in result.stdout
    assert empty_leaf.is_dir()
    assert (target / "subject").is_dir()


def test_cleanup_storage_rejects_missing_target(tmp_path):
    """Missing target directories should fail instead of being created.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts a missing target returns nonzero status.
    """
    missing_target = tmp_path / "missing"

    result = run_cleanup_storage(str(missing_target))

    assert result.returncode != 0
    assert "does not exist" in result.stdout or "does not exist" in result.stderr


def test_cleanup_storage_rejects_file_target(tmp_path):
    """File targets should fail because only directories can be cleaned.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts a file target returns nonzero status.
    """
    file_target = tmp_path / "not_a_directory.txt"
    file_target.write_text("data\n")

    result = run_cleanup_storage(str(file_target))

    assert result.returncode != 0
    assert "not a directory" in result.stdout or "not a directory" in result.stderr
