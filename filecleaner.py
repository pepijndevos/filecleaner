from pathlib import Path
from shutil import rmtree
import argparse
from collections import namedtuple
from datetime import datetime, timedelta

class PackageManager:
    def owning_packages(self, path):
        "Returns the package which provides path, or None"
        []

class Pacman(PackageManager):
    def __init__(self, root="/", db="/var/lib/pacman"):
        import pyalpm
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

def file_prompt(path):
    response = input("What to do [d/i/s/l/p]: ")
    if response == 'd':
        input("confirm delete")
        rmtree(path)
    elif response == 'i':
        with open('ignorelist.txt', 'a') as f:
            f.write('\n')
            f.write(str(path))
    elif response == 's':
        return
    elif response == 'p':
        print(path.parent)
        file_prompt(path.parent)
    elif response == 'l':
        for p in path.iterdir():
            print(p)
        file_prompt(path)
    else:
        file_prompt(path)
    

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
            and t.size > bytes
            and not t.packages)
    files = sorted(files, key=lambda f: f.size, reverse=True)
    for f in files:
        print(f.name, f.size/1e9, "GB")
        file_prompt(f.name)
    print(sum(f.size for f in files)/1e9, "GB")

def old_packages(tree, days=365):
    for pkg, atime in tree.packages.items():
        if datetime.now()-atime > timedelta(days):
            print(pkg, atime)

def package_manager(name):
    if name == "none":
        return PackageManager()
    elif name == "pacman":
        return Pacman()
    else:
        raise KeyError(name)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Find unused files')
    parser.add_argument('--root', type=Path, default="/", help='the root directory to scan')
    parser.add_argument('--days', metavar='N', type=int, default=365, help='filter directories older than N days')
    parser.add_argument('--pkg-days', metavar='N', type=int, default=365, help='filter packages older than N days')
    # float to allow exponential notation
    parser.add_argument('--size', metavar='BYTES', type=float, default=1e8, help='filter directories larger than BYTES')
    parser.add_argument('--ignore', metavar='PATH', nargs='+', help='Ignore files under PATH')
    parser.add_argument('--ignore-file', metavar='FILE', type=argparse.FileType('r+'), default="ignorelist.txt", help='Ignore files listed in FILE')
    parser.add_argument('--package-manager', type=package_manager, default="none", help='Ignore files listed in FILE')

    args = parser.parse_args()
    print(args)

    ignores = args.ignore or []
    if args.ignore_file:
        for line in args.ignore_file:
            ignores.append(line.strip())

    p = path_tree(args.package_manager, args.root, ignores)
    old_dirs(p, args.days, args.size)
    old_packages(p, args.pkg_days)
