"""End to end: a generated SD card that mimics the camera's layout, run through the
whole pipeline with the real FFmpeg, checking what comes out rather than just the
exit code. Skipped when FFmpeg isn't installed (required on CI).

The card follows Tuya's IPC storage layout, which these cameras use:
DCIM/YYYY/MM/DD/<event start, UTC epoch>_<event length in s>/<offset in s>.media,
with each .media file a raw H.264 stream.
"""
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

FPS = 15  # not FFmpeg's 25 fps default for raw streams, so timing errors show up

# Events as (UTC start, segment lengths in seconds). Times are mid-day UTC, so each
# event falls on the same calendar day for any machine timezone from UTC-6 to UTC+8;
# merging groups by the processing machine's local day (see #8).
EVENTS = [
    (datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc), [10, 10, 5]),
    (datetime(2026, 10, 1, 15, 30, tzinfo=timezone.utc), [10, 4]),
    (datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc), [10, 10]),
]
DAY_TOTALS = {(2026, 10, 1): 39, (2026, 10, 2): 20}
SEGMENTS = sum(len(lengths) for _, lengths in EVENTS)
TOLERANCE = 0.25  # seconds; one frame at 15 fps is 0.067 s


def event_folder(start, lengths):
    return f'{int(start.timestamp())}_{sum(lengths):04d}'


@pytest.fixture(scope='module')
def card(tmp_path_factory):
    """The generated DCIM folder, built once per test module."""
    if not (shutil.which('ffmpeg') and shutil.which('ffprobe')):
        return None
    dcim = tmp_path_factory.mktemp('card') / 'DCIM'
    for start, lengths in EVENTS:
        folder = dcim / start.strftime('%Y/%m/%d') / event_folder(start, lengths)
        folder.mkdir(parents=True)
        offset = 0
        for length in lengths:
            subprocess.run(
                ['ffmpeg', '-v', 'error', '-f', 'lavfi',
                 '-i', f'testsrc=duration={length}:size=320x240:rate={FPS}',
                 '-c:v', 'libx264', '-preset', 'ultrafast', '-f', 'h264',
                 str(folder / f'{offset:04d}.media')],
                check=True,
            )
            offset += length
    return dcim


@pytest.fixture
def card_ws(real_ws, card):
    shutil.copytree(card, real_ws.root / 'input' / 'DCIM')
    return real_ws


def duration(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)['format']['duration'])


def merged_by_day(ws):
    days = {}
    for f in ws.files('merged_*.mp4'):
        # output/merged/YYYY/MM/DD/merged_*.mp4
        day = tuple(int(part) for part in f.parent.relative_to(ws.root / 'output' / 'merged').parts)
        days.setdefault(day, []).append(f)
    return days


def run(ws, *args):
    return ws.run('process_all.py', '--accel', 'cpu', *args)


def test_card_converts_merges_and_validates(card_ws):
    result = run(card_ws)

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'All output videos are correctly named and playable.' in result.stdout
    assert card_ws.files('*.part') == []

    # Every segment converted, at its true length
    for start, lengths in EVENTS:
        folder = event_folder(start, lengths)
        offset = 0
        for length in lengths:
            [mp4] = card_ws.files(f'{folder}_{offset:04d}.mp4')
            assert duration(mp4) == pytest.approx(length, abs=TOLERANCE), mp4.name
            offset += length
    assert len(card_ws.files('*_*_*.mp4')) - len(card_ws.files('merged_*.mp4')) == SEGMENTS

    # One merged file per day, containing all of that day's footage
    days = merged_by_day(card_ws)
    assert sorted(days) == sorted(DAY_TOTALS)
    for day, files in days.items():
        [merged] = files
        assert duration(merged) == pytest.approx(DAY_TOTALS[day], abs=TOLERANCE * 2), day

    assert (card_ws.root / 'output' / 'conversion_summary.txt').is_file()
    assert (card_ws.root / 'output' / 'merged' / 'merge_summary.txt').is_file()


def test_card_rerun_skips_finished_work(card_ws):
    assert run(card_ws).returncode == 0
    converted = {f: f.stat().st_mtime_ns for f in card_ws.files('*.mp4') if 'merged' not in f.parts}

    result = run(card_ws)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count('SKIPPED:') == SEGMENTS
    assert {f: f.stat().st_mtime_ns for f in converted} == converted


def test_card_splits_each_day(card_ws):
    result = run(card_ws, '--splits-per-day', '2')

    assert result.returncode == 0, result.stdout + result.stderr
    days = merged_by_day(card_ws)
    assert sorted(days) == sorted(DAY_TOTALS)
    for day, files in days.items():
        assert sorted(f.name.rsplit('_', 1)[1] for f in files) == ['part1of2.mp4', 'part2of2.mp4']
        assert sum(duration(f) for f in files) == pytest.approx(DAY_TOTALS[day], abs=TOLERANCE * 2), day
