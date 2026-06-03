import subprocess
from pathlib import Path


SCRIPT = Path("shell_scripts/prepare_experiment_v2.sh")


def run_prepare_experiment_v2(tmp_path, *args):
    """Run the v2 experiment folder creation script.

    Data contract:
    - Inputs:
      - `tmp_path`: pathlib.Path temporary top folder.
      - `*args`: command-line string arguments passed after the script path.
    - Output:
      - `subprocess.CompletedProcess` with captured text stdout/stderr.
    """
    return subprocess.run(
        ["sh", str(SCRIPT), "-p", str(tmp_path), *args],
        capture_output=True,
        text=True,
    )


def test_prepare_experiment_v2_creates_subject_session_structure(tmp_path):
    """Create `<top>/<subject>/<subject>_<date>_<tag>/...` folders.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts subject, session, ephys/raw, rpi, teensy, notes, and README paths exist.
    """
    result = run_prepare_experiment_v2(tmp_path, "-d", "20260603", "CT020", "latent_inference")

    session_dir = tmp_path / "CT020" / "CT020_20260603_latent_inference"
    assert result.returncode == 0, result.stderr
    assert (session_dir / "ephys" / "raw").is_dir()
    assert (session_dir / "rpi").is_dir()
    assert (session_dir / "teensy").is_dir()
    assert (session_dir / "CT020_20260603.txt").is_file()
    assert (session_dir / "README.txt").is_file()


def test_prepare_experiment_v2_creates_missing_subject_folder(tmp_path):
    """Create the subject folder when it does not already exist.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts `<top>/<subject>` is created.
    """
    result = run_prepare_experiment_v2(tmp_path, "-d", "20260603", "CT020", "latent_inference")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "CT020").is_dir()


def test_prepare_experiment_v2_reuses_existing_subject_folder(tmp_path):
    """Reuse an existing subject folder while creating a new session folder.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts the new session folder is created under the pre-existing subject folder.
    """
    subject_dir = tmp_path / "CT020"
    subject_dir.mkdir()

    result = run_prepare_experiment_v2(tmp_path, "-d", "20260603", "CT020", "latent_inference")

    assert result.returncode == 0, result.stderr
    assert (subject_dir / "CT020_20260603_latent_inference").is_dir()


def test_prepare_experiment_v2_fails_when_session_folder_exists(tmp_path):
    """Do not overwrite an existing session folder.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts a pre-existing session folder causes a nonzero exit.
    """
    session_dir = tmp_path / "CT020" / "CT020_20260603_latent_inference"
    session_dir.mkdir(parents=True)

    result = run_prepare_experiment_v2(tmp_path, "-d", "20260603", "CT020", "latent_inference")

    assert result.returncode != 0
    assert "already exists" in result.stdout or "already exists" in result.stderr


def test_prepare_experiment_v2_rejects_invalid_subject(tmp_path):
    """Reject subject names with unsupported characters.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts an invalid subject name causes a nonzero exit.
    """
    result = run_prepare_experiment_v2(tmp_path, "-d", "20260603", "CT/020", "latent_inference")

    assert result.returncode != 0
    assert "Subject" in result.stdout or "Subject" in result.stderr


def test_prepare_experiment_v2_rejects_invalid_tag(tmp_path):
    """Reject tags containing path separators.

    Data contract:
    - Inputs:
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts an invalid tag causes a nonzero exit.
    """
    result = run_prepare_experiment_v2(tmp_path, "-d", "20260603", "CT020", "latent/inference")

    assert result.returncode != 0
    assert "Tag" in result.stdout or "Tag" in result.stderr
