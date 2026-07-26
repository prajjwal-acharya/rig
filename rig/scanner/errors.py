from __future__ import annotations


class ScannerError(Exception):
    pass


class RepositoryPathNotFoundError(ScannerError):
    pass


class RepositoryPathNotADirectoryError(ScannerError):
    pass
