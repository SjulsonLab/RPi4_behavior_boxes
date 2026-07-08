"""Hotfix baseline runner files on the Raspberry Pi.

This removes the PDict-breaking deepcopy calls from the baseline run files.
Run this from ~/RPi4_behavior_boxes with:

    python3 fix_baseline_deepcopy_on_pi.py

It creates a .bak_before_nodeepcopy_hotfix backup before modifying each file.
"""
from pathlib import Path

FILES_TO_PATCH = [
    "run_go_nogo_first_rule_2p_baseline.py",
    "run_go_nogo_first_rule_2p_baseline_v2.py",
    "run_go_nogo_reversal_2p_baseline.py",
    "run_go_nogo_reversal_2p_baseline_v2.py",
]

REPLACEMENTS = {
    "session_info = copy.deepcopy(tempmod.session_info)": "session_info = tempmod.session_info",
    "mouse_info = copy.deepcopy(tempmod.mouse_info)": "mouse_info = tempmod.mouse_info",
    "import copy\n": "",
}


def patch_file(path: Path) -> None:
    if not path.exists():
        print(f"SKIP missing: {path.name}")
        return

    original_text = path.read_text()
    patched_text = original_text
    for old, new in REPLACEMENTS.items():
        patched_text = patched_text.replace(old, new)

    if patched_text == original_text:
        if "deepcopy" in original_text or "import copy" in original_text:
            print(f"WARNING: {path.name} still contains copy/deepcopy, but exact pattern was not found")
        else:
            print(f"OK already fixed: {path.name}")
        return

    backup_path = path.with_suffix(path.suffix + ".bak_before_nodeepcopy_hotfix")
    if not backup_path.exists():
        backup_path.write_text(original_text)
    path.write_text(patched_text)

    if "deepcopy" in patched_text or "import copy" in patched_text:
        print(f"PATCHED with WARNING: {path.name} still contains copy/deepcopy text; inspect with grep")
    else:
        print(f"PATCHED: {path.name}")


def main() -> None:
    print("Applying no-deepcopy hotfix in:", Path.cwd())
    for filename in FILES_TO_PATCH:
        patch_file(Path(filename))

    print("\nVerification commands to run next:")
    print("grep -n \"deepcopy\\|import copy\" run_go_nogo_first_rule_2p_baseline.py")
    print("grep -n \"deepcopy\\|import copy\" run_go_nogo_reversal_2p_baseline.py")
    print("\nBoth grep commands should print nothing.")


if __name__ == "__main__":
    main()
