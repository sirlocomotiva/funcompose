#!/usr/bin/env python3
"""Run a 7 Days to Die dedicated server with configs from the funcompose repo.

Commands:
  sdtd run          Install or update the game, apply /config, start the server.
  sdtd cmd <text>   Send one console command to the running server over telnet.

On every start, "run" applies the repo configs that are mounted at /config:
  serverconfig.xml  Your properties are merged over the game's default file.
                    The result is written to /data/serverconfig.xml.
  serveradmin.xml   If present, it replaces the server's admin file.
  Mods/<name>/      Each folder is copied into the game's Mods folder.
                    A mod that you remove from the repo is removed from the server.
  Data/Config/*.xml Your fragments are merged over the game's own tuning files
                    (spawning.xml, gamestages.xml, loot.xml, ...) and the result
                    replaces the game's copy, so the server reads your values.
"""

import copy
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from xml.parsers import expat

SERVER_DIR = "/server"
DATA_DIR = "/data"
CONFIG_DIR = "/config"
HOME_DIR = os.environ.get("HOME", "/home/sdtd")

APP_ID = "294420"
LINUX_DEPOT_ID = "294422"
DEPOT_DOWNLOADER = "/opt/depotdownloader/DepotDownloader"
SERVER_BINARY = "7DaysToDieServer.x86_64"
MANAGED_MODS_FILE = ".funcompose-managed-mods.json"
# The game's own tuning files. The repo mirrors this path under /config.
GAME_CONFIG_SUBDIR = os.path.join("Data", "Config")
# Pristine copies of those files, so a repo edit can be undone by removing it.
ORIGINALS_DIR = os.path.join(DATA_DIR, ".sdtd-originals")
APPLIED_STATE_FILE = "applied.json"
XML_DECLARATION = '''<?xml version="1.0" encoding="UTF-8"?>'''

# The container layout needs these values, so they win over the repo config.
FORCED_PROPERTIES = {
    "UserDataFolder": DATA_DIR,  # saves and generated worlds go to the /data volume
    "TelnetEnabled": "true",  # needed to stop the server cleanly and for "sdtd cmd"
}

STOP_TIMEOUT_SECONDS = 90


def log(message):
    print(f"[sdtd] {message}", flush=True)


def fail(message):
    log(f"ERROR: {message}")
    sys.exit(1)


def env_flag(name, default):
    value = os.environ.get(name, default).strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    fail(f"{name} must be true or false, not {value!r}")


# --- serverconfig.xml -------------------------------------------------------


def parse_xml(path):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    try:
        return ET.parse(path, parser)
    except ET.ParseError as error:
        fail(f"{path} is not valid XML: {error}. Fix the file and restart the container.")


def read_properties(tree, path):
    root = tree.getroot()
    if root.tag != "ServerSettings":
        fail(f"{path}: the root element must be <ServerSettings>, not <{root.tag}>")
    properties = {}
    for element in root.iter("property"):
        name = element.get("name")
        value = element.get("value")
        if not name or value is None:
            fail(f"{path}: every <property> needs a name and a value attribute")
        properties[name] = value
    return properties


def merge_server_config(default_path, overrides_path, output_path):
    """Write the game's default config with the repo properties applied.

    Returns the effective properties.
    """
    tree = parse_xml(default_path)
    root = tree.getroot()
    elements = {element.get("name"): element for element in root.iter("property")}

    overrides = {}
    if os.path.isfile(overrides_path):
        overrides = read_properties(parse_xml(overrides_path), overrides_path)
    else:
        log(f"No {overrides_path}; using the game's default settings.")

    for name, value in overrides.items():
        if name in FORCED_PROPERTIES and value != FORCED_PROPERTIES[name]:
            log(f"WARNING: {name} is managed by the container; ignoring your value {value!r}.")
            continue
        if name not in elements:
            log(f"WARNING: {name} is not in the game's default serverconfig.xml. Check the spelling.")
        set_property(root, elements, name, value)

    for name, value in FORCED_PROPERTIES.items():
        set_property(root, elements, name, value)

    notice = ET.Comment(
        " GENERATED FILE. Do not edit. Edit configs/7dtd/serverconfig.xml in the repo"
        " and restart the container. "
    )
    notice.tail = "\n\n\t"
    root.insert(0, notice)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    log(f"Applied {len(overrides)} setting(s) from {overrides_path} -> {output_path}")
    return {element.get("name"): element.get("value") for element in root.iter("property")}


def set_property(root, elements, name, value):
    element = elements.get(name)
    if element is None:
        if len(root):
            root[-1].tail = "\n\t"
        element = ET.SubElement(root, "property", {"name": name, "value": value})
        element.tail = "\n"
        elements[name] = element
    element.set("value", value)


# --- serveradmin.xml and Mods -----------------------------------------------


def apply_admin_file(config_dir, data_dir, admin_file_name):
    source = os.path.join(config_dir, "serveradmin.xml")
    if not os.path.isfile(source):
        return
    parse_xml(source)  # stop early if the file is broken
    target = os.path.join(data_dir, "Saves", admin_file_name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(source, target)
    log(f"Applied {source} -> {target}")


def sync_mods(config_mods_dir, server_mods_dir):
    """Copy each repo mod folder into the game. Remove repo mods that are gone."""
    os.makedirs(server_mods_dir, exist_ok=True)
    state_path = os.path.join(server_mods_dir, MANAGED_MODS_FILE)

    previous = []
    if os.path.isfile(state_path):
        with open(state_path) as state_file:
            previous = json.load(state_file)

    current = []
    if os.path.isdir(config_mods_dir):
        for name in sorted(os.listdir(config_mods_dir)):
            path = os.path.join(config_mods_dir, name)
            if name.startswith("."):
                continue
            if not os.path.isdir(path):
                log(f"WARNING: skipping {path}: a mod must be a folder. Extract archives first.")
                continue
            current.append(name)

    for name in previous:
        if name not in current:
            shutil.rmtree(os.path.join(server_mods_dir, name), ignore_errors=True)
            log(f"Removed mod {name} (not in the repo anymore)")

    for name in current:
        target = os.path.join(server_mods_dir, name)
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(os.path.join(config_mods_dir, name), target)
        log(f"Installed mod {name}")

    with open(state_path, "w") as state_file:
        json.dump(current, state_file)


# --- Data/Config overlays ----------------------------------------------------

def parse_match(value, tag):
    """Turn match="a=1,b=2" into {"a": "1", "b": "2"}."""
    identity = {}
    for pair in value.split(","):
        pair = pair.strip()
        if not pair:
            continue
        key, sep, val = pair.partition("=")
        if not sep:
            fail(f'<{tag}> has match="{value}": expected match="attr=value,attr=value"')
        identity[key.strip()] = val.strip()
    if not identity:
        fail(f"<{tag}> has an empty match attribute")
    return identity


def identity_of(element):
    """The attributes that pick this element out of its siblings.

    An explicit match="attr=value" always wins. Otherwise name, otherwise id.
    A container with none of those is identified by every attribute it carries,
    because a fragment normally restates only the key. A leaf is not: there its
    attributes are the values to change, so it is identified by being the only
    element of that tag, or by an explicit match.
    """
    if "match" in element.attrib:
        return parse_match(element.attrib["match"], element.tag)
    for key in ("name", "id"):
        if key in element.attrib:
            return {key: element.attrib[key]}
    if len(element):
        return dict(element.attrib)
    return {}


def describe(element, identity):
    shown = ",".join(f'{key}="{value}"' for key, value in identity.items())
    return f"{element.tag}[{shown}]" if shown else element.tag


def locate(parent, child):
    """Find the element of the base file that this overlay element refers to.

    Returns (element_or_None, status) where status is "ok", "missing" or
    "ambiguous".
    """
    identity = identity_of(child)
    # element.tag is a callable for comments, so this also drops them.
    candidates = [element for element in parent if element.tag == child.tag]
    if not candidates:
        return None, "missing"
    if identity:
        matched = [
            element for element in candidates
            if all(element.get(key) == value for key, value in identity.items())
        ]
        if len(matched) == 1:
            return matched[0], "ok"
        if matched:
            return None, "ambiguous"
        return None, "missing"
    if len(candidates) == 1:
        return candidates[0], "ok"
    return None, "ambiguous"


def merge_overlay(base, overlay, path, report, known_tags):
    """Copy values from the overlay fragment into the base tree, in place."""
    for child in overlay:
        if not isinstance(child.tag, str):
            continue  # comment or processing instruction
        identity = identity_of(child)
        here = f"{path} > {describe(child, identity)}"
        target, status = locate(base, child)
        if status == "ambiguous":
            same_tag = len([element for element in base if element.tag == child.tag])
            if identity and "match" not in child.attrib:
                detail = f"({len(same_tag)} <{child.tag}> here, none of them match {identity})"
            else:
                detail = f"({same_tag} <{child.tag}> here, {len(identity)} attribute(s) given)"
            fail(f"{here} is ambiguous in the game's file {detail}. "
                 f'Add more attributes to match="..." so exactly one element matches.')
        if target is None:
            if "match" in child.attrib:
                log(f"WARNING: {here}: nothing in the game's file matches that selector, "
                    "so the element was ADDED. Check the attribute values.")
            elif child.tag not in known_tags:
                log(f"WARNING: {here}: the game's file has no <{child.tag}> element. Check the spelling.")
            base.append(copy.deepcopy(child))
            report["added"].append(here)
            continue
        for key, value in child.attrib.items():
            if key == "match":
                continue
            if target.get(key) != value:
                report["changed"] += 1
                report["touched"].add(here)
                target.set(key, value)
        if len(child):
            merge_overlay(target, child, here, report, known_tags)


def check_written_xml(path):
    """Refuse to leave a file the game could not read."""
    try:
        parse_xml(path)
    except SystemExit:
        fail(f"{path} is not valid XML after merging. Nothing was changed in the repo; "
             "check the WARNING lines above and restart.")


def read_prolog(path):
    """Everything before the root element: the declaration and its comments.

    The offset comes from a real parser, because these files put example XML
    inside the comment in front of the root, so searching for "<" by hand lands
    inside the comment and would truncate it.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    parser = expat.ParserCreate()
    start_at = []

    def on_start_element(_name, _attributes):
        if not start_at:
            start_at.append(parser.CurrentByteIndex)

    parser.StartElementHandler = on_start_element
    try:
        parser.Parse(data, True)
    except expat.ExpatError:
        return XML_DECLARATION + "\n"
    if not start_at:
        return XML_DECLARATION + "\n"
    return data[: start_at[0]].decode("utf-8")


def merge_game_config(base_path, overlay_path, output_path):
    """Write the game's tuning file with the repo fragment applied on top."""
    base_tree = parse_xml(base_path)
    overlay_tree = parse_xml(overlay_path)
    base_root = base_tree.getroot()
    overlay_root = overlay_tree.getroot()
    name = os.path.basename(overlay_path)
    if base_root.tag != overlay_root.tag:
        fail(f"{name}: the root element must be <{base_root.tag}>, not <{overlay_root.tag}>")
    known_tags = {element.tag for element in base_root.iter()}
    report = {"changed": 0, "touched": set(), "added": []}
    merge_overlay(base_root, overlay_root, name, report, known_tags)
    # Serialize the root by hand so the comments in front of it (the file's table
    # of contents) survive, which ET.tostring on the root would drop.
    body = ET.tostring(base_root, encoding="unicode")
    prolog = read_prolog(base_path)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(prolog)
        handle.write(body)
        if not body.endswith("\n"):
            handle.write("\n")
    check_written_xml(output_path)
    parts = [f"{report['changed']} value(s) in {len(report['touched'])} element(s)"]
    if report["added"]:
        parts.append(f"{len(report['added'])} added element(s)")
    log(f"Applied {name}: " + ", ".join(parts) + f" -> {output_path}")


def apply_game_configs(config_dir=CONFIG_DIR, server_dir=SERVER_DIR, data_dir=DATA_DIR):
    """Merge every repo Data/Config fragment over the game's own file.

    A fragment that is deleted from the repo is undone on the next start, because
    the merge always runs against a pristine copy of the file as the game shipped
    it rather than against the previous result.
    """
    overlay_dir = os.path.join(config_dir, GAME_CONFIG_SUBDIR)
    target_dir = os.path.join(server_dir, GAME_CONFIG_SUBDIR)
    originals_dir = os.path.join(data_dir, ORIGINALS_DIR, GAME_CONFIG_SUBDIR)
    overlays = {}
    if os.path.isdir(overlay_dir):
        overlays = {
            name: os.path.join(overlay_dir, name)
            for name in sorted(os.listdir(overlay_dir))
            if name.endswith(".xml") and not name.startswith(".")
        }

    previously_applied = []
    state_path = os.path.join(data_dir, ORIGINALS_DIR, APPLIED_STATE_FILE)
    if os.path.isfile(state_path):
        try:
            with open(state_path) as handle:
                previously_applied = json.load(handle)
        except (OSError, ValueError):
            previously_applied = []

    # Undo fragments that were removed from the repo.
    for name in sorted(set(previously_applied) - set(overlays)):
        original_path = os.path.join(originals_dir, name)
        target_path = os.path.join(target_dir, name)
        if os.path.isfile(original_path) and os.path.isfile(target_path):
            shutil.copyfile(original_path, target_path)
            log(f"Restored the game's own {name} (its repo fragment is gone).")

    applied = []
    for name, overlay_path in overlays.items():
        target_path = os.path.join(target_dir, name)
        if not os.path.isfile(target_path):
            log(f"WARNING: {overlay_path} has no matching file in the game. Check the spelling.")
            continue
        original_path = os.path.join(originals_dir, name)
        if not os.path.isfile(original_path):
            # Keep the file as the game shipped it, so removing the fragment later
            # restores the default instead of leaving the last merge in place.
            os.makedirs(originals_dir, exist_ok=True)
            shutil.copyfile(target_path, original_path)
        merge_game_config(original_path, overlay_path, target_path)
        applied.append(name)

    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w") as handle:
        json.dump(applied, handle, indent=2)


def check_game_configs(config_dir=CONFIG_DIR):
    """Stop before the long game update if a repo fragment is broken XML."""
    overlay_dir = os.path.join(config_dir, GAME_CONFIG_SUBDIR)
    if not os.path.isdir(overlay_dir):
        return
    for name in sorted(os.listdir(overlay_dir)):
        if name.endswith(".xml") and not name.startswith("."):
            parse_xml(os.path.join(overlay_dir, name))


def check_repo_config(config_dir=CONFIG_DIR):
    """Stop before the long game update if a repo config file is broken."""
    config_file = os.path.join(config_dir, "serverconfig.xml")
    if os.path.isfile(config_file):
        read_properties(parse_xml(config_file), config_file)
    admin_file = os.path.join(config_dir, "serveradmin.xml")
    if os.path.isfile(admin_file):
        parse_xml(admin_file)
    check_game_configs(config_dir)


def apply_repo_config(config_dir=CONFIG_DIR, server_dir=SERVER_DIR, data_dir=DATA_DIR):
    default_config = os.path.join(server_dir, "serverconfig.xml")
    if not os.path.isfile(default_config):
        fail(f"{default_config} is missing. Is the game installed? Set SDTD_UPDATE=true.")
    config_file = os.path.join(data_dir, "serverconfig.xml")
    properties = merge_server_config(
        default_config, os.path.join(config_dir, "serverconfig.xml"), config_file
    )
    apply_admin_file(config_dir, data_dir, properties.get("AdminFileName", "serveradmin.xml"))
    sync_mods(os.path.join(config_dir, "Mods"), os.path.join(server_dir, "Mods"))
    apply_game_configs(config_dir, server_dir, data_dir)
    return config_file, properties


# --- telnet -----------------------------------------------------------------


class Telnet:
    """Minimal client for the 7 Days to Die telnet console."""

    READY = "Press 'help' to get a list of all commands"

    def __init__(self, port, password, timeout=10):
        host = "127.0.0.1"
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buffer = ""
        text = self.read_until([self.READY, "Please enter password:"], timeout)
        if "Please enter password:" in text:
            self.send(password)
            self.read_until([self.READY], timeout)

    def read_until(self, patterns, timeout):
        deadline = time.monotonic() + timeout
        while not any(pattern in self.buffer for pattern in patterns):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"no {patterns[0]!r} from the telnet console")
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("the telnet console closed the connection")
            self.buffer += chunk.decode("utf-8", errors="replace")
        text, self.buffer = self.buffer, ""
        return text

    def read_for(self, seconds):
        deadline = time.monotonic() + seconds
        output = self.buffer
        self.buffer = ""
        while time.monotonic() < deadline:
            self.sock.settimeout(max(deadline - time.monotonic(), 0.01))
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            output += chunk.decode("utf-8", errors="replace")
        return output

    def send(self, line):
        self.sock.sendall(line.encode("utf-8") + b"\n")

    def close(self):
        try:
            self.send("exit")
        except OSError:
            pass
        self.sock.close()


def telnet_settings():
    properties = {}
    config_file = os.path.join(DATA_DIR, "serverconfig.xml")
    if os.path.isfile(config_file):
        properties = read_properties(parse_xml(config_file), config_file)
    return int(properties.get("TelnetPort", "8081")), properties.get("TelnetPassword", "")


def command(args):
    if not args:
        fail('usage: sdtd cmd "<console command>"')
    port, password = telnet_settings()
    try:
        console = Telnet(port, password)
    except (OSError, TimeoutError) as error:
        fail(f"cannot reach the server console on port {port}: {error}")
    console.send(" ".join(args))
    print(console.read_for(3).strip())
    console.close()


# --- install and run --------------------------------------------------------


def check_cpu():
    """Stop before the 14 GB download if x86_64 is only emulated (for example on Apple Silicon).

    The game's Mono runtime aborts under Rosetta and QEMU:
    "Assertion at ../../mono/arch/amd64/../x86/x86-codegen.h:410".
    """
    if env_flag("SDTD_ALLOW_EMULATION", "false"):
        return
    try:
        with open("/proc/cpuinfo") as cpuinfo_file:
            cpuinfo = cpuinfo_file.read()
    except OSError:
        return
    if "VirtualApple" in cpuinfo or "CPU implementer" in cpuinfo:
        fail("This host runs x86_64 programs with emulation (for example Apple Silicon or another ARM CPU). "
             "The 7 Days to Die server crashes in emulation. Run this service on an x86_64 host. "
             "To try anyway, set SDTD_ALLOW_EMULATION=true.")


def drop_privileges():
    """Run as PUID:PGID so files in the bind mounts belong to the host user."""
    if os.getuid() != 0:
        return
    uid = int(os.environ.get("PUID", "1000"))
    gid = int(os.environ.get("PGID", "1000"))
    if uid == 0:
        return
    for path in (SERVER_DIR, DATA_DIR, HOME_DIR):
        os.makedirs(path, exist_ok=True)
        stat = os.stat(path)
        if (stat.st_uid, stat.st_gid) != (uid, gid):
            subprocess.run(["chown", "-R", f"{uid}:{gid}", path], check=True)
    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)
    log(f"Running as uid {uid}, gid {gid}")


class Runner:
    """Start child processes and stop them cleanly on SIGTERM or SIGINT."""

    def __init__(self):
        self.child = None
        self.stopping = False
        self.kill_at = None
        self.telnet = None  # (port, password) once the game server is running
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGINT, self.on_signal)

    def on_signal(self, signum, frame):
        if self.stopping:
            return
        self.stopping = True
        log(f"Received {signal.Signals(signum).name}; stopping.")
        if self.child is None or self.child.poll() is not None:
            sys.exit(0)
        self.kill_at = time.monotonic() + STOP_TIMEOUT_SECONDS
        if self.telnet and self.shutdown_over_telnet():
            return
        self.child.terminate()

    def shutdown_over_telnet(self):
        port, password = self.telnet
        for _ in range(3):
            try:
                console = Telnet(port, password, timeout=5)
                console.send("shutdown")
                console.close()
                log("Sent 'shutdown' to the server. Waiting for it to save and exit.")
                return True
            except (OSError, TimeoutError) as error:
                log(f"Telnet shutdown failed ({error}); trying again.")
                time.sleep(2)
        return False

    def run(self, args, output_filter=None, **kwargs):
        if output_filter:
            kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        # A new session keeps a terminal Ctrl-C from reaching the child directly.
        self.child = subprocess.Popen(args, start_new_session=True, **kwargs)
        reader = None
        if output_filter:
            reader = threading.Thread(target=output_filter, args=(self.child.stdout,), daemon=True)
            reader.start()
        while True:
            try:
                code = self.child.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                if self.kill_at is not None and time.monotonic() > self.kill_at:
                    log("The process did not stop in time; killing it.")
                    self.child.kill()
                    self.kill_at = None
        if reader:
            reader.join(timeout=5)
        return code


def print_download_progress(stream):
    """DepotDownloader prints two lines for each of about 17,000 files. Keep the log short."""
    last_progress = 0.0
    for line in stream:
        line = line.rstrip()
        if line.startswith("Pre-allocating"):
            continue
        match = re.match(r"\s*(\d+\.\d+)% ", line)
        if match:
            if time.monotonic() - last_progress < 30:
                continue
            last_progress = time.monotonic()
            line = f"Download progress: {match.group(1)}%"
        print(line, flush=True)


def install_game(runner):
    branch = os.environ.get("SDTD_BRANCH", "public").strip() or "public"
    installed = os.path.isfile(os.path.join(SERVER_DIR, SERVER_BINARY))
    if installed and not env_flag("SDTD_UPDATE", "true"):
        log("SDTD_UPDATE=false; skipping the update check.")
        return
    if installed:
        log(f"Checking for game updates (branch {branch}).")
    else:
        log(f"Installing the game (branch {branch}). This downloads about 14 GB.")
    args = [DEPOT_DOWNLOADER, "-app", APP_ID, "-depot", LINUX_DEPOT_ID,
            "-branch", branch, "-dir", SERVER_DIR]
    if env_flag("SDTD_VALIDATE", "false"):
        args.append("-validate")
    code = runner.run(args, output_filter=print_download_progress)
    if runner.stopping:
        sys.exit(0)
    if code != 0:
        fail(f"DepotDownloader failed with exit code {code}")
    os.chmod(os.path.join(SERVER_DIR, SERVER_BINARY), 0o755)


def run():
    check_cpu()
    drop_privileges()
    check_repo_config()
    runner = Runner()
    install_game(runner)
    config_file, properties = apply_repo_config()
    runner.telnet = (int(properties.get("TelnetPort", "8081")), properties.get("TelnetPassword", ""))
    log(f"Starting the server. Game port {properties.get('ServerPort')}.")
    code = runner.run(
        [f"./{SERVER_BINARY}", "-logfile", "-", "-quit", "-batchmode", "-nographics",
         "-dedicated", f"-configfile={config_file}"],
        cwd=SERVER_DIR,
        env={**os.environ, "LD_LIBRARY_PATH": "."},
    )
    log(f"The server exited with code {code}.")
    sys.exit(0 if runner.stopping else code)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "cmd"):
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "run":
        run()
    else:
        command(sys.argv[2:])


if __name__ == "__main__":
    main()
