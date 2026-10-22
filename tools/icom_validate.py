#!/usr/bin/env python3
"""Check the Laputka ICOM book and the sample messages in this repo.

Usage:
  python3 tools/icom_validate.py
  python3 tools/icom_validate.py --icx /path/to/icx/examples/codebook.yaml

Exit 0 when the book, the sample lines, and the public-file scan are clean.
Exit 1 with one error per line otherwise. Needs PyYAML.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

VERBS = ["GO", "HOLD", "DONE", "BLOCKED", "REC", "FYI", "ASK", "ACK", "NAK"]
PRIORITIES = ["P0", "P1", "P2", "P3"]
COMPTROLLERS = ["CLAP", "CILL", "CCLR", "CWAT", "CMON", "CPRE", "CBIG", "CFUN", "CWES"]
TRAVEL = ["FLT", "HTL", "CAR", "REST", "TRV"]
ROSTER = [
    "MARIAG", "JEN", "GAUNT", "POLL", "ICOM", "CTO", "TEAMS", "CFO",
    *COMPTROLLERS, "TRAV", *TRAVEL,
]
AGENTS = ROSTER
PILOT = ["MARIAG", "JEN", "GAUNT", "ICOM"]
SEG = re.compile(r"^[a-z][a-z0-9]{0,5}$")
CODE = r"[A-Z][A-Z0-9]{0,5}"
ADDR = rf"{CODE}(?:,{CODE})*"
TAIL = (
    r"P(?P<pri>[0-3]) (?P<lane>[A-Z0-9]{1,6})(?: #(?P<ticket>T-\d+))? "
    r"(?P<verb>GO|HOLD|DONE|BLOCKED|REC|FYI|ASK|ACK|NAK)\b(?P<rest>.*)$"
)
# Assistants route through ICOM. A line ICOM itself sends is @ICOM>TO, with no extra hop.
ROUTED = re.compile(rf"@(?P<frm>{CODE})>ICOM>(?P<to>{ADDR}) {TAIL}")
DIRECT = re.compile(rf"@ICOM>(?P<to>{ADDR}) {TAIL}")
CONCRETE = re.compile(rf"@{CODE}>(?:ICOM>)?{ADDR} P[0-3] ")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\w)(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\w)")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
LONG_DIGITS = re.compile(r"\b\d{13,}\b")
SECRET_ASSIGN = re.compile(r"(?i)\b(api[_-]?key|password|secret|token)\s*[:=]\s*\S+")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")

SKIP_DIRS = {".git", "__pycache__"}


def load_book(path):
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("codebook root is not a map")
    return data


def topic_ok(topic, objects, facets):
    base, sep, facet = topic.partition("~")
    if sep and (not facet or "~" in facet):
        return False
    parts = base.split(".")
    if base in objects:
        pass
    elif len(parts) == 2 and parts[0] == "x" and SEG.match(parts[1]):
        pass
    else:
        return False
    if not facet:
        return True
    if facet in facets:
        return True
    head, dot, tail = facet.partition(".")
    if dot and f"{head}.*" in facets and re.fullmatch(r"[a-z0-9]{1,6}(?:\.[a-z0-9]{1,6})*", tail):
        return True
    return False


def check_objects(objects, facets, errors, label="objects"):
    if not isinstance(objects, dict) or not objects:
        errors.append(f"{label}: missing")
        return
    for code in objects:
        segs = code.split(".")
        if len(segs) > 4:
            errors.append(f"{label}: too deep: {code}")
        for seg in segs:
            if not SEG.match(seg):
                errors.append(f"{label}: bad segment in {code}")
        for i in range(1, len(segs)):
            parent = ".".join(segs[:i])
            if parent not in objects:
                errors.append(f"{label}: missing parent {parent} for {code}")
    for facet in facets:
        head = facet.split(".")[0]
        if not SEG.match(head):
            errors.append(f"bad facet: {facet}")


def parse_message(text):
    """Return (msg, error). msg is a dict when error is None."""
    raw = text.strip().strip("`")
    routed = ROUTED.match(raw)
    direct = DIRECT.match(raw)
    if routed:
        m = routed
        frm = m.group("frm")
        if frm == "ICOM":
            return None, "ICOM's own line has no extra hop"
    elif direct:
        m = direct
        frm = "ICOM"
    else:
        return None, "not a message"
    rest = m.group("rest").strip()
    if '"' in rest or "'" in rest:
        return None, "quoted prose"
    tokens = rest.split()
    verb = m.group("verb")
    action = None
    if tokens and verb == "REC" and tokens[0] in VERBS:
        action = tokens.pop(0)
    if not tokens:
        return None, "missing topic"
    topic = tokens.pop(0)
    if "=" in topic:
        return None, "missing topic"
    kvs = {}
    for tok in tokens:
        if "=" not in tok:
            return None, f"prose token {tok}"
        key, value = tok.split("=", 1)
        if not key or not value or key in kvs:
            return None, f"bad field {tok}"
        kvs[key] = value
    recipients = m.group("to").split(",")
    return {
        "frm": frm,
        "to": recipients,
        "pri": "P" + m.group("pri"),
        "lane": m.group("lane"),
        "ticket": m.group("ticket"),
        "verb": verb,
        "action": action,
        "topic": topic,
        "kv": kvs,
        "raw": text.strip().strip("`"),
    }, None


def check_message(msg, book, where):
    errors = []
    agents = book["agents"]
    objects = book["objects"]
    facets = book["facets"]
    fields = book["fields"]
    if msg["frm"] not in agents:
        errors.append(f"{where}: unknown sender {msg['frm']}")
    for rec in msg["to"]:
        if rec not in agents:
            errors.append(f"{where}: unknown recipient {rec}")
    if msg["lane"] not in book["clients"]:
        errors.append(f"{where}: unknown lane {msg['lane']}")
    if msg["pri"] not in book["priority"]:
        errors.append(f"{where}: unknown priority {msg['pri']}")
    if msg["ticket"] is None and not (msg["verb"] == "NAK" and msg["kv"].get("why") == "no-ticket"):
        errors.append(f"{where}: missing ticket")
    if not topic_ok(msg["topic"], objects, facets):
        errors.append(f"{where}: unknown topic {msg['topic']}")
    for key, value in msg["kv"].items():
        if key not in fields:
            errors.append(f"{where}: unknown key {key}")
        if "@" in value or EMAIL.search(value) or PHONE.search(value) or LONG_DIGITS.search(value):
            errors.append(f"{where}: value looks like contact data or a secret ({key})")
    if "co" in msg["kv"] and msg["kv"]["co"] not in COMPTROLLERS:
        errors.append(f"{where}: co= must be a comptroller code")
    for key in ("nx", "ret", "qa"):
        if key in msg["kv"]:
            agent = msg["kv"][key].split(":", 1)[0]
            if ":" not in msg["kv"][key] or agent not in agents:
                errors.append(f"{where}: {key}= must be AGENT:action")
    if "cc" in msg["kv"]:
        for code in msg["kv"]["cc"].split(","):
            if code not in agents:
                errors.append(f"{where}: cc has unknown code {code}")
    if "own" in msg["kv"] and msg["kv"]["own"] not in agents:
        errors.append(f"{where}: own= is not an assistant")
    reports = book["reports"]
    if msg["verb"] == "REC" and msg["frm"] in reports:
        boss = reports[msg["frm"]]
        if msg["to"] != [boss]:
            errors.append(f"{where}: REC from {msg['frm']} goes to {boss}")
        if boss in ("CFO", "TRAV") and "cc" in msg["kv"]:
            errors.append(f"{where}: REC up the {boss} line has no cc")
    return errors


def check_money(messages, book, errors):
    money = book["money"]
    approval = money["approval_topic"]
    holds = set(money["holds"])
    remind = set(money["remind_only"])
    approved = set()
    for msg in messages:
        if msg["verb"] == "GO" and msg["topic"] == approval and msg["frm"] == "MARIAG" and msg["ticket"]:
            approved.add(msg["ticket"])
    for msg in messages:
        topic = msg["topic"]
        where = msg["where"]
        if msg["verb"] != "GO":
            continue
        if topic in remind or any(topic == item or topic.startswith(item + ".") for item in remind):
            errors.append(f"{where}: payroll topic is a reminder, not a GO")
        if topic == approval and msg["frm"] != "MARIAG":
            errors.append(f"{where}: only MARIAG records payment approval")
        held = topic != approval and any(topic == item or topic.startswith(item + ".") for item in holds)
        if held:
            if msg["frm"] != "CFO" or msg["to"][0] not in COMPTROLLERS or len(msg["to"]) != 1:
                errors.append(f"{where}: a payment GO goes from CFO to one comptroller")
            if msg["ticket"] not in approved:
                errors.append(f"{where}: payment GO has no MARIAG approval on that ticket")


def check_book(book, errors):
    if book.get("version") != "2.0.0":
        errors.append("version is not 2.0.0")
    if book.get("rules", {}).get("editor") != "ICOM" or book.get("rules", {}).get("approver") != "MARIAG":
        errors.append("editor must be ICOM and approver must be MARIAG")
    if list(book.get("verbs", {})) != VERBS:
        errors.append(f"verbs must be {VERBS}")
    if list(book.get("priority", {})) != PRIORITIES:
        errors.append(f"priorities must be {PRIORITIES}")
    agents = book.get("agents", {})
    if list(agents) != AGENTS:
        errors.append("assistant list does not match the firm roster")
    for code in agents:
        if not re.fullmatch(r"[A-Z][A-Z0-9]{0,5}", code):
            errors.append(f"bad assistant code {code}")
        if not isinstance(agents[code], str) or not agents[code].strip():
            errors.append(f"missing description for {code}")
    mariag = agents.get("MARIAG", "")
    if "only assistant who speaks to Charles" not in mariag:
        errors.append("MARIAG must be the only assistant who speaks to Charles")
    if "only editor" not in agents.get("ICOM", ""):
        errors.append("ICOM must be the only editor")
    reports = book.get("reports", {})
    if set(reports) != set(AGENTS) - {"MARIAG"}:
        errors.append("reports must cover every assistant except MARIAG")
    for code, boss in reports.items():
        if code in COMPTROLLERS and boss != "CFO":
            errors.append(f"{code} reports only to CFO")
        elif code in TRAVEL and boss != "TRAV":
            errors.append(f"{code} reports to TRAV")
        elif code not in COMPTROLLERS and code not in TRAVEL and boss != "MARIAG":
            errors.append(f"{code} reports to MARIAG")
        if code in COMPTROLLERS and "comptroller" not in agents[code]:
            errors.append(f"{code} description must say comptroller and not a company name")
    if book.get("clients") != {"INT0": book.get("clients", {}).get("INT0")}:
        errors.append("the only lane is INT0")
    if list(book.get("pilot", {}).get("senders", [])) != PILOT:
        errors.append(f"pilot senders must be {PILOT}")
    money = book.get("money", {})
    objects = book.get("objects", {})
    facets = book.get("facets", {})
    for key in ("approval_topic", "standing_topic"):
        if money.get(key) not in objects:
            errors.append(f"money {key} is not a topic")
    for topic in list(money.get("remind_only", [])) + list(money.get("holds", [])):
        if topic not in objects:
            errors.append(f"money topic missing: {topic}")
    if "Charles" not in money.get("rule", "") or "MARIAG" not in money.get("rule", ""):
        errors.append("money rule must name Charles's approval through MARIAG")
    check_objects(objects, facets, errors)
    if book.get("tombstones") not in ({}, None):
        errors.append("tombstones must stay empty until a firm code is retired")
    for key in ("f", "ref", "co", "scope", "ask", "why", "nx"):
        if key not in book.get("fields", {}):
            errors.append(f"missing field {key}")
    if "no client name" not in book.get("rules", {}).get("names", ""):
        errors.append("name rule missing")


def check_text(path, book, errors, found):
    rel = path.relative_to(ROOT).as_posix()
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if "@" not in line:
            continue
        frag = line[line.find("@"):].strip()
        # Drop a closing markdown backtick, and anything a template left after it.
        if "`" in frag:
            frag = frag.split("`", 1)[0].strip()
        # A format template uses P0-3 or a placeholder recipient and is not a live line.
        if not CONCRETE.search(frag):
            continue
        msg, err = parse_message(frag)
        where = f"{rel}:{lineno}"
        if err:
            errors.append(f"{where}: {err}: {frag}")
            continue
        msg["where"] = where
        found.append(msg)
        errors.extend(check_message(msg, book, where))


def check_docs(book, errors):
    hdr = (ROOT / "adopt" / "HDR.txt").read_text()
    if len(hdr) > 2000:
        errors.append("adopt/HDR.txt is too long to paste as a header")
    for phrase in (
        "INT0",
        "#T-1001",
        "github.com/attorneylaputka/icx",
        "MARIAG is the only assistant who speaks to Charles",
        "GO HOLD DONE BLOCKED REC FYI ASK ACK NAK",
        "fin.paybl.apprv",
        "org.rule.apprv",
        "ICOM never appears in a client email, letter, or filing",
        "never the value",
        "Do not edit codebook.yaml",
        "comptrollers to CFO",
        "FLT HTL CAR REST TRV to TRAV",
    ):
        if phrase not in hdr:
            errors.append(f"HDR missing: {phrase}")
    instructions = (ROOT / "AGENT-INSTRUCTIONS.md").read_text()
    for phrase in (
        "only assistant who edits the codebook",
        "only assistant who does",
        "once a week",
        "why=no-ticket",
        "why=prose",
        "why=icx.unk",
        "why=unk",
        "why=no-apprv",
        "why=line",
        "why=pilot",
        "why=remind-only",
        "why=client-doc",
        "fin.paybl.apprv",
        "org.rule.apprv",
        "Iron Docket is not installed yet",
        "#T-1001",
        "MARIAG, JEN, GAUNT",
        "letter, or filing",
        "Never write the value",
        "CLAP, CILL, CCLR, CWAT, CMON, CPRE, CBIG, CFUN, CWES",
        "FLT, HTL, CAR, REST, and TRV report to TRAV",
    ):
        if phrase not in instructions:
            errors.append(f"AGENT-INSTRUCTIONS missing: {phrase}")


def check_public(errors):
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pyc"}:
            continue
        text = path.read_text(errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for rx, label in (
            (EMAIL, "email address"),
            (PHONE, "phone number"),
            (SSN, "id number"),
            (LONG_DIGITS, "long account-like number"),
            (SECRET_ASSIGN, "secret assignment"),
            (PRIVATE_KEY, "private key"),
            (AWS_KEY, "cloud key"),
        ):
            hit = rx.search(text)
            if hit:
                errors.append(f"{rel}: found {label}: {hit.group(0)[:40]}")


def check_icx(book, icx_path, errors):
    raw = yaml.safe_load(Path(icx_path).read_text())["icx"]
    expected = {}
    owners = set()
    for item in raw["classes"] + raw["codes"]:
        expected[item["code"]] = item["name"]
        owners.add(item["owner"])
    objects = book["objects"]
    if objects != expected:
        missing = sorted(set(expected) - set(objects))
        extra = sorted(set(objects) - set(expected))
        changed = sorted(k for k in set(expected) & set(objects) if objects[k] != expected[k])
        if missing:
            errors.append("ICX topics missing from objects: " + ", ".join(missing))
        if extra:
            errors.append("objects not in the ICX book: " + ", ".join(extra))
        if changed:
            errors.append("topic names differ from ICX: " + ", ".join(changed))
    facets = {item["code"]: item["name"] for item in raw["facets"]}
    if book["facets"] != facets:
        errors.append("facets differ from the ICX book")
    unknown_owners = sorted(owners - set(book["agents"]))
    if unknown_owners:
        errors.append("ICX owners missing from assistants: " + ", ".join(unknown_owners))


def self_check(book, errors):
    samples = [
        "@NOPE>ICOM>JEN P2 INT0 #T-1001 FYI org.proto",
        "@JEN>ICOM>MARIAG P2 INT0 FYI org.proto",
        "@JEN>ICOM>MARIAG P2 INT0 #T-1001 FYI not.a.topic",
        "@JEN>ICOM>MARIAG P2 CL01 #T-1001 FYI org.proto",
        "@ALL>ICOM>MARIAG P2 INT0 #T-1001 FYI org.proto",
        "@JEN>ICOM>GAUNT P2 INT0 #T-1001 REC org.proto",
        "@CFO>ICOM>CLAP P1 INT0 #T-1001 GO fin.payrl",
        "@CLAP>ICOM>CFO P1 INT0 #T-1001 GO fin.paybl co=CLAP",
        "@JEN>ICOM>MARIAG P2 INT0 #T-1001 FYI org.proto nope=1",
        "@JEN>ICOM>MARIAG P2 INT0 #T-1001 DONE please book it",
    ]
    for sample in samples:
        msg, err = parse_message(sample)
        problems = []
        if err:
            problems.append(err)
        elif msg is not None:
            msg["where"] = "self-check"
            problems.extend(check_message(msg, book, "self-check"))
            scratch = dict(msg)
            scratch["where"] = "self-check"
            before = len(errors)
            check_money([scratch], book, errors)
            if len(errors) > before:
                problems.append("money")
                del errors[before:]
        if not problems:
            errors.append(f"self-check accepted a bad line: {sample}")
    good = "@JEN>ICOM>MARIAG P2 INT0 #T-1001 FYI lg.court.efil~err n=1"
    msg, err = parse_message(good)
    if err or check_message(msg, book, "self-check"):
        errors.append("self-check rejected a good facet line")
    direct = "@ICOM>JEN P2 INT0 NAK org.proto why=no-ticket"
    msg, err = parse_message(direct)
    if err or check_message(msg, book, "self-check"):
        errors.append("self-check rejected a line ICOM itself sends")
    bypass, bypass_err = parse_message("@JEN>MARIAG P2 INT0 #T-1001 FYI org.proto")
    if bypass_err is None:
        errors.append("self-check accepted a line that skipped ICOM")
    built = "person@" + "example.com"
    if not EMAIL.search(built):
        errors.append("self-check email detector is blind")


def iter_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pyc"}:
            continue
        yield path


def main():
    parser = argparse.ArgumentParser(description="Validate the Laputka ICOM book")
    parser.add_argument("--icx", help="path to the firm ICX examples/codebook.yaml")
    args = parser.parse_args()
    errors = []
    book = load_book(ROOT / "codebook.yaml")
    check_book(book, errors)
    check_docs(book, errors)
    check_public(errors)
    found = []
    for path in iter_files():
        if path.suffix.lower() in {".md", ".txt", ".yaml", ".yml"} or path.name.startswith("HDR"):
            check_text(path, book, errors, found)
    check_money(found, book, errors)
    self_check(book, errors)
    counts = {}
    for msg in found:
        counts[msg["where"].split(":", 1)[0]] = counts.get(msg["where"].split(":", 1)[0], 0) + 1
    for rel in ("examples.txt", "AGENT-INSTRUCTIONS.md", "PROTOCOL-v1.md", "README.md"):
        if counts.get(rel, 0) < 1:
            errors.append(f"no sample message found in {rel}")
    if args.icx:
        check_icx(book, args.icx, errors)
    for err in errors:
        print(err)
    icx_note = " icx=checked" if args.icx and not any(e.startswith("ICX") or e.startswith("objects") or e.startswith("facets") or e.startswith("topic") for e in errors) else ""
    print(
        f"{'FAIL' if errors else 'OK'}: {len(book['agents'])} assistants, "
        f"{len(book['objects'])} topics, {len(book['facets'])} facets, "
        f"{len(found)} sample lines, {len(errors)} errors{icx_note}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # surface a broken book instead of a traceback-only exit
        print(f"FAIL: {exc}")
        sys.exit(1)
