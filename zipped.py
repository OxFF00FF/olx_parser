import os
import zipfile
from datetime import datetime
from pathlib import Path
from fnmatch import fnmatch
from main import __version__


def load_gitignore_patterns(gitignore_path=".gitignore"):
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns

    with open(gitignore_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)

    patterns.append(".git/")
    return patterns


def is_ignored(path, patterns):
    rel_path = str(path).replace("\\", "/")
    for pattern in patterns:
        if pattern.endswith("/"):
            if rel_path.startswith(pattern.rstrip("/")):
                return True
        elif fnmatch(rel_path, pattern):
            return True
        elif fnmatch(os.path.basename(rel_path), pattern):
            return True
    return False


def zip_directory(output_zip="archive.zip", exclude_patterns=None, folder_prefix="project"):
    if exclude_patterns is None:
        exclude_patterns = []

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk("."):
            foldername = Path(foldername).as_posix()
            if is_ignored(foldername, exclude_patterns) and foldername != ".":
                subfolders[:] = []
                continue

            if '__pycache__' in foldername:
                continue

            for filename in filenames:
                filepath = Path(foldername, filename).as_posix()
                if filepath == output_zip:
                    continue
                if is_ignored(filepath, exclude_patterns):
                    continue

                # Добавляем корневую папку в пути внутри архива
                arcname = Path(folder_prefix) / Path(filepath)
                zipf.write(filepath, arcname=arcname.as_posix())


if __name__ == "__main__":
    ignore_patterns = load_gitignore_patterns()
    current_date = datetime.now().strftime("%d_%m_%Y")
    folder_name = f"olx_{current_date}"
    archive_name = f"olx_parser-master_{__version__}.zip"

    zip_directory(output_zip=archive_name, exclude_patterns=ignore_patterns, folder_prefix=folder_name)
