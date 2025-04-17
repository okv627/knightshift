import os
import re
import shutil
from pathlib import Path

# Get the folder this script is in
SOURCE_DIR = Path(__file__).resolve().parent

# Store output one level *above* to avoid recursive copying
DEST_DIR = SOURCE_DIR.parent / "stripped_code_output"

# File types to process
INCLUDE_EXTENSIONS = [
    ".py",
    ".yml",
    ".yaml",
    ".sql",
    ".sh",
    ".dockerfile",
    ".env",
    ".md",
]

# Regex patterns for stripping comments by file type
COMMENT_PATTERNS = {
    ".py": r"#.*?$",
    ".yml": r"#.*?$",
    ".yaml": r"#.*?$",
    ".sql": r"--.*?$",
    ".sh": r"#.*?$",
    ".dockerfile": r"#.*?$",
    ".env": r"#.*?$",
    # .md is intentionally excluded from comment stripping
}


def strip_comments(file_path: Path, file_type: str):
    """Remove comment lines or inline comments from a file based on its type."""
    pattern = COMMENT_PATTERNS.get(file_type, "")
    try:
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"Skipping unreadable file (Unicode error): {file_path}")
        return []

    stripped = []
    for line in lines:
        # Strip comments unless it's a markdown file
        line_no_comment = (
            re.sub(pattern, "", line).rstrip() if file_type != ".md" else line
        )
        if line_no_comment.strip() != "":
            stripped.append(line_no_comment + "\n")
    return stripped


def main():
    # Remove previous output folder if it exists
    if DEST_DIR.exists():
        print(f"🧹 Removing existing output at {DEST_DIR}")
        shutil.rmtree(DEST_DIR)
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    for path in SOURCE_DIR.rglob("*"):
        # Skip folders and the output directory itself
        if not path.is_file() or DEST_DIR in path.parents:
            continue

        # Filter by extension
        if path.suffix.lower() not in INCLUDE_EXTENSIONS:
            continue

        rel_path = path.relative_to(SOURCE_DIR)
        dest_path = DEST_DIR / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy markdowns unchanged, clean the rest
        cleaned_lines = strip_comments(path, path.suffix.lower())
        dest_path.write_text("".join(cleaned_lines), encoding="utf-8")
        print(f"Processed: {rel_path}")

    print(f"\nDone! Cleaned files are saved to: {DEST_DIR.resolve()}")


if __name__ == "__main__":
    main()
