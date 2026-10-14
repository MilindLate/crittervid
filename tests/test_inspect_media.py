"""tools/inspect_media.py on synthetic .media data in the record format."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import inspect_media  # noqa: E402

HEADER = struct.Struct('<IIIIQ')


def record(rtype, payload, t_us):
    return HEADER.pack(rtype, len(payload), t_us // 1000, 0, t_us) + payload


def synthetic_segment(start_us=10_000_000):
    """1 s of 'video' at 50/100 ms gaps (keyframe first) and 8 kHz s16 audio."""
    out, t = [], start_us
    out.append(record(1, b'\x00\x00\x00\x01\x27key', t))
    for gap in [50_000, 100_000] * 6 + [50_000] * 2:   # 14 more frames, 1.0 s
        t += gap
        out.append(record(0, b'\x00\x00\x00\x01\x21p', t))
    for i in range(25):                                  # 25 x 40 ms of audio
        out.append(record(3, b'\x00' * 640, start_us + i * 40_000))
    return b''.join(out)


def test_reads_every_record():
    recs = list(inspect_media.read_records(synthetic_segment()))
    assert [r[0] for r in recs].count(1) == 1
    assert [r[0] for r in recs].count(0) == 14
    assert [r[0] for r in recs].count(3) == 25


def test_summarises_timing(tmp_path):
    f = tmp_path / '0000.media'
    f.write_bytes(synthetic_segment())

    s = inspect_media.summarise([f])

    assert s['records'] == {'video frame': 14, 'video keyframe': 1, 'audio': 25}
    assert s['video_span_s'] == pytest.approx(1.0)
    assert s['video_gaps_ms'] == {50: 8, 100: 6}
    assert s['audio_bytes_per_s'] == 16000


@pytest.mark.parametrize('data', [b'\x00' * 10, record(0, b'abc', 0)[:-1]])
def test_rejects_data_that_isnt_whole_records(data):
    with pytest.raises(ValueError):
        list(inspect_media.read_records(data))
