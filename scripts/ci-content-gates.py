#!/usr/bin/env python3
"""
CI Content Gates — Detect byte-level corruption in repository files.

Rules:
  R1: Byte 0x08 (backspace) in any file
  R2: Isolated 0x0D (CR not followed by LF) in any file
  R3: .sh files with zero LF bytes AND size > 200 bytes
  R4: .sh files: any line > 300 chars; .md files: any line > 300 chars inside code fences

Exit 0 if clean, exit 1 if any violation found.
"""

import os
import sys
from pathlib import Path

# Directories and patterns to skip
SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    '.next', '.pytest_cache', '.workbuddy',
    'temp-engineering-review',
}
SKIP_EXTENSIONS = {'.pyc'}
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
    '.db', '.sqlite', '.sqlite3',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.webm', '.ogg', '.wav',
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.exe', '.dll', '.so', '.dylib',
    '.bin', '.dat',
    '.lock', '.pack', '.map',
}
# Files with no extension that are known binary
BINARY_BASENAMES = {'.coverage'}


def should_skip(path: Path) -> bool:
    """Check if a file or directory should be skipped."""
    parts = path.parts
    for part in parts:
        if part in SKIP_DIRS:
            return True

    ext = path.suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True
    if ext in BINARY_EXTENSIONS:
        return True
    if path.name in BINARY_BASENAMES:
        return True

    return False


def r1_check_byte_08(path: Path) -> list[str]:
    """R1: Scan for byte 0x08 (backspace)."""
    violations = []
    try:
        with open(path, 'rb') as f:
            data = f.read()
        positions = [i for i, b in enumerate(data) if b == 0x08]
        for pos in positions:
            # Show context: 20 bytes around the offending byte
            start = max(0, pos - 10)
            end = min(len(data), pos + 10)
            ctx = data[start:end]
            violations.append(
                f"  R1: byte 0x08 (backspace) at offset {pos}, "
                f"context bytes: {ctx.hex(' ')}"
            )
    except (OSError, PermissionError) as e:
        violations.append(f"  ERROR reading file: {e}")
    return violations


def r2_check_isolated_cr(path: Path) -> list[str]:
    """R2: Scan for isolated 0x0D (CR not followed by LF)."""
    violations = []
    try:
        with open(path, 'rb') as f:
            data = f.read()
        for i, b in enumerate(data):
            if b == 0x0D:
                # Check if next byte is 0x0A (LF)
                if i + 1 >= len(data) or data[i + 1] != 0x0A:
                    start = max(0, i - 10)
                    end = min(len(data), i + 10)
                    ctx = data[start:end]
                    violations.append(
                        f"  R2: isolated 0x0D (CR without LF) at offset {i}, "
                        f"context bytes: {ctx.hex(' ')}"
                    )
                    # Only report first violation per file to avoid flood
                    break
    except (OSError, PermissionError) as e:
        violations.append(f"  ERROR reading file: {e}")
    return violations


def r3_check_sh_no_lf(path: Path) -> list[str]:
    """R3: .sh files with zero LF bytes AND size > 200 bytes."""
    violations = []
    if path.suffix.lower() != '.sh':
        return violations
    try:
        size = path.stat().st_size
        if size <= 200:
            return violations
        with open(path, 'rb') as f:
            data = f.read()
        lf_count = data.count(0x0A)
        if lf_count == 0:
            violations.append(
                f"  R3: .sh file has 0 LF bytes (size={size} > 200) — likely corruption"
            )
    except (OSError, PermissionError) as e:
        violations.append(f"  ERROR reading file: {e}")
    return violations


def r4_check_line_length(path: Path) -> list[str]:
    """R4: .sh any line > 300; .md line > 300 only inside code fences."""
    violations = []
    ext = path.suffix.lower()

    if ext not in ('.sh', '.md'):
        return violations

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except (OSError, PermissionError) as e:
        violations.append(f"  ERROR reading file: {e}")
        return violations

    if ext == '.sh':
        for lineno, line in enumerate(lines, 1):
            if len(line.rstrip('\n\r')) > 300:
                violations.append(
                    f"  R4: .sh line {lineno} exceeds 300 chars "
                    f"(length={len(line.rstrip())})"
                )
                # Report only first violation per file
                break
    elif ext == '.md':
        in_code_fence = False
        for lineno, line in enumerate(lines, 1):
            stripped = line.rstrip('\n\r')
            # Toggle code fence state on ``` lines
            if stripped.startswith('```'):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence and len(stripped) > 300:
                violations.append(
                    f"  R4: .md code-fence line {lineno} exceeds 300 chars "
                    f"(length={len(stripped)})"
                )
                # Report only first violation per file
                break

    return violations


def scan_repository(root_dir: str) -> int:
    """Scan all files in the repository. Return 0 if clean, 1 if violations."""
    root = Path(root_dir).resolve()
    violations_found = False

    for filepath in sorted(root.rglob('*')):
        if not filepath.is_file():
            continue
        if should_skip(filepath):
            continue

        relpath = filepath.relative_to(root)

        file_violations = []
        file_violations.extend(r1_check_byte_08(filepath))
        file_violations.extend(r2_check_isolated_cr(filepath))
        file_violations.extend(r3_check_sh_no_lf(filepath))
        file_violations.extend(r4_check_line_length(filepath))

        if file_violations:
            violations_found = True
            print(f"{relpath}:")
            for v in file_violations:
                print(v)

    return 1 if violations_found else 0


def main():
    # Default to the repository root (parent of the scripts directory)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    if not repo_root.is_dir():
        print(f"ERROR: Repository root not found: {repo_root}", file=sys.stderr)
        sys.exit(2)

    print(f"Scanning repository: {repo_root}")
    exit_code = scan_repository(str(repo_root))

    if exit_code == 0:
        print("CI content gates: PASSED (no violations)")
    else:
        print("CI content gates: FAILED (violations found)")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
