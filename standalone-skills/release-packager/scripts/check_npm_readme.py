#!/usr/bin/env python3
"""Check an npm tarball's README images and reviewed installed Node CLI example.

No packing, installation, lifecycle hooks, shell evaluation or URL fetching.
The caller supplies an isolated consumer installed from these exact bytes.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shlex
import shutil
import signal
import subprocess
import tarfile
import tempfile
from urllib.parse import unquote, urlsplit


class CheckError(ValueError):
    """Verification failed or applicable input is unsupported."""


def require(condition, message):
    if not condition:
        raise CheckError(message)


def payload(artifact):
    with artifact.open("rb") as stream:
        raw = stream.read(64 * 1024 * 1024 + 1)
    require(len(raw) <= 64 * 1024 * 1024, "archive exceeds 64 MiB compressed")
    files = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for index, member in enumerate(archive):
            require(index < 10000, "archive exceeds 10000 entries")
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and path.parts[:1] == ("package",)
                    and ".." not in path.parts and "\\" not in member.name
                    and ":" not in member.name, "unsafe archive path")
            require(member.isfile() or member.isdir(), "archive links/special files are unsupported")
            if member.isdir():
                continue
            name = path.relative_to("package").as_posix()
            require(name not in files, f"duplicate archive file: {name}")
            total += member.size
            require(total <= 64 * 1024 * 1024, "archive exceeds 64 MiB expanded")
            files[name] = archive.extractfile(member).read()
    require("package.json" in files, "missing packaged package.json")
    return files, hashlib.sha256(raw).hexdigest()


def fenced(text):
    """Return prose and fenced blocks; unsupported/unclosed fences fail closed."""
    prose, blocks, lines = [], [], []
    marker = None
    language = ""
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if marker is None and match:
            marker, language = match.groups()
            language = language.strip().lower()
            lines = []
        elif marker and match and match[1][0] == marker[0] and len(match[1]) >= len(marker) and not match[2].strip():
            blocks.append((language, lines))
            marker = None
        elif marker:
            lines.append(line)
        else:
            prose.append(line)
    require(marker is None, "unclosed README code fence")
    return "\n".join(prose), blocks


class ImageHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
        self.pictures = 0
        self.image_tags = 0

    def handle_starttag(self, tag, attrs):
        # Browsers keep the first of duplicated attributes; so does this check.
        values = {}
        for name, value in attrs:
            values.setdefault(name, value)
        if tag in {"img", "picture", "source"}:
            self.image_tags += 1
        if tag == "picture":
            self.pictures += 1
        if tag == "img" or (tag == "source" and (self.pictures or values.get("type", "").startswith("image/"))):
            require(bool(values.get("src") or values.get("srcset")), f"{tag} lacks an image source")
            if "src" in values:
                require(bool(values["src"]), "empty image src")
                self.refs.append(values["src"])
            if "srcset" in values:
                # Data URLs contain commas; leave those for a format-specific check.
                require("data:" not in values["srcset"].lower(), "data srcset is unsupported")
                for candidate in values["srcset"].split(","):
                    parts = candidate.split()
                    require(1 <= len(parts) <= 2 and
                            (len(parts) == 1 or re.fullmatch(r"(?:\d+w|\d+(?:\.\d+)?x)", parts[1])),
                            "unparseable image srcset")
                    self.refs.append(parts[0])

    def handle_endtag(self, tag):
        if tag == "picture":
            self.pictures -= 1
            require(self.pictures >= 0, "unmatched picture close tag")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "picture":
            self.handle_endtag(tag)


DESTINATION = r'(?:<([^<>\n]+)>|([^\s()<>]+))(?:\s+["\'][^\n]*["\'])?'


def image_references(prose):
    html = ImageHTML()
    html.feed(prose)
    html.close()
    require(html.pictures == 0, "unclosed picture tag")
    require(html.image_tags == len(re.findall(r"<(?:img|picture|source)\b", prose, re.I)),
            "unparseable HTML image tag")
    refs = html.refs
    definitions = {}
    for match in re.finditer(r"(?m)^\s*\[([^\]]+)\]:\s*(.+)$", prose):
        target = re.fullmatch(DESTINATION, match[2].strip())
        if target:
            # CommonMark uses the first definition of a repeated label.
            definitions.setdefault(" ".join(match[1].lower().split()), target[1] or target[2])
    # Inline destinations support angle brackets, URL encoding and optional titles.
    pattern = r"!\[([^\]\n]*)\](?:\(([^\n]*?)\)|\[([^\]\n]*)\])?"
    for match in re.finditer(pattern, prose):
        require(not (match[2] is None and match[3] is None and prose[match.end():match.end() + 1] in {"(", "["}),
                "unparseable Markdown image")
        if match[2] is not None:
            target = re.fullmatch(DESTINATION, match[2])
            require(target is not None, "unsupported Markdown image destination")
            refs.append(target[1] or target[2])
        else:
            key = " ".join((match[3] or match[1]).lower().split())
            require(key in definitions, f"unresolved Markdown image reference: {key}")
            refs.append(definitions[key])
    require(prose.count("![") == len(list(re.finditer(pattern, prose))),
            "unparseable Markdown image")
    return refs


def check_images(readme, prose, files):
    local, external = [], []
    for ref in image_references(prose):
        require(bool(ref.strip()), "empty image reference")
        url = urlsplit(ref)
        if url.scheme.lower() in {"https", "http", "data"} or ref.startswith("//"):
            external.append(ref)
            continue
        require(not url.scheme and not url.netloc, "unsupported image URI scheme")
        path = unquote(url.path)
        require(path and not path.startswith("/") and "\\" not in path and ":" not in path,
                f"unsafe local image reference: {ref}")
        name = posixpath.normpath(posixpath.join(posixpath.dirname(readme), path))
        require(not name.startswith("../") and name != "..", "image escapes package")
        require(name in files, f"missing packaged README image: {name}")
        local.append(name)
    return {"local": local, "external_unverified": external}


def package_bins(manifest):
    bins = manifest.get("bin")
    if bins is None or bins == {}:
        directories = manifest.get("directories") or {}
        require(isinstance(directories, dict), "unsupported package directories declaration")
        require(not directories.get("bin"),
                "implicit directories.bin is unsupported; applicable CLI verification is unresolved")
        return {}
    if isinstance(bins, str):
        bins = {manifest["name"].split("/")[-1]: bins}
    require(isinstance(bins, dict) and all(isinstance(k, str) and k and isinstance(v, str) and v
                                         for k, v in bins.items()), "unsupported package bin declaration")
    return bins


def primary_example(blocks, bins):
    examples = []
    for language, lines in blocks:
        for raw in lines:
            line = raw.strip()
            if line.startswith("$ "):
                line = line[2:]
            # No README text becomes executable. Recognize only direct bin calls.
            first = line.split(maxsplit=1)[0] if line else ""
            if first not in bins:
                continue
            require(language in {"sh", "shell", "bash", "console", ""}, "unsupported CLI code fence language")
            # Anything a shell would expand, group or comment out makes the argv differ from what users run.
            require(not re.search(r"[;&|<>$`\\\r\n*?\[\]~#{}()!]", line), "shell syntax in README CLI example")
            try:
                argv = shlex.split(line, posix=True)
            except ValueError as exc:
                raise CheckError("unparseable README CLI example") from exc
            if argv[1:] not in (["--version"], ["--help"], ["-h"], ["-v"]):
                examples.append(argv)
    require(bool(examples), "no supported useful direct CLI example; applicable CLI verification is unresolved")
    return examples[0]


def installed_package(consumer, manifest, files):
    name = manifest.get("name")
    require(isinstance(name, str) and re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]+", name)
            and name not in {".", ".."}, "unsupported package name")
    consumer = consumer.absolute()
    require(consumer.is_dir() and consumer.resolve() == consumer, "consumer must be an isolated real directory")
    package = consumer / "node_modules" / name
    for relative, data in files.items():
        path = package / relative
        require(path.resolve() == path.absolute() and path.is_file(), f"missing or linked installed file: {relative}")
        require(path.read_bytes() == data, f"installed bytes differ from tarball: {relative}")
    return package


def run_example(artifact_hash, review, argv, bins, files, package, consumer, timeout):
    require(isinstance(review, dict) and review.get("artifact_sha256") == artifact_hash,
            "review must bind the actual tarball SHA-256")
    require(review.get("argv") == argv, "reviewed argv differs from primary documented CLI example")
    require(review.get("offline_code_reviewed") is True,
            "review the CLI, dependencies and fixture for offline execution before approving argv")
    require(isinstance(review.get("stdout"), str), "review must specify exact expected stdout")
    binary = posixpath.normpath(bins[argv[0]])
    require(binary in files and not binary.startswith("../"), "missing or unsafe packaged bin")
    require(PurePosixPath(binary).suffix in {".js", ".cjs", ".mjs"}, "only Node JS CLI bins are supported")
    node = shutil.which("node")
    require(node is not None, "Node is required; CLI verification cannot be skipped")
    guard = Path(__file__).with_name("offline_node.cjs").resolve()
    command = [node, "--permission", f"--allow-fs-read={consumer}", f"--allow-fs-read={guard}",
               "--require", str(guard), str(package / binary), *argv[1:]]
    # Do not inherit NODE_OPTIONS, NODE_PATH, proxy credentials or user configuration.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ}
    # `node` can be a version-manager shim that starts the real Node as a child, so the
    # CLI runs in its own process group and a timeout stops the whole tree.
    group = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
             else {"start_new_session": True})
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=consumer, env=env, shell=False, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, **group)
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            stopped = stop_tree(process)
            raise CheckError("documented CLI exceeded its deadline; " + (
                "Node process tree terminated" if stopped else
                "termination of its process tree could not be confirmed")) from exc
        stdout.seek(0)
        stderr.seek(0)
        out, err = stdout.read(65537), stderr.read(65537)
    require(len(out) <= 65536 and len(err) <= 65536, "CLI output exceeds 64 KiB per stream")
    require(returncode == 0, f"documented CLI failed with exit {returncode}: {err.decode('utf-8', 'replace')[-2000:]}")
    require(out.decode("utf-8").replace("\r\n", "\n") == review["stdout"], "documented CLI stdout differs from reviewed expectation")
    return {"status": "passed", "argv": argv, "exit_code": returncode}


def process_rows():
    """{pid: (parent pid, creation time)} of every Windows process; empty when the list cannot be read."""
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "Get-CimInstance Win32_Process | ForEach-Object { '{0} {1} {2}' -f $_.ProcessId, $_.ParentProcessId, "
               "$(if ($_.CreationDate) { $_.CreationDate.ToFileTimeUtc() } else { 0 }) }"]
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False).stdout or ""
    except (OSError, subprocess.SubprocessError):
        return {}
    rows = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            rows[int(parts[0])] = (int(parts[1]), int(parts[2]))
    return rows


def descendants_first(rows, root):
    """``root`` and every process below it, deepest first, from ``process_rows()``.

    Windows keeps a dead parent's id on its children and gives that id to new processes, so `taskkill /T` can reach
    an unrelated program. Here a process is a child only when it started no earlier than its parent, and a root
    missing from the list has no known children."""
    if root not in rows:
        return [root]
    order, frontier = [root], [root]
    while frontier:
        parent = frontier.pop()
        born = rows[parent][1]
        for pid, (ppid, created) in rows.items():
            if ppid == parent and pid not in order and created >= born:
                order.append(pid)
                frontier.append(pid)
    return order[::-1]


PROCESS_TERMINATE, PROCESS_QUERY_LIMITED_INFORMATION, SYNCHRONIZE = 0x0001, 0x1000, 0x00100000
ERROR_INVALID_PARAMETER, STILL_ACTIVE, WAIT_OBJECT_0, END_WAIT_MS = 87, 259, 0, 5000


def windows_kernel32():
    """kernel32 with the calls ``end_process`` makes, typed. A HANDLE is pointer-sized."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle, dword, ok = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
    for name, restype, argtypes in (("OpenProcess", handle, [dword, ok, dword]),
                                    ("GetProcessTimes", ok, [handle] + [ctypes.POINTER(ctypes.c_uint64)] * 4),
                                    ("TerminateProcess", ok, [handle, ctypes.c_uint]),
                                    ("GetExitCodeProcess", ok, [handle, ctypes.POINTER(dword)]),
                                    ("WaitForSingleObject", dword, [handle, dword]),
                                    ("CloseHandle", ok, [handle])):
        function = getattr(kernel32, name)
        function.restype, function.argtypes = restype, argtypes
    return kernel32


def end_process(pid, created, kernel32):
    """Terminate ``pid`` only while it is the process ``process_rows()`` listed as created at ``created``.
    Return whether that process has ended.

    The identity check and the termination use one handle, and Windows gives no process's id to another while a
    handle to it is open. WMI keeps creation times to the microsecond: 10 FILETIME ticks."""
    handle = kernel32.OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
    if not handle:
        return ctypes.get_last_error() == ERROR_INVALID_PARAMETER      # no process has this id any more
    try:
        times = [ctypes.c_uint64() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *map(ctypes.pointer, times)):
            return False
        if abs(times[0].value - created) > 10:
            return times[0].value > created         # a later process has the id: the listed one has ended
        if kernel32.TerminateProcess(handle, 1):        # it starts the end; the wait sees it finish
            return kernel32.WaitForSingleObject(handle, END_WAIT_MS) == WAIT_OBJECT_0
        code = ctypes.c_uint32()                    # TerminateProcess refuses a process that has already exited
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.pointer(code))) and code.value != STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def stop_tree(process):
    """Stop a timed-out CLI and every process it started; return whether that is confirmed.

    The children end through ``end_process``, deepest first. The root is always killed through its Popen handle and
    waited for, whatever happens to the tree stop.
    """
    tree_stopped = False
    try:
        try:
            if os.name == "nt":
                # The root is still alive here, so a list that holds it holds its whole tree.
                rows, kernel32 = process_rows(), windows_kernel32()
                ended = [end_process(pid, rows[pid][1], kernel32) for pid in descendants_first(rows, process.pid)[:-1]]
                tree_stopped = process.pid in rows and all(ended)
            else:
                os.killpg(process.pid, signal.SIGKILL)
                tree_stopped = True
        except (OSError, subprocess.SubprocessError):
            tree_stopped = False
    finally:
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                tree_stopped = False
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        return False
    return tree_stopped


def verify(artifact, consumer, review=None, timeout=10):
    require(0 < timeout <= 60, "timeout must be greater than zero and at most 60 seconds")
    files, digest = payload(artifact)
    manifest = json.loads(files["package.json"].decode("utf-8"))
    require(isinstance(manifest, dict), "package.json must be an object")
    readmes = [name for name in files if re.fullmatch(r"readme(?:\.(?:md|markdown|txt))?", name, re.I)]
    require(len(readmes) == 1, "expected one root README in the npm tarball")
    readme = readmes[0]
    prose, blocks = fenced(files[readme].decode("utf-8-sig"))
    images = check_images(readme, prose, files)
    require(consumer is not None, "supply the isolated installed consumer")
    package = installed_package(consumer, manifest, files)
    bins = package_bins(manifest)
    cli = {"status": "not_applicable", "reason": "package declares no bin; library import verification remains separate"}
    if bins:
        argv = primary_example(blocks, bins)
        cli = run_example(digest, review, argv, bins, files, package, consumer.absolute(), timeout)
    return {"status": "passed", "scope": "npm README local images and applicable Node CLI only",
            "artifact_sha256": digest, "readme": readme, "images": images, "cli": cli}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tarball", required=True, type=Path)
    parser.add_argument("--consumer", required=True, type=Path)
    parser.add_argument("--review", type=Path, help="reviewed JSON: artifact_sha256, argv, stdout, offline_code_reviewed")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    try:
        review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
        report = verify(args.tarball, args.consumer, review, args.timeout)
    except (CheckError, OSError, ValueError, KeyError, TypeError, tarfile.TarError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
