"""Reject linked output trees before any artifact or sample write."""
import os
from pathlib import Path
import stat


def validate_output_tree(root):
    root=Path(root)
    def inspect(path):
        s=path.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:
            raise ValueError('Linked/reparse output path rejected: '+str(path))
        if stat.S_ISREG(s.st_mode) and s.st_nlink!=1:
            raise ValueError('Multiple-link output file rejected: '+str(path))
    inspect(root)
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:inspect(Path(directory)/name)
