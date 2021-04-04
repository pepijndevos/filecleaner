from pathlib import Path
import argparse
from abc import ABC, abstractmethod
import pyalpm
from collections import namedtuple
from datetime import datetime, timedelta

class PackageManager(ABC):
    @abstractmethod
    def owning_packages(self, path):
        "Returns the package which provides path, or None"
        pass

class Alpm(PackageManager):
    def __init__(self, root="/", db="/var/lib/pacman"):
        self.handle = pyalpm.Handle(root, db)

        self.path_table = {}
        localpkgs = self.handle.get_localdb().pkgcache
        for pkg in localpkgs:
            files = pkg.files
            for name, size, mode in files:
                path = Path(root) / name
                self.path_table.setdefault(path, []).append(pkg.name)

    def owning_packages(self, path):
        return self.path_table.get(path, [])

def path_match(patterns, path):
    return any(path.is_relative_to(p) for p in patterns)

Tree = namedtuple("Tree", ["name", "atime", "size", "children", "packages"])

def merge(d, o, f=max):
    for k, v in o.items():
        if k in d:
            d[k] = f(d[k], v)
        else:
            d[k] = v
    return d

def path_tree(mgr, root, ignores):
    if root.is_symlink(): # don't follow
        time = datetime.fromtimestamp(0)
        size = 0
        return Tree(root, time, size, [], {})
    if root.is_dir():
        atime = datetime.fromtimestamp(0)
        size = 0
        children = []
        pkgs = {}
        try:
            for f in root.iterdir():
                if path_match(ignores, root): continue
                sub = path_tree(mgr, f, ignores)
                atime = max(atime, sub.atime)
                size += sub.size
                merge(pkgs, sub.packages)
                children.append(sub)
        except PermissionError:
            pass
        return Tree(root, atime, size, children, pkgs)
    elif root.is_file():
        st = root.stat()
        time = datetime.fromtimestamp(st.st_atime)
        size = st.st_size
        pkgs = {p: time for p in mgr.owning_packages(root)}
        return Tree(root, time, size, [], pkgs)
    else: # some weird fifo socket thing
        time = datetime.fromtimestamp(0)
        size = 0
        return Tree(root, time, size, [], {})

def apply_filter(tree, f):
    "Return subtrees maching f(tree)"
    if f(tree):
        yield tree
    else:
        for t in tree.children:
            yield from apply_filter(t, f)

def old_dirs(tree, days=365, bytes=1e8):
    files = apply_filter(tree,
        lambda t:
            datetime.now()-t.atime > timedelta(days)
            and t.name.is_dir()
            and t.size > bytes)
    files = sorted(files, key=lambda f: f.size, reverse=True)
    for f in files:
        print(f.name, f.size/1e9, "GB")
    print(sum(f.size for f in files)/1e9, "GB")

def old_packages(tree, days=365):
    for pkg, atime in tree.packages.items():
        if datetime.now()-atime > timedelta(days):
            print(pkg, atime)


ignores = [
    # "/home",
    "/sys",
    "/dev",
    "/proc",
    "/boot",
    "/tmp",
    "/run"
]

if __name__ == "__main__":
    p = path_tree(Alpm(), Path("/"), ignores)
    old_dirs(p)
    old_packages(p)
