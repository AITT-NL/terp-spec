"""The conversation event stream's schema and fixtures hold together.

``conversation-events.schema.json`` is the normative vocabulary of the events one run
of a conversation streams to the people following it: a profile of AG-UI 1.0, plus the
names Terp adds where AG-UI leaves a name open. It has two kinds of reader, the
producers that validate every event before they send it and the clients that read the
stream, and neither imports the other, which is why the words live here.

It is a vocabulary with readers and no catalog rule. The schema validates one event;
the order of a run's events is held by the stream rules the schema names in
``$defs.streamRules``, because a schema cannot state them. This suite is the spec's
half: the schema's own discipline, a small reference reader that applies the stream
rules and resolves what a reader shows from a valid run, and every fixture read as it
says.
"""

from __future__ import annotations

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
_MAX_EVENT_BYTES = _DEFS["maxEventBytes"]["const"]
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


def _errors(event: object) -> list[str]:
    return _validate(event, _SCHEMA, "$")


def _size(event: object) -> int:
    """An event's size as the cap counts it: compact JSON, UTF-8."""
    return len(json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


# --------------------------------------------------------------------------- #
# the reference reader                                                         #
# --------------------------------------------------------------------------- #
def _problem(events: list[dict]) -> tuple[int, str, str | None] | None:
    """The first place *events* breaks a stream rule: ``(index, rule, field)``.

    ``field`` is set only for ``events-are-valid``. ``None`` when the run is sound.
    """
    if not events:
        return 0, "starts-with-run-started", None
    thread = run = None
    kinds: dict[str, str] = {}  # messageId -> text | result | activity
    open_text: set[str] = set()
    calls: dict[str, str] = {}  # toolCallId -> open | ended | answered
    handoff = finished = False
    for index, event in enumerate(events):
        errors = _errors(event)
        if errors:
            return index, "events-are-valid", _field(errors[0])
        if _size(event) > _MAX_EVENT_BYTES:
            return index, "events-are-valid", "$"
        kind = event["type"]
        if (index == 0) != (kind == "RUN_STARTED"):
            return index, "starts-with-run-started", None
        if finished:
            return index, "ends-with-one-terminal", None
        if handoff and kind not in _TERMINAL:
            return index, "handoff-precedes-the-terminal", None
        if kind == "RUN_STARTED":
            thread, run = event["threadId"], event["runId"]
            continue
        if ("threadId" in event and event["threadId"] != thread) or (
            "runId" in event and event["runId"] != run
        ):
            return index, "one-run", None
        if kind == "TEXT_MESSAGE_START":
            message = event["messageId"]
            if kinds.get(message) == "text":
                return index, "text-message-lifecycle", None
            if message in kinds:
                return index, "message-id-names-one-thing", None
            kinds[message] = "text"
            open_text.add(message)
        elif kind in {"TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"}:
            if event["messageId"] not in open_text:
                return index, "text-message-lifecycle", None
            if kind == "TEXT_MESSAGE_END":
                open_text.discard(event["messageId"])
        elif kind == "TOOL_CALL_START":
            if event["toolCallId"] in calls:
                return index, "tool-call-lifecycle", None
            parent = event.get("parentMessageId")
            if parent is not None and kinds.get(parent) != "text":
                return index, "references-are-known", None
            calls[event["toolCallId"]] = "open"
        elif kind in {"TOOL_CALL_ARGS", "TOOL_CALL_END"}:
            if calls.get(event["toolCallId"]) != "open":
                return index, "tool-call-lifecycle", None
            if kind == "TOOL_CALL_END":
                calls[event["toolCallId"]] = "ended"
        elif kind == "TOOL_CALL_RESULT":
            if calls.get(event["toolCallId"]) != "ended":
                return index, "tool-call-lifecycle", None
            if event["messageId"] in kinds:
                return index, "message-id-names-one-thing", None
            kinds[event["messageId"]] = "result"
            calls[event["toolCallId"]] = "answered"
        elif kind == "ACTIVITY_SNAPSHOT":
            if kinds.setdefault(event["messageId"], "activity") != "activity":
                return index, "message-id-names-one-thing", None
        elif kind == "CUSTOM" and event["name"] == "terp.handoff":
            handoff = True
        elif kind == "RUN_FINISHED":
            waiting = {
                interrupt["toolCallId"]
                for interrupt in event["outcome"].get("interrupts", [])
                if "toolCallId" in interrupt
            }
            if waiting - set(calls):
                return index, "references-are-known", None
            unanswered = {call for call, state in calls.items() if state != "answered"}
            if open_text or unanswered - waiting:
                return index, "closed-before-finish", None
            finished = True
        elif kind == "RUN_ERROR":
            finished = True
    if not finished:
        return len(events), "ends-with-one-terminal", None
    return None


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
            read["handoff"] = event["value"]["nextRunId"]
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
#: The controls prose may hold: a reply has line breaks and an argument may be indented.
_PROSE = ("\t", "\n", "\r")


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
    """A stream is shown to people and kept as a transcript: every string has a cap, and
    no control character reaches a reader except the line breaks and tabs of prose."""
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
        for control in _CONTROLS:
            if is_prose and control in _PROSE:
                continue
            for probe in (f"a{control}", f"{control}a", f"a{control}b"):
                assert re.search(pattern, probe) is None, (
                    f"{path}: {probe!r} passes {pattern!r} - a control character got through"
                )
    assert prose == 4, "the deltas, a result and a question are prose; every other string is one line"


def test_every_pattern_ends_at_the_end_of_the_input() -> None:
    """``$`` also matches before a final newline in Python; ``(?![\\s\\S])`` is the end
    of the input in Python and ECMA-262 alike."""
    patterns = {schema["pattern"] for _, schema in _subschemas(_SCHEMA) if "pattern" in schema}
    assert patterns
    for pattern in sorted(patterns):
        assert pattern.startswith("^") and pattern.endswith("(?![\\s\\S])"), pattern
    identifier = _EVENTS["RUN_STARTED"]["properties"]["runId"]["pattern"]
    assert re.search(identifier, "run-1") and not re.search(identifier, "run-1\n")


def test_the_named_lists_are_sorted_described_and_coherent() -> None:
    for name, definition in _DEFS.items():
        assert definition.get("description", "").strip(), f"$defs/{name}: say what it is"
        if "enum" in definition:
            values = definition["enum"]
            assert values and values == sorted(values) and len(values) == len(set(values)), name
    for rule in _RULES:
        assert f"{rule}:" in _DEFS["streamRules"]["description"], f"{rule}: the rule is stated"
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
    assert _errors(case["event"]) == [], case["about"]
    assert _size(case["event"]) <= _MAX_EVENT_BYTES


@pytest.mark.parametrize("case", _cases("events", "invalid"), ids=lambda case: case["id"])
def test_an_invalid_event_is_refused_at_its_field(case: dict) -> None:
    fields = {_field(message) for message in _errors(case["event"])}
    assert case["field"] in fields, (
        f"{case['id']} ({case['about']}): refused at {sorted(fields)}, the fixture says {case['field']}"
    )
    assert case["allowed"].strip(), f"{case['id']}: say what the field allows"


@pytest.mark.parametrize("case", _cases("streams", "valid"), ids=lambda case: case["id"])
def test_a_valid_stream_reads_as_it_says(case: dict) -> None:
    assert _problem(case["events"]) is None, case["about"]
    assert _reads(case["events"]) == case["reads"], case["about"]


@pytest.mark.parametrize("case", _cases("streams", "invalid"), ids=lambda case: case["id"])
def test_an_invalid_stream_breaks_its_rule_where_it_says(case: dict) -> None:
    expected = (case["at"], case["rule"], case.get("field"))
    assert _problem(case["events"]) == expected, case["about"]


def test_the_fixtures_are_well_formed_and_cover_the_vocabulary() -> None:
    ids = [case["id"] for section in ("events", "streams") for case in _FIXTURES[section]]
    assert len(ids) == len(set(ids))
    for case in _FIXTURES["events"]:
        keys = {"id", "expect", "about", "event"} | ({"field", "allowed"} if case["expect"] == "invalid" else set())
        assert set(case) == keys, case["id"]
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
