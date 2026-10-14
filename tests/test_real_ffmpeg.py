"""End-to-end runs with the real ffmpeg. Skipped when ffmpeg isn't on PATH."""
import subprocess


def make_clip(ws, name):
    path = ws.add_media(name, b'')
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-y',
         '-f', 'lavfi', '-i', 'testsrc=duration=1:size=160x120:rate=10',
         '-f', 'lavfi', '-i', 'sine=duration=1',
         '-c:v', 'libx264', '-c:a', 'aac', '-f', 'mpegts', str(path)],
        check=True,
    )


def test_full_pipeline(real_ws):
    make_clip(real_ws, '0001.media')
    make_clip(real_ws, '0002.media')

    result = real_ws.run('process_all.py', '--accel', 'cpu')

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(real_ws.files('1759300000_0001_*.mp4')) == 2
    assert len(real_ws.files('merged_*.mp4')) == 1
    assert real_ws.files('*.part') == []


def test_full_pipeline_with_quote_and_non_ascii_output_dir(real_ws):
    out_dir = "out O'Brien ėų 野"
    make_clip(real_ws, '0001.media')
    make_clip(real_ws, '0002.media')

    result = real_ws.run('process_all.py', '--accel', 'cpu', '--output-dir', out_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(list((real_ws.root / out_dir).rglob('merged_*.mp4'))) == 1


def test_unreadable_input_fails_cleanly(real_ws):
    make_clip(real_ws, '0001.media')
    real_ws.add_media('0002.media', bytes(range(256)) * 20)

    result = real_ws.run('convert_media.py', '--accel', 'cpu')

    assert real_ws.converted('0001.media').exists()
    assert not real_ws.converted('0002.media').exists()
    assert real_ws.files('*.part') == []
    assert result.returncode == 1
