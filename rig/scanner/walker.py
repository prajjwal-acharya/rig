from __future__ import annotations

import os
from pathlib import Path

from rig.scanner.models import DiscoveredDirectory, DiscoveredFile, FileWalkResult


class FileWalker:
    # No entries are filtered here (including .git) - that's the Ignore Engine's job.
    def walk(self, root: Path | str) -> FileWalkResult:
        root_path = Path(root).resolve()
        directories: list[DiscoveredDirectory] = []
        files: list[DiscoveredFile] = []

        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
            dirnames.sort()
            filenames.sort()
            current_dir = Path(dirpath)

            for dirname in dirnames:
                relative = (current_dir / dirname).relative_to(root_path)
                directories.append(DiscoveredDirectory(relative_path=relative))

            for filename in filenames:
                relative = (current_dir / filename).relative_to(root_path)
                files.append(DiscoveredFile(relative_path=relative))

        directories.sort(key=lambda d: d.relative_path.as_posix())
        files.sort(key=lambda f: f.relative_path.as_posix())
        return FileWalkResult(root=root_path, directories=directories, files=files)


def walk_repository(root: Path | str) -> FileWalkResult:
    return FileWalker().walk(root)
