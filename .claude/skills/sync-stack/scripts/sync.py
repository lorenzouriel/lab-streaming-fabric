#!/usr/bin/env python3
"""Sync commands/skills of a project's .claude/ from the master-claude GitHub repo.

Plan (default, read-only) -> --apply (safe changes only) -> --take PATH (resolve a conflict with upstream).
State lives in <dest>/.master-claude-sync.json (last synced commit + upstream hash per file).
"""
import argparse
import datetime
import difflib
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

DEFAULT_REPO = "https://github.com/lorenzouriel/master-claude.git"
UPSTREAM_SUBDIR = "engineer/.claude"
MANIFEST = ".master-claude-sync.json"
SCOPES = ("skills", "commands")  # hard-coded: agents, kb, sdd, settings are never synced
SKIP_NAMES = {".DS_Store", "__pycache__"}


def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        sys.exit("git error: %s\n%s" % (" ".join(cmd), p.stderr.decode("utf-8", "replace")))
    return p.stdout


def norm(data):
    return data.replace(b"\r\n", b"\n")


def digest(data):
    return hashlib.sha256(norm(data)).hexdigest()


def read(path):
    with open(path, "rb") as f:
        return f.read()


def list_files(root, scopes):
    out = {}
    for scope in scopes:
        base = os.path.join(root, scope)
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d not in SKIP_NAMES]
            for fn in fns:
                if fn in SKIP_NAMES or fn.endswith(".pyc"):
                    continue
                full = os.path.join(dp, fn)
                out[os.path.relpath(full, root).replace(os.sep, "/")] = full
    return out


def history_hashes(clone, rel):
    """Hashes of every historical upstream version of a file (first-sync base detection)."""
    path = UPSTREAM_SUBDIR + "/" + rel
    shas = run(["git", "log", "--format=%H", "--", path], cwd=clone).decode().split()
    hashes = set()
    for sha in shas:
        p = subprocess.run(["git", "show", "%s:%s" % (sha, path)], cwd=clone,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            hashes.add(digest(p.stdout))
    return hashes


def archived(dest, rel):
    arch = os.path.join(dest, "_archive")
    if not os.path.isdir(arch):
        return False
    for d in os.listdir(arch):
        if os.path.exists(os.path.join(arch, d, *rel.split("/"))):
            return True
    return False


def ignored(rel, patterns):
    return any(fnmatch.fnmatch(rel, p) for p in patterns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("MASTER_CLAUDE_REPO", DEFAULT_REPO))
    ap.add_argument("--ref", default=None, help="branch/tag/commit (default: remote HEAD)")
    ap.add_argument("--dest", default=".claude")
    ap.add_argument("--apply", action="store_true", help="apply adds + safe updates")
    ap.add_argument("--add-new", action="store_true", help="first sync: also install files missing locally")
    ap.add_argument("--prune", action="store_true", help="delete files removed upstream (only if unmodified locally)")
    ap.add_argument("--take", nargs="*", default=[], metavar="PATH", help="overwrite conflicted files with upstream (backed up)")
    ap.add_argument("--diff", nargs="*", default=[], metavar="PATH", help="show local->upstream diff")
    args = ap.parse_args()

    dest = os.path.abspath(args.dest)
    if not os.path.isdir(dest):
        sys.exit("No %s directory. Run from the project root." % args.dest)
    if os.path.isdir(os.path.join(os.path.dirname(dest), "engineer", ".claude")):
        sys.exit("Refusing: this looks like the master-claude source repo, not a consumer project.")
    scopes = list(SCOPES)

    manifest_path = os.path.join(dest, MANIFEST)
    manifest = {"repo": args.repo, "commit": None, "files": {}, "ignore": []}
    bootstrap = True
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest.update(json.load(f))
        bootstrap = False
    known = manifest["files"]
    ignore = manifest.get("ignore", [])

    tmp = tempfile.mkdtemp(prefix="master-claude-sync-")
    try:
        clone = os.path.join(tmp, "src")
        run(["git", "-c", "core.autocrlf=false", "clone", "--quiet", "--no-tags", args.repo, clone])
        if args.ref:
            run(["git", "checkout", "--quiet", args.ref], cwd=clone)
        commit = run(["git", "rev-parse", "HEAD"], cwd=clone).decode().strip()
        up_root = os.path.join(clone, *UPSTREAM_SUBDIR.split("/"))
        if not os.path.isdir(up_root):
            sys.exit("%s not found in %s" % (UPSTREAM_SUBDIR, args.repo))

        up = list_files(up_root, scopes)
        local = list_files(dest, scopes)
        up_hash = {r: digest(read(p)) for r, p in up.items()}

        plan = {"add": [], "update": [], "conflict": [], "stale": [], "keep_local": [],
                "skipped": [], "unchanged": 0}
        new_known = dict(known)

        for rel in sorted(up):
            if ignored(rel, ignore):
                continue
            U = up_hash[rel]
            M = known.get(rel)
            if rel not in local:
                if rel in known:
                    plan["skipped"].append((rel, "removed/pruned locally"))
                elif archived(dest, rel):
                    plan["skipped"].append((rel, "archived by prune-stack"))
                    new_known[rel] = U
                elif bootstrap and not args.add_new:
                    plan["skipped"].append((rel, "not installed (use --add-new to install)"))
                    new_known[rel] = U
                else:
                    plan["add"].append(rel)
                continue
            L = digest(read(local[rel]))
            if L == U:
                plan["unchanged"] += 1
                new_known[rel] = U
            elif M is not None:
                if L == M:
                    plan["update"].append(rel)
                elif U == M:
                    plan["keep_local"].append(rel)
                else:
                    plan["conflict"].append((rel, "both changed"))
            else:
                if L in history_hashes(clone, rel):
                    plan["update"].append(rel)
                else:
                    plan["conflict"].append((rel, "differs, base unknown"))

        for rel in sorted(known):
            if rel in up or ignored(rel, ignore) or not any(rel.startswith(s + "/") for s in scopes):
                continue
            if rel in local:
                same = digest(read(local[rel])) == known[rel]
                plan["stale"].append((rel, "unmodified" if same else "modified locally"))
            else:
                new_known.pop(rel, None)

        rc = 0
        conflict_paths = set(i[0] for i in plan["conflict"])

        for rel in args.diff:
            if rel in up and rel in local:
                a = norm(read(local[rel])).decode("utf-8", "replace").splitlines()
                b = norm(read(up[rel])).decode("utf-8", "replace").splitlines()
                sys.stdout.write("\n".join(difflib.unified_diff(
                    a, b, "local/" + rel, "upstream/" + rel, lineterm="")) + "\n")
            else:
                print("no diff for %s" % rel)

        def put(rel):
            target = os.path.join(dest, *rel.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(up[rel], target)

        backup_dir = os.path.join(dest, "_sync-backup", datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

        def backup(rel):
            src = os.path.join(dest, *rel.split("/"))
            if os.path.exists(src):
                dst = os.path.join(backup_dir, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)

        applied = []
        if args.apply:
            for rel in plan["add"] + plan["update"]:
                put(rel)
                new_known[rel] = up_hash[rel]
                applied.append(rel)
            if args.prune:
                for rel, why in plan["stale"]:
                    if why == "unmodified":
                        os.remove(os.path.join(dest, *rel.split("/")))
                        new_known.pop(rel, None)
                        applied.append("-" + rel)
            for rel in plan["keep_local"]:
                new_known[rel] = up_hash[rel]
        for rel in args.take:
            if rel not in up:
                print("unknown upstream path: %s" % rel)
                rc = 1
                continue
            backup(rel)
            put(rel)
            new_known[rel] = up_hash[rel]
            conflict_paths.discard(rel)
            applied.append(rel + " (taken upstream)")

        old = manifest.get("commit")
        print("repo:     %s" % args.repo)
        print("upstream: %s%s" % (commit[:8], " (was %s)" % old[:8] if old else " (first sync)"))
        if old:
            log = run(["git", "log", "--oneline", "%s..%s" % (old, commit), "--"]
                      + [UPSTREAM_SUBDIR + "/" + s for s in scopes], cwd=clone, check=False).decode().strip()
            if log:
                print("\nupstream commits touching %s:\n%s" % (", ".join(scopes), log))
        for key, label in (("add", "NEW upstream"), ("update", "UPDATE (local unmodified)"),
                           ("conflict", "CONFLICT (local edits + upstream change)"),
                           ("keep_local", "KEEP (local-only edits, upstream unchanged)"),
                           ("stale", "REMOVED upstream"), ("skipped", "SKIPPED")):
            items = plan[key]
            if items:
                print("\n%s [%d]" % (label, len(items)))
                for i in items:
                    print("  %s" % (("%s  -- %s" % i) if isinstance(i, tuple) else i))
        print("\nunchanged: %d" % plan["unchanged"])
        if applied:
            print("\nAPPLIED [%d]" % len(applied))
            for a in applied:
                print("  %s" % a)
            if os.path.isdir(backup_dir):
                print("backups: %s" % backup_dir)
        elif not args.apply and (plan["add"] or plan["update"]):
            print("\nDry run. Re-run with --apply to write NEW + UPDATE.")
        if conflict_paths:
            print("\n%d conflict(s) untouched. Inspect: --diff PATH; take upstream: --take PATH"
                  % len(conflict_paths))

        if args.apply or args.take:
            for rel in conflict_paths:
                if rel in known:
                    new_known[rel] = known[rel]
                else:
                    new_known.pop(rel, None)
            manifest.update({"repo": args.repo, "commit": commit, "files": new_known})
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2, sort_keys=True)
                f.write("\n")
        return rc
    finally:
        def _rm(func, path, exc):
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(tmp, onerror=_rm)


if __name__ == "__main__":
    sys.exit(main())
