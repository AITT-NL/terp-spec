"""The conversation event stream's schema and fixtures hold together.

``conversation-events.schema.json`` is the normative vocabulary of the events one run
of a conversation streams to the people following it: a profile of AG-UI 1.0, plus the
names Terp adds where AG-UI leaves a name open. It has two kinds of reader, the
producers that validate every event before they send it and the clients that read the
stream, and neither imports the other, which is why the words live here.

It is a vocabulary with readers and no catalog rule. The schema validates one event,
and what a single event keeps that a schema cannot state (a bounded depth, an option
value carried once, no control character anywhere in an open object) is named in
``$defs.eventRules``; the order of a run's events is held by the stream rules the schema
names in ``$defs.streamRules``. This suite is the spec's half: the schema's own discipline, a
small reference reader of the event rules and the stream rules that resolves what a
reader shows from a valid run, and every fixture read as it says.
"""

from __future__ import annotations

import dataclasses
import json
import re

import pytest
from terp_spec import spec_dir

from test_deployment_declaration import _field, _subschemas
from test_standard import _validate

_SPEC = spec_dir()
_SCHEMA = json.loads((_SPEC / "conversation-events.schema.json").read_text(encoding="utf-8"))
_FIXTURES = json.loads(
    (_SPEC / "conversation-events.fixtures.json").read_text(encoding="utf-8")
)

_DEFS = _SCHEMA["$defs"]
_RULES = set(_DEFS["streamRules"]["enum"])
#: The order a reader reports the rules one event breaks in: the order they are listed.
_ORDER = _DEFS["streamRules"]["enum"]
_EVENT_RULES = set(_DEFS["eventRules"]["enum"])
#: The controls prose may hold: a reply has line breaks and an argument may be indented.
_PROSE = ("\t", "\n", "\r")
_CONTROL = re.compile("[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]")
_MAX_EVENT_BYTES = _DEFS["maxEventBytes"]["const"]
_MAX_EVENT_DEPTH = _DEFS["maxEventDepth"]["const"]
_TERMINAL = {"RUN_FINISHED", "RUN_ERROR"}


def _branches(schema: dict = _SCHEMA) -> dict[str, dict]:
    """The event schemas of the root's if/then/else chain, by the type each one holds."""
    found: dict[str, dict] = {}
    link: dict | None = schema
    while link and "if" in link:
        found[link["if"]["properties"]["type"]["const"]] = link["then"]
        link = link.get("else")
    return found


_EVENTS = _branches()


def _too_deep(event: object) -> bool:
    """Does *event* nest past maxEventDepth? Measured without recursion, so an event of any
    depth is measured, and before anything that does recurse reads it."""
    stack: list[tuple[object, int]] = [(event, 1)]
    while stack:
        value, level = stack.pop()
        if isinstance(value, (dict, list)):
            if level > _MAX_EVENT_DEPTH:
                return True
            inner = value.values() if isinstance(value, dict) else value
            stack.extend((item, level + 1) for item in inner)
    return False


def _errors(event: object) -> list[str]:
    """What the schema alone refuses in *event*. ``_validate`` recurses, so it never sees an
    event past maxEventDepth: every caller measures the depth first."""
    assert not _too_deep(event), "the schema is never run on an event past maxEventDepth"
    return _validate(event, _SCHEMA, "$")


def _size(event: object) -> int:
    """An event's size as the cap counts it: compact JSON, UTF-8. An event UTF-8 cannot
    carry (a lone surrogate) is past every cap: no serialization of it exists to read."""
    try:
        return len(json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except UnicodeEncodeError:
        return _MAX_EVENT_BYTES + 1


def _strings(event: object):
    """Every string in *event*, object keys included, with the JSON path it sits at, in
    document order: a key at the path of the member it names, just before its value.
    Walked without recursion, as every walk of an event is."""
    stack: list[tuple[str, object]] = [("$", event)]
    while stack:
        path, value = stack.pop()
        if isinstance(value, str):
            yield path, value
        elif isinstance(value, dict):
            for key, inner in reversed(value.items()):
                stack += [(f"{path}.{key}", inner), (f"{path}.{key}", key)]
        elif isinstance(value, list):
            stack.extend((f"{path}[{index}]", value[index]) for index in reversed(range(len(value))))


def _beyond_schema(event: object) -> list[tuple[str, str]]:
    """``(field, rule)`` for every refusal of *event* a reader makes from ``$defs.eventRules``:
    what the schema describes and its keyword subset cannot state. An event past
    maxEventDepth is refused as a whole, and nothing else is read from it."""
    if _too_deep(event):
        return [("$", "nesting-is-bounded")]
    refused = [
        (path, "strings-hold-no-controls")
        for path, text in _strings(event)
        if _CONTROL.search(text)
    ]
    if isinstance(event, dict) and event.get("type") == "RUN_FINISHED":
        for i, interrupt in enumerate(_member(_member(event, "outcome", dict), "interrupts", list)):
            expires = _member(interrupt, "expiresAt", str)
            if expires is not None and not _real_day(expires):
                refused.append((f"$.outcome.interrupts[{i}].expiresAt", "instants-are-real"))
            terp = _member(_member(interrupt, "metadata", dict), "terp", dict)
            seen: set[str] = set()
            for j, option in enumerate(_member(terp, "options", list)):
                value = _member(option, "value", str)
                if value is not None and value in seen:
                    refused.append((f"$.outcome.interrupts[{i}].metadata.terp.options[{j}].value",
                                    "option-values-are-distinct"))
                seen.add(value)
    return refused


def _real_day(instant: str) -> bool:
    """Does *instant* begin with a day that exists, from the year 0001? Checked by hand
    rather than by a date parser, since parsers disagree: one rolls 2026-02-31 over into
    March and one reads the year 0000. The schema's pattern holds the rest of the shape,
    the time of day included."""
    day = re.match(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T", instant)
    if day is None:
        return False
    year, month, date = (int(part) for part in day.groups())
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return year >= 1 and 1 <= month <= 12 and 1 <= date <= days[month - 1]


def _member(value: object, key: str, kind: type):
    """``value[key]`` when *value* is an object and the member is a *kind*: an empty one of
    the kind otherwise, or ``None`` for a string. The event rules are read from events the
    schema may also refuse, so nothing in them assumes a shape the schema has not checked."""
    inner = value.get(key) if isinstance(value, dict) else None
    if isinstance(inner, kind):
        return inner
    return None if kind is str else kind()


def _refused_fields(event: object) -> set[str]:
    beyond = {field for field, _ in _beyond_schema(event)}
    if _too_deep(event):
        return beyond
    return {_field(message) for message in _errors(event)} | beyond


def _refusal(event: object) -> str | None:
    """The field at which a reader refuses *event*, checked in the order a reader checks
    it: the depth before anything that walks the event, then the schema, the byte cap and
    the other event rules. ``None`` when the event is valid."""
    if _too_deep(event):
        return "$"
    errors = _errors(event)
    if errors:
        return _field(errors[0])
    if _size(event) > _MAX_EVENT_BYTES:
        return "$"
    beyond = _beyond_schema(event)
    return beyond[0][0] if beyond else None


# --------------------------------------------------------------------------- #
# the reference reader                                                         #
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class _Run:
    """What a reader has read of a run so far: all a stream rule needs to judge the next event."""

    thread: str | None = None
    run: str | None = None
    kinds: dict[str, str] = dataclasses.field(default_factory=dict)  # id -> text | call | result | activity
    open_text: set[str] = dataclasses.field(default_factory=set)
    calls: dict[str, str] = dataclasses.field(default_factory=dict)  # toolCallId -> open | ended | answered
    activities: dict[str, str] = dataclasses.field(default_factory=dict)  # messageId -> activityType
    handoff: bool = False
    finished: bool = False


#: The events that give an id the thing it names, by the member that carries the id.
_NAMING = {"TEXT_MESSAGE_START": ("messageId", "text"), "TOOL_CALL_START": ("toolCallId", "call"),
           "TOOL_CALL_RESULT": ("messageId", "result"), "ACTIVITY_SNAPSHOT": ("messageId", "activity")}


def _waiting(finish: dict) -> set[str]:
    """The tool calls a RUN_FINISHED's interrupts name."""
    return {interrupt["toolCallId"] for interrupt in finish["outcome"].get("interrupts", [])
            if "toolCallId" in interrupt}


def _broken(read: _Run, index: int, event: dict) -> set[str]:
    """Every stream rule a valid *event* breaks at *index*, after what *read* holds.

    Each rule is judged on its own, as its text in ``$defs.streamRules`` says, so an event
    that breaks several shows them all.
    """
    kind = event["type"]
    broken: set[str] = set()
    if (index == 0) != (kind == "RUN_STARTED"):
        broken.add("starts-with-run-started")
    if read.finished:
        broken.add("ends-with-one-terminal")
    if read.handoff and kind not in _TERMINAL:
        broken.add("handoff-precedes-the-terminal")
    opened = {"threadId": read.thread, "runId": read.run}
    if read.thread is not None and any(key in event and event[key] != value for key, value in opened.items()):
        broken.add("one-run")
    if kind in _NAMING:
        key, thing = _NAMING[kind]
        named = read.kinds.get(event[key])
        # Opening a message or a call twice is its lifecycle's to judge; a result is named once.
        if named is not None and (named != thing or thing == "result"):
            broken.add("message-id-names-one-thing")
    if kind == "ACTIVITY_SNAPSHOT":
        kept = read.activities.get(event["messageId"], event["activityType"])
        if kept != event["activityType"]:  # an activity keeps its activityType
            broken.add("message-id-names-one-thing")
    if kind == "TEXT_MESSAGE_START" and read.kinds.get(event["messageId"]) == "text":
        broken.add("text-message-lifecycle")
    if kind in {"TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"} and event["messageId"] not in read.open_text:
        broken.add("text-message-lifecycle")
    if kind == "TOOL_CALL_START" and event["toolCallId"] in read.calls:
        broken.add("tool-call-lifecycle")
    if kind in {"TOOL_CALL_ARGS", "TOOL_CALL_END"} and read.calls.get(event["toolCallId"]) != "open":
        broken.add("tool-call-lifecycle")
    if kind == "TOOL_CALL_RESULT" and read.calls.get(event["toolCallId"]) != "ended":
        broken.add("tool-call-lifecycle")
    parent = event.get("parentMessageId") if kind == "TOOL_CALL_START" else None
    if parent is not None and read.kinds.get(parent) != "text":
        broken.add("references-are-known")
    if kind == "RUN_FINISHED":
        waiting = _waiting(event)
        if any(read.calls.get(call) != "ended" for call in waiting):
            broken.add("references-are-known")
        if read.open_text or any(
            state != "answered" for call, state in read.calls.items() if call not in waiting
        ):
            broken.add("closed-before-finish")
    return broken


def _take(read: _Run, event: dict) -> None:
    """What a valid *event* that breaks no rule adds to what a reader has read."""
    kind = event["type"]
    if kind == "RUN_STARTED":
        read.thread, read.run = event["threadId"], event["runId"]
    elif kind in _NAMING:
        key, thing = _NAMING[kind]
        read.kinds[event[key]] = thing
    if kind == "TEXT_MESSAGE_START":
        read.open_text.add(event["messageId"])
    elif kind == "TEXT_MESSAGE_END":
        read.open_text.discard(event["messageId"])
    elif kind == "TOOL_CALL_START":
        read.calls[event["toolCallId"]] = "open"
    elif kind == "TOOL_CALL_END":
        read.calls[event["toolCallId"]] = "ended"
    elif kind == "TOOL_CALL_RESULT":
        read.calls[event["toolCallId"]] = "answered"
    elif kind == "ACTIVITY_SNAPSHOT":
        read.activities[event["messageId"]] = event["activityType"]
    elif kind == "CUSTOM" and event["name"] == "terp.handoff":
        read.handoff = True
    elif kind in _TERMINAL:
        read.finished = True


def _stop(events: list) -> tuple[int, dict[str, str | None]]:
    """Where a reader stops reading *events*, and every rule broken there, each with its
    field (set only for ``events-are-valid``). A sound run is read to its end and breaks
    nothing: ``(len(events), {})``.

    A reader reads nothing from an event that is not valid, so such an event breaks
    ``events-are-valid`` and no other rule.
    """
    read = _Run()
    for index, event in enumerate(events):
        refused = _refusal(event)
        if refused is not None:
            return index, {"events-are-valid": refused}
        broken = _broken(read, index, event)
        if broken:
            return index, dict.fromkeys(broken)
        _take(read, event)
    if not events:
        return 0, {"starts-with-run-started": None}
    return len(events), ({} if read.finished else {"ends-with-one-terminal": None})


def _problem(events: list) -> tuple[int, str, str | None] | None:
    """What a reader reports of *events*: ``(index, rule, field)`` at the first place a
    rule is broken, and among the rules broken there the first in ``$defs.streamRules``'
    order. ``None`` when the run is sound."""
    index, broken = _stop(events)
    if not broken:
        return None
    rule = min(broken, key=_ORDER.index)
    return index, rule, broken[rule]


def _reads(events: list[dict]) -> dict:
    """What a reader resolves from a sound run, in the fixtures' shape."""
    items: list[dict] = []
    by_id: dict[str, dict] = {}
    read = {"outcome": None, "interrupt": None, "context": None, "usage": [], "handoff": None, "error": None}
    for event in events:
        kind = event["type"]
        if kind == "TEXT_MESSAGE_START":
            by_id[event["messageId"]] = {"kind": "text", "id": event["messageId"], "text": ""}
            items.append(by_id[event["messageId"]])
        elif kind == "TEXT_MESSAGE_CONTENT":
            by_id[event["messageId"]]["text"] += event["delta"]
        elif kind == "TOOL_CALL_START":
            item = {"kind": "tool", "id": event["toolCallId"], "name": event["toolCallName"],
                    "args": "", "status": "unfinished"}
            subtitle = event.get("metadata", {}).get("terp", {}).get("subtitle")
            if subtitle is not None:
                item["subtitle"] = subtitle
            if "parentMessageId" in event:
                item["parent"] = event["parentMessageId"]
            by_id[event["toolCallId"]] = item
            items.append(item)
        elif kind == "TOOL_CALL_ARGS":
            by_id[event["toolCallId"]]["args"] += event["delta"]
        elif kind == "TOOL_CALL_RESULT":
            item = by_id[event["toolCallId"]]
            item["status"] = event.get("metadata", {}).get("terp", {}).get("status", "completed")
            item["result"] = event["content"]
        elif kind == "ACTIVITY_SNAPSHOT" and event["activityType"] in _DEFS["terpActivityTypes"]["enum"]:
            if event["messageId"] in by_id:
                by_id[event["messageId"]]["content"] = event["content"]
            else:
                by_id[event["messageId"]] = {"kind": "activity", "id": event["messageId"],
                                             "type": event["activityType"], "content": event["content"]}
                items.append(by_id[event["messageId"]])
        elif kind == "CUSTOM" and event["name"] == "terp.context":
            read["context"] = event["value"]
        elif kind == "CUSTOM" and event["name"] == "terp.handoff":
            read["handoff"] = event["value"]
        elif kind == "RUN_FINISHED":
            outcome = event["outcome"]
            steered = event.get("metadata", {}).get("terp", {}).get("reason") == "steered"
            read["outcome"] = "steered" if steered else outcome["type"]
            read["usage"] = event.get("usage", [])
            for interrupt in outcome.get("interrupts", []):
                resolved = {key: interrupt[key] for key in ("id", "reason", "message", "toolCallId") if key in interrupt}
                resolved.update(interrupt.get("metadata", {}).get("terp", {}))
                read["interrupt"] = resolved
                if "toolCallId" in interrupt:
                    by_id[interrupt["toolCallId"]]["status"] = "waiting"
        elif kind == "RUN_ERROR":
            read["outcome"] = "error"
            read["usage"] = event.get("usage", [])
            read["error"] = {key: event[key] for key in ("message", "code") if key in event}
    return {**read, "items": items}


def _opening() -> dict:
    return {"type": "RUN_STARTED", "threadId": "c", "runId": "r", "protocolVersion": "1.0",
            "metadata": {"terp": {"schemaVersion": 1}}}


def _cases(section: str, expect: str) -> list[dict]:
    return [case for case in _FIXTURES[section] if case["expect"] == expect]


# --------------------------------------------------------------------------- #
# the schema's own discipline                                                  #
# --------------------------------------------------------------------------- #
_CONTROLS = ("\u0000", "\u0007", "\u000a", "\u001b", "\u007f", "\u0085", "\u009b")
_SEPARATORS = ("\u2028", "\u2029")


def test_the_schema_is_a_draft_2020_12_schema_inside_the_validator_subset() -> None:
    assert _SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert _SCHEMA["$id"].endswith("/conversation-events.schema.json")
    # `_validate` reports an unknown schema KEYWORD, so validating an event of every type
    # through it proves the schema stays inside the subset the smallest reader honours.
    for case in _cases("events", "valid"):
        assert _errors(case["event"]) == [], case["id"]


def test_the_type_list_and_the_chain_name_the_same_events() -> None:
    assert sorted(_EVENTS) == _SCHEMA["properties"]["type"]["enum"]
    assert len(_EVENTS) == 12
    for kind, schema in _EVENTS.items():
        assert schema["additionalProperties"] is False, f"{kind}: an event is closed"
        assert "type" in schema["required"], kind
        assert schema["properties"]["type"]["const"] == kind
    refused = {"RAW", "TEXT_MESSAGE_CHUNK", "TOOL_CALL_CHUNK", "STATE_SNAPSHOT", "STATE_DELTA",
               "MESSAGES_SNAPSHOT", "ACTIVITY_DELTA", "STEP_STARTED", "REASONING_START",
               "SUBAGENT_STARTED"}
    assert not refused & set(_EVENTS), "the profile carries none of these in version 1"


def test_three_objects_are_open_and_every_other_is_closed() -> None:
    """The CHANGELOG and the README name the open objects, so the schema holds to the
    list: an interrupt's responseSchema and a producer's own activity content are objects
    with no shape of their own, a custom event's value is any JSON value, and every other
    object is closed, itself or in each branch of its if/then/else."""
    open_objects = set()
    for path, schema in _subschemas(_SCHEMA):
        if schema.get("type") != "object" or schema.get("additionalProperties") is False:
            continue
        if path == "#":  # the root only chooses the event's branch, and every branch is closed
            continue
        branches = [schema.get("then"), schema.get("else")]
        if all(isinstance(branch, dict) and branch.get("additionalProperties") is False for branch in branches):
            continue
        open_objects.add(path.rsplit("/", 1)[-1])
    assert open_objects == {"content", "responseSchema"}
    assert "type" not in _EVENTS["CUSTOM"]["properties"]["value"], "a custom value is any JSON value"


def test_every_shape_and_every_field_says_what_it_means() -> None:
    shapes = [(path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "object"]
    assert len(shapes) >= 20
    for path, schema in shapes:
        assert schema.get("description", "").strip(), f"{path}: say what the shape is"
        for name, definition in schema.get("properties", {}).items():
            assert definition.get("description", "").strip(), (
                f"{path}/properties/{name}: say what the field means"
            )


def test_every_string_is_capped_and_refuses_control_characters() -> None:
    """A stream is shown to people and kept as a transcript: every string the schema
    types has a cap, and no control character reaches a reader except the line breaks
    and tabs of prose. The strings inside the open objects (a form schema, a producer's
    own content and value) are held by the strings-hold-no-controls event rule instead,
    and the reader test below proves that rule reaches them."""
    strings = [(path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "string"]
    assert len(strings) >= 30
    prose = 0
    for path, schema in strings:
        assert isinstance(schema.get("maxLength"), int), f"{path}: a string needs a length cap"
        assert schema["maxLength"] <= _MAX_EVENT_BYTES, path
        pattern = schema.get("pattern")
        assert pattern, f"{path}: a string needs a pattern that refuses control characters"
        is_prose = all(re.search(pattern, f"a{control}b") for control in _PROSE)
        prose += is_prose
        # A line or paragraph separator is a line break to a reader, so one line refuses it.
        for control in _CONTROLS + (() if is_prose else _SEPARATORS):
            if is_prose and control in _PROSE:
                continue
            for probe in (f"a{control}", f"{control}a", f"a{control}b"):
                assert re.search(pattern, probe) is None, (
                    f"{path}: {probe!r} passes {pattern!r} - a control character got through"
                )
    assert prose == 4, "the deltas, a result and a question are prose; every other string is one line"


#: The end of the input, spelled the same for every engine: nothing follows, neither a
#: character of the Basic Multilingual Plane (a UTF-16 code unit, to an engine that reads
#: code units) nor one beyond it (a code point, to an engine that reads code points).
_END = "(?![\\u0000-\\uFFFF]|[^\\u0000-\\uFFFF])"
#: A namespace test reads a prefix and nothing else, so it has no end to anchor.
_PREFIX_TESTS = {"^terp\\."}
#: The escapes a pattern may use: a code point, or a character that is otherwise syntax.
_PORTABLE_ESCAPE = re.compile(r"\\(?:u[0-9A-Fa-f]{4}|[\^$\\.*+?()\[\]{}|/-])")


def _patterns() -> list[str]:
    return sorted({schema["pattern"] for _, schema in _subschemas(_SCHEMA) if "pattern" in schema})


def test_every_pattern_ends_at_the_end_of_the_input() -> None:
    """``$`` also matches before a final newline in Python, so a pattern ends in an explicit
    end of the input, which ``_END`` spells out for Python and ECMA-262 alike: an engine
    that reads UTF-16 code units sees every unit in its first class, and one that reads
    code points (Python, or ECMA-262 under the u flag) sees a character past U+FFFF in
    its second, so an identifier never ends before an emoji."""
    assert _patterns()
    for pattern in _patterns():
        assert pattern.startswith("^"), pattern
        assert pattern.endswith(_END) or pattern in _PREFIX_TESTS, pattern
    identifier = _EVENTS["RUN_STARTED"]["properties"]["runId"]["pattern"]
    assert re.search(identifier, "run-1")
    for tail in ("\n", "\u2028", "\ufeff", "\U0001f600", "\udcff"):
        assert not re.search(identifier, f"run-1{tail}"), repr(tail)


def test_every_pattern_means_the_same_in_python_and_ecma_262() -> None:
    """A schema's patterns are ECMA-262 regular expressions: the npm package is read by
    JavaScript, and this suite reads them in Python. A class escape is where the two
    disagree: Python's ``\\s`` leaves U+FEFF out and ECMA-262's takes it in, so a run error
    whose message was a lone U+FEFF passed one reader and failed the other; ``\\d`` and
    ``\\w`` are Unicode-wide in Python and ASCII in ECMA-262, and ``.`` and ``$`` treat
    line breaks differently. So a pattern spells every class out: its only escapes are a
    code point or a character that is otherwise syntax, and ``.`` and ``$`` appear only
    inside a class."""
    for pattern in _patterns():
        in_class, index = False, 0
        while index < len(pattern):
            char = pattern[index]
            if char == "\\":
                escape = _PORTABLE_ESCAPE.match(pattern, index)
                assert escape, f"{pattern!r}: {pattern[index:index + 2]!r} differs between engines"
                index = escape.end()
                continue
            if in_class:
                in_class = char != "]"
            elif char == "[":
                in_class = True
            else:
                assert char not in ".$", f"{pattern!r}: {char!r} outside a class differs between engines"
            index += 1
    # Every character either engine's \s calls white space is blank to the schema too.
    blank = "\t\n\v\f\r \u0085\u00a0\u1680\u2028\u2029\u202f\u205f\u3000\ufeff" + "".join(
        chr(code) for code in range(0x2000, 0x200B))
    message = _EVENTS["RUN_ERROR"]["properties"]["message"]["pattern"]
    question = _EVENTS["RUN_FINISHED"]["properties"]["outcome"]["properties"]["interrupts"]["items"][
        "properties"]["message"]["pattern"]
    for pattern in (message, question):
        assert re.search(pattern, "x") and re.search(pattern, "\U0001f600")
        for space in blank:
            assert not re.search(pattern, space * 2), (pattern, hex(ord(space)))


def test_the_named_lists_are_sorted_described_and_coherent() -> None:
    for name, definition in _DEFS.items():
        assert definition.get("description", "").strip(), f"$defs/{name}: say what it is"
        if "enum" in definition:
            values = definition["enum"]
            assert values and values == sorted(values) and len(values) == len(set(values)), name
    for rule in _RULES:
        assert f"{rule}:" in _DEFS["streamRules"]["description"], f"{rule}: the rule is stated"
    for rule in _EVENT_RULES:
        assert f"{rule}:" in _DEFS["eventRules"]["description"], f"{rule}: the rule is stated"
    assert "eventRules" in _DEFS["streamRules"]["description"], "events-are-valid names the event rules"
    assert "maxEventDepth" in _DEFS["eventRules"]["description"], "nesting-is-bounded names its bound"
    question = _EVENTS["RUN_FINISHED"]["properties"]["outcome"]["properties"]["interrupts"]["items"]
    terp = question["properties"]["metadata"]["properties"]["terp"]
    assert terp["properties"]["input"]["enum"] == _DEFS["questionInputs"]["enum"]
    names = {
        "terpActivityTypes": _EVENTS["ACTIVITY_SNAPSHOT"]["properties"]["activityType"],
        "terpCustomEvents": _EVENTS["CUSTOM"]["properties"]["name"],
        "terpInterruptReasons": question["properties"]["reason"],
    }
    for name, field in names.items():
        assert field["then"]["enum"] == _DEFS[name]["enum"], name
        assert all(value.startswith("terp.") and re.search(field["pattern"], value) for value in _DEFS[name]["enum"])


@pytest.mark.parametrize("name", ["terpActivityTypes", "terpCustomEvents", "terpInterruptReasons"])
def test_the_terp_namespace_is_closed_and_every_other_is_open(name: str) -> None:
    """A name under terp. is this vocabulary's, so one it does not define is refused; any
    other name is the producer's, and a reader that does not know it passes it by."""
    known = _DEFS[name]["enum"][0]
    seed = {
        "terpActivityTypes": {"type": "ACTIVITY_SNAPSHOT", "messageId": "a-1", "activityType": "x", "content": {}},
        "terpCustomEvents": {"type": "CUSTOM", "name": "x", "value": None},
        "terpInterruptReasons": {
            "type": "RUN_FINISHED", "threadId": "c", "runId": "r",
            "outcome": {"type": "interrupt", "interrupts": [{"id": "i", "reason": "x"}]},
        },
    }[name]

    def named(value: str) -> dict:
        event = json.loads(json.dumps(seed))
        if name == "terpInterruptReasons":
            event["outcome"]["interrupts"][0]["reason"] = value
        else:
            event["activityType" if name == "terpActivityTypes" else "name"] = value
        return event

    field = {
        "terpActivityTypes": "$.activityType",
        "terpCustomEvents": "$.name",
        "terpInterruptReasons": "$.outcome.interrupts[0].reason",
    }[name]

    def refused(value: str) -> set[str]:
        return {_field(message) for message in _errors(named(value))}

    # The vocabulary's own name passes as a name; its shape asks for more than the seed has.
    assert field not in refused(known), f"{name}: {known} is the vocabulary's own"
    assert field in refused("terp.not-in-the-vocabulary"), f"{name}: an unknown terp. name"
    assert _errors(named("example.own-name")) == [], f"{name}: a producer's own name"


def test_the_byte_cap_is_held_at_the_byte_and_not_at_the_character() -> None:
    """The cap counts compact UTF-8 bytes, so a string of characters that are each two
    bytes reaches it at half the length."""
    skeleton = {"type": "TEXT_MESSAGE_CONTENT", "messageId": "msg-1", "delta": ""}
    room = _MAX_EVENT_BYTES - _size(skeleton)
    fits = [_opening(), {"type": "TEXT_MESSAGE_START", "messageId": "msg-1", "role": "assistant"},
            {**skeleton, "delta": "é" * (room // 2)}]
    assert _size(fits[-1]) <= _MAX_EVENT_BYTES
    too_big = [*fits[:2], {**skeleton, "delta": "é" * (room // 2 + 1)}]
    assert _errors(too_big[-1]) == [], "the schema alone cannot count bytes"
    assert _problem(too_big) == (2, "events-are-valid", "$")
    assert _problem(fits) == (3, "ends-with-one-terminal", None)



def test_an_event_utf8_cannot_carry_is_refused_rather_than_crashing_the_reader() -> None:
    """A lone surrogate is legal JSON syntax and no UTF-8 text: a reader that tried to
    size it would raise in the middle of a run instead of ending the reading."""
    events = [_opening(), {"type": "TEXT_MESSAGE_START", "messageId": "m", "role": "assistant"},
              {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "a\udcffb"}]
    assert _problem(events) == (2, "events-are-valid", "$")


def _nested(levels: int) -> tuple[object, str]:
    """A value of *levels* nested arrays around a 0, and its compact JSON, built without
    recursion: json.dumps itself recurses, and would raise on what this test is about."""
    value: object = 0
    for _ in range(levels):
        value = [value]
    return value, "[" * levels + "0" + "]" * levels


def _holding(where: str, value: object, text: str) -> tuple[dict, str]:
    """An event that carries *value* in one of the three open objects, and its compact JSON."""
    if where == "value":
        return ({"type": "CUSTOM", "name": "example.deep", "value": value},
                '{"type":"CUSTOM","name":"example.deep","value":' + text + "}")
    if where == "content":
        return ({"type": "ACTIVITY_SNAPSHOT", "messageId": "a-1", "activityType": "example.deep",
                 "content": {"x": value}},
                '{"type":"ACTIVITY_SNAPSHOT","messageId":"a-1","activityType":"example.deep",'
                '"content":{"x":' + text + "}}")
    return ({"type": "RUN_FINISHED", "threadId": "c", "runId": "r",
             "outcome": {"type": "interrupt", "interrupts": [
                 {"id": "i", "reason": "example.deep", "responseSchema": {"x": value}}]}},
            '{"type":"RUN_FINISHED","threadId":"c","runId":"r","outcome":{"type":"interrupt",'
            '"interrupts":[{"id":"i","reason":"example.deep","responseSchema":{"x":' + text + "}}]}}")


@pytest.mark.parametrize("where", ["value", "content", "responseSchema"])
def test_no_event_under_the_byte_cap_nests_deep_enough_to_crash_the_reader(where: str) -> None:
    """An open object can nest as deep as its bytes allow: some 32 000 levels fit under
    maxEventBytes, and a reader that recursed into them would exhaust its stack in the
    middle of a run instead of ending the reading. The depth is measured first, without
    recursion, so every such event is refused at the bound, and an event at the bound is
    read as any other."""
    skeleton = len(_holding(where, 0, "0")[1].encode("utf-8"))
    for levels in (990, (_MAX_EVENT_BYTES - skeleton) // 2):
        event, text = _holding(where, *_nested(levels))
        assert len(text.encode("utf-8")) <= _MAX_EVENT_BYTES
        assert _too_deep(event)
        assert _beyond_schema(event) == [("$", "nesting-is-bounded")]
        assert _refused_fields(event) == {"$"}
        assert _problem([_opening(), event]) == (1, "events-are-valid", "$")
    # The levels above the nested value: the event; the content; the outcome, the
    # interrupts, the interrupt and the responseSchema.
    above = {"value": 1, "content": 2, "responseSchema": 5}[where]
    at_the_bound = _MAX_EVENT_DEPTH - above
    event, _ = _holding(where, *_nested(at_the_bound))
    assert not _too_deep(event) and _refusal(event) is None
    event, _ = _holding(where, *_nested(at_the_bound + 1))
    assert _refusal(event) == "$"


@pytest.mark.parametrize("outcome", [
    {"type": "interrupt", "interrupts": [{"id": "i", "reason": "example.x", "metadata": "terp"}]},
    {"type": "interrupt", "interrupts": [{"id": "i", "reason": "terp.question", "message": "Which?",
                                          "metadata": {"terp": ["input"]}}]},
    {"type": "interrupt", "interrupts": [{"id": "i", "reason": "terp.question", "message": "Which?",
                                          "metadata": {"terp": {"input": "choice", "options": {"value": "a"}}}}]},
    {"type": "interrupt", "interrupts": [{"id": "i", "reason": "terp.question", "message": "Which?",
                                          "metadata": {"terp": {"input": "choice", "options": [
                                              {"value": ["a"], "label": "A"}, {"value": ["a"], "label": "B"},
                                              {"value": {"a": 1}, "label": "C"}, "a"]}}}]},
    {"type": "interrupt", "interrupts": 7},
    {"type": "interrupt", "interrupts": ["i"]},
    ["interrupt"],
])
def test_the_event_rules_read_any_shape_the_schema_refuses(outcome: object) -> None:
    """A reader applies the event rules beside the schema, so they meet every shape the
    schema refuses, and a refusal never becomes a crash in the middle of a run."""
    event = {"type": "RUN_FINISHED", "threadId": "c", "runId": "r", "outcome": outcome}
    assert _beyond_schema(event) == []
    assert _refused_fields(event)
    assert _problem([_opening(), event])[1] == "events-are-valid"


def test_a_later_version_is_refused_rather_than_read() -> None:
    """A reader that does not know a version reads nothing from the stream: an unreadable
    stream is not an empty one, and guessing past it would act on words it cannot read."""
    later = _opening()
    later["metadata"]["terp"]["schemaVersion"] = 2
    assert _problem([later]) == (0, "events-are-valid", "$.metadata.terp.schemaVersion")


# --------------------------------------------------------------------------- #
# the fixtures                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _cases("events", "valid"), ids=lambda case: case["id"])
def test_a_valid_event_passes(case: dict) -> None:
    assert _refusal(case["event"]) is None, case["about"]


@pytest.mark.parametrize("case", _cases("events", "invalid"), ids=lambda case: case["id"])
def test_an_invalid_event_is_refused_at_its_field(case: dict) -> None:
    fields = _refused_fields(case["event"])
    assert case["field"] in fields, (
        f"{case['id']} ({case['about']}): refused at {sorted(fields)}, the fixture says {case['field']}"
    )
    assert case["allowed"].strip(), f"{case['id']}: say what the field allows"
    if case.get("beyondSchema"):
        assert (case["field"], case["rule"]) in _beyond_schema(case["event"]), case["id"]
        if case["rule"] != "nesting-is-bounded":  # the schema never sees an event past the bound
            assert _errors(case["event"]) == [], f"{case['id']}: marked beyond the schema, and the schema refuses it"
    else:
        assert _errors(case["event"]), f"{case['id']}: the schema alone must refuse it"


@pytest.mark.parametrize("case", _cases("streams", "valid"), ids=lambda case: case["id"])
def test_a_valid_stream_reads_as_it_says(case: dict) -> None:
    assert _problem(case["events"]) is None, case["about"]
    assert _reads(case["events"]) == case["reads"], case["about"]


@pytest.mark.parametrize("case", _cases("streams", "invalid"), ids=lambda case: case["id"])
def test_an_invalid_stream_breaks_its_rule_where_it_says(case: dict) -> None:
    expected = (case["at"], case["rule"], case.get("field"))
    assert _problem(case["events"]) == expected, case["about"]


@pytest.mark.parametrize("case", _cases("streams", "invalid"), ids=lambda case: case["id"])
def test_an_invalid_stream_breaks_no_other_rule_where_it_stops(case: dict) -> None:
    """A fixture pins one rule, so it breaks one: every rule is judged on its own at the
    event where the reader stops, and only the fixture's is broken there. A run that
    broke two would hold a second implementation to this reader's order of checks rather
    than to the rules' text. Where the broken rule is events-are-valid, the event is
    refused at the fixture's field and no other."""
    index, broken = _stop(case["events"])
    assert (index, sorted(broken)) == (case["at"], [case["rule"]]), case["about"]
    if case["rule"] == "events-are-valid":
        assert _refused_fields(case["events"][index]) == {case["field"]}, case["about"]


def test_a_run_that_breaks_several_rules_at_one_event_reports_the_first_listed() -> None:
    """No fixture breaks two rules at once, and a run in the wild may: a reader then
    reports the first event at which any rule is broken and, of the rules broken there,
    the first in $defs.streamRules' order. An event that is not valid is not read, so it
    breaks events-are-valid alone."""
    call = {"type": "TOOL_CALL_START", "toolCallId": "call-1", "toolCallName": "delete_order"}
    waits = {"type": "RUN_FINISHED", "threadId": "c", "runId": "r", "outcome": {
        "type": "interrupt", "interrupts": [{"id": "ap-1", "reason": "example.approval", "toolCallId": "call-1"}]}}
    text = {"type": "TEXT_MESSAGE_START", "messageId": "m", "role": "assistant"}
    # A message still open, and an interrupt naming a call whose arguments never ended.
    events = [_opening(), text, call, waits]
    assert _stop(events) == (3, {"closed-before-finish": None, "references-are-known": None})
    assert _problem(events) == (3, "closed-before-finish", None)
    # A finish that opens the run, waiting on a call the run never made.
    assert set(_stop([waits])[1]) == {"references-are-known", "starts-with-run-started"}
    assert _problem([waits]) == (0, "references-are-known", None)
    # Text after the run ended, for a message that was never opened.
    late = {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "more"}
    events = [_opening(), {**waits, "outcome": {"type": "success"}}, late]
    assert set(_stop(events)[1]) == {"ends-with-one-terminal", "text-message-lifecycle"}
    assert _problem(events) == (2, "ends-with-one-terminal", None)
    # An event the schema refuses is not read, whatever else it would break.
    assert _stop([_opening(), {**late, "delta": "\u0000"}]) == (1, {"events-are-valid": "$.delta"})


def test_the_stream_rules_are_stated_in_the_order_a_reader_reports_them() -> None:
    """The order is the enum's, and the description states each rule in that order too."""
    description = _DEFS["streamRules"]["description"]
    positions = [description.index(f"{rule}:") for rule in _ORDER]
    assert positions == sorted(positions)
    assert "order" in description.split(_ORDER[0] + ":")[0], "the preamble says how several are reported"


def test_the_fixtures_are_well_formed_and_cover_the_vocabulary() -> None:
    ids = [case["id"] for section in ("events", "streams") for case in _FIXTURES[section]]
    assert len(ids) == len(set(ids))
    for case in _FIXTURES["events"]:
        keys = {"id", "expect", "about", "event"}
        if case["expect"] == "invalid":
            keys |= {"field", "allowed"} | ({"beyondSchema", "rule"} if "beyondSchema" in case else set())
        assert set(case) == keys, case["id"]
        assert case.get("rule", next(iter(_EVENT_RULES))) in _EVENT_RULES, case["id"]
    for case in _FIXTURES["streams"]:
        keys = {"id", "expect", "about", "events"}
        keys |= {"reads"} if case["expect"] == "valid" else {"at", "rule"} | ({"field"} if "field" in case else set())
        assert set(case) == keys, case["id"]
    assert len(_cases("events", "valid")) >= 20 and len(_cases("events", "invalid")) >= 50
    assert len(_cases("streams", "valid")) >= 10

    valid_events = [case["event"] for case in _cases("events", "valid")]
    assert {event["type"] for event in valid_events} == set(_EVENTS), "every event type has a valid fixture"
    streamed = {event["type"] for case in _cases("streams", "valid") for event in case["events"]}
    assert streamed == set(_EVENTS), "every event type appears in a valid stream"
    assert {case["rule"] for case in _cases("streams", "invalid")} == _RULES, "every stream rule is broken once"
    assert {case["rule"] for case in _cases("events", "invalid") if "rule" in case} == _EVENT_RULES, (
        "every event rule is broken once"
    )

    terp_names = {event.get("activityType") or event.get("name") for event in valid_events} | {
        interrupt["reason"]
        for event in valid_events
        for interrupt in event.get("outcome", {}).get("interrupts", [])
    }
    for name in ("terpActivityTypes", "terpCustomEvents", "terpInterruptReasons"):
        assert set(_DEFS[name]["enum"]) <= terp_names, f"every {name} entry has a valid fixture"
    inputs = {
        interrupt["metadata"]["terp"]["input"]
        for event in valid_events
        for interrupt in event.get("outcome", {}).get("interrupts", [])
        if "metadata" in interrupt
    }
    assert inputs == set(_DEFS["questionInputs"]["enum"]), "every way to answer has a valid fixture"

    reads = [case["reads"] for case in _cases("streams", "valid")]
    assert {read["outcome"] for read in reads} == {"success", "interrupt", "cancelled", "steered", "error"}
    statuses = {item["status"] for read in reads for item in read["items"] if item["kind"] == "tool"}
    assert statuses == {"completed", "error", "waiting", "unfinished"}
    touched = " ".join(case["field"] for case in _cases("events", "invalid"))
    for name in ("type", "metadata.terp.schemaVersion", "protocolVersion", "delta", "toolCallName",
                 "subtitle", "content", "activityType", "value", "outcome", "interrupts", "input",
                 "options", "reason", "expiresAt", "usage", "message", "code", "timestamp"):
        assert name in touched, f"no invalid event fixture is about {name}"
