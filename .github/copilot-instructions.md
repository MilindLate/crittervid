# Copilot Instructions for CritterVid

CritterVid converts segmented `.media` files from wildlife trail cameras into `.mp4`, merges them into longer clips per day, and validates that the results play. It runs as a command-line pipeline or a Streamlit GUI, and can be packaged as a Windows executable with PyInstaller.

## Input layout
- Camera files live under `input/DCIM/YYYY/MM/DD/<unix_timestamp>_<NNNN>/*.media`, with a `.info` file alongside (currently unused).
- The layout matches Tuya's documented IPC storage format: the folder timestamp is the event start (UTC) and `NNNN` is the event length in seconds; each `.media` file name is its offset in seconds into the event. The code currently calls `NNNN` a "group ID" (see issue #30).

## Pipeline
- `convert_media.py` — `.media` → `.mp4` with FFmpeg in a thread pool; optional hardware encoding (`--accel`) or stream copy (`--copy`).
- `merge_videos.py` — groups converted clips by day and joins them with FFmpeg's concat demuxer into `--splits-per-day` files.
- `validate_output.py` — decodes every output to check it plays.
- `process_all.py` — runs the three stages in order; `app.py` is the GUI that runs `process_all.py`.
- `ffmpeg_helper.py` — finds FFmpeg (project folder, then `PATH`).

## Conventions
- Write FFmpeg output to `<name>.mp4.part` and rename on success, so a failed run never leaves a partial `.mp4`.
- Every script exits non-zero when anything fails; `process_all.py` exits non-zero if any stage did.
- Write all text (stdout, summaries, concat lists) as UTF-8; escape `'` as `'\''` in concat lists.
- Keep code cross-platform (Windows, macOS, Linux): `pathlib`, no Windows-only APIs.

## Tests
- `python -m pytest`. Most tests use a stand-in FFmpeg (`tests/fake_ffmpeg.py`); `tests/test_real_ffmpeg.py` needs FFmpeg on `PATH` and is skipped otherwise.
- CI runs the suite on Windows and Ubuntu (`.github/workflows/tests.yml`).

## Workflow
- Work is tracked as GitHub issues grouped into roadmap milestones (Phase 0–10). One branch per issue; PRs reference it with `Closes #N`.
