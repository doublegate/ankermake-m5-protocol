from pathlib import Path
import threading

from web.camera import (
    CameraCaptureError,
    capture_camera_snapshot_to_file,
    iter_mjpeg_frames,
    open_external_mjpeg_stream,
)


def test_external_rtsp_capture_falls_back_when_tcp_transport_fails(monkeypatch):
    attempts = []

    def fake_run(ffmpeg_path, input_url, output_path, *, timeout, input_args=None, format_hint=None, scale=None):
        attempts.append(list(input_args or []))
        if "-rtsp_transport" in (input_args or []):
            raise CameraCaptureError("TCP transport failed")
        Path(output_path).write_bytes(b"jpeg")

    monkeypatch.setattr("web.camera._run_ffmpeg_snapshot", fake_run)

    output_dir = Path(".tmp")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "camera_helper_rtsp_fallback.jpg"
    try:
        if output_path.exists():
            output_path.unlink()

        capture_camera_snapshot_to_file(
            {
                "source": "external",
                "effective_source": "external",
                "external": {
                    "stream_url": "rtsp://cam.local/live",
                    "snapshot_url": "",
                },
            },
            "ffmpeg",
            str(output_path),
            host="127.0.0.1",
            port="4470",
        )

        assert attempts == [
            ["-rtsp_transport", "tcp", "-fflags", "nobuffer", "-probesize", "32768", "-analyzeduration", "0"],
            ["-fflags", "nobuffer", "-probesize", "32768", "-analyzeduration", "0"],
        ]
        assert output_path.read_bytes() == b"jpeg"
    finally:
        try:
            output_path.unlink()
        except OSError:
            pass


def test_open_external_mjpeg_stream_uses_persistent_rtsp_preview_command(monkeypatch):
    captured = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            self.stdout = None

    monkeypatch.setattr("subprocess.Popen", FakePopen)

    proc = open_external_mjpeg_stream(
        "ffmpeg",
        "rtsp://cam.local/stream1",
        scale=(640, 360),
    )

    cmd = captured["cmd"]
    assert proc.stdout is None
    assert cmd[:4] == ["ffmpeg", "-loglevel", "error", "-nostdin"]
    assert "-rtsp_transport" in cmd
    assert "tcp" in cmd
    assert "-fflags" in cmd
    assert "nobuffer" in cmd
    assert "-vf" in cmd
    assert "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2" in cmd
    assert cmd[-7:] == ["-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "5", "pipe:1"]


def test_open_external_mjpeg_stream_supports_ffmpeg_readable_non_rtsp_stream(monkeypatch):
    captured = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            self.stdout = None

    monkeypatch.setattr("subprocess.Popen", FakePopen)

    open_external_mjpeg_stream("ffmpeg", "http://cam.local/mjpeg", scale=(640, 360))

    cmd = captured["cmd"]
    assert "-rtsp_transport" not in cmd
    assert "http://cam.local/mjpeg" in cmd
    assert cmd[-7:] == ["-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "5", "pipe:1"]


def test_iter_mjpeg_frames_extracts_jpegs_from_chunked_stream():
    class FakeStdout:
        def __init__(self):
            self.chunks = [
                b"noise\xff\xd8one",
                b"\xff\xd9middle\xff\xd8two",
                b"\xff\xd9tail",
                b"",
            ]

        def read(self, _size):
            return self.chunks.pop(0)

    class FakeProc:
        stdout = FakeStdout()

    assert list(iter_mjpeg_frames(FakeProc(), chunk_size=4)) == [
        b"\xff\xd8one\xff\xd9",
        b"\xff\xd8two\xff\xd9",
    ]


def test_iter_mjpeg_frames_stops_when_ffmpeg_stdout_stalls():
    read_started = threading.Event()
    release_read = threading.Event()

    class FakeStdout:
        def read(self, _size):
            read_started.set()
            release_read.wait(timeout=1.0)
            return b""

    class FakeProc:
        stdout = FakeStdout()

        def poll(self):
            return None

    try:
        assert list(iter_mjpeg_frames(FakeProc(), stale_timeout=0.01)) == []
        assert read_started.wait(timeout=0.5)
    finally:
        release_read.set()
