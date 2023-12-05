from datetime import datetime, timedelta, timezone

import bytewax.operators as op
import bytewax.operators.window as win
from bytewax.dataflow import Dataflow
from bytewax.operators.window import EventClockConfig, TumblingWindow, WindowMetadata
from bytewax.testing import TestingSink, TestingSource, run_main

ZERO_TD = timedelta(seconds=0)


def test_reduce_window():
    align_to = datetime(2022, 1, 1, tzinfo=timezone.utc)
    inp = [
        {"time": align_to, "user": "a", "val": 1},
        {"time": align_to + timedelta(seconds=4), "user": "a", "val": 1},
        {"time": align_to + timedelta(seconds=8), "user": "a", "val": 1},
        # First 10 sec window closes during processing this input.
        {"time": align_to + timedelta(seconds=12), "user": "a", "val": 1},
        {"time": align_to + timedelta(seconds=13), "user": "a", "val": 1},
    ]
    out = []

    clock = EventClockConfig(lambda e: e["time"], wait_for_system_duration=ZERO_TD)
    windower = TumblingWindow(length=timedelta(seconds=10), align_to=align_to)

    def add(acc, x):
        acc["val"] += x["val"]
        return acc

    def extract_val(key__metadata_event):
        key, (metadata, event) = key__metadata_event
        return (key, (metadata, event["val"]))

    flow = Dataflow("test_df")
    s = op.input("inp", flow, TestingSource(inp))
    s = op.key_on("key_on_user", s, lambda e: e["user"])
    s = win.reduce_window("add", s, clock, windower, add)
    s = op.map("extract_val", s, extract_val)
    op.output("out", s, TestingSink(out))

    run_main(flow)
    assert out == [
        ("a", (WindowMetadata(align_to, align_to + timedelta(seconds=10)), 3)),
        (
            "a",
            (
                WindowMetadata(
                    align_to + timedelta(seconds=10), align_to + timedelta(seconds=20)
                ),
                2,
            ),
        ),
    ]
