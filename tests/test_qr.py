"""Tests for ``qr-gen`` and ``qr-decode``."""

from __future__ import annotations

import io
import sys

import pytest

from toolscripts.commands.media import qr_decode, qr_gen


class _FakeTty(io.StringIO):
    def isatty(self) -> bool:
        return True


def _generate(monkeypatch, text: str, output) -> None:
    monkeypatch.setattr(sys, "argv", ["qr-gen", text, "-o", str(output)])
    qr_gen.main()


def test_gen_writes_png(tmp_path, monkeypatch):
    pytest.importorskip("segno")

    output = tmp_path / "code.png"
    _generate(monkeypatch, "hello world", output)

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_gen_prompts_for_output(tmp_path, monkeypatch):
    pytest.importorskip("segno")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", _FakeTty("mycode\n"))
    monkeypatch.setattr(sys, "argv", ["qr-gen", "hello"])
    qr_gen.main()

    assert (tmp_path / "mycode.png").exists()


def test_gen_defaults_to_out_png_on_empty_prompt(tmp_path, monkeypatch):
    pytest.importorskip("segno")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", _FakeTty("\n"))
    monkeypatch.setattr(sys, "argv", ["qr-gen", "hello"])
    qr_gen.main()

    assert (tmp_path / "out.png").exists()


def test_decode_single(tmp_path, monkeypatch, capsys):
    pytest.importorskip("segno")
    pytest.importorskip("zxingcpp")
    pytest.importorskip("PIL")

    output = tmp_path / "code.png"
    _generate(monkeypatch, "hello world", output)

    monkeypatch.setattr(sys, "argv", ["qr-decode", str(output)])
    qr_decode.main()

    assert capsys.readouterr().out == "hello world\n"


def test_decode_multiple(tmp_path, monkeypatch, capsys):
    pytest.importorskip("segno")
    pytest.importorskip("zxingcpp")
    Image = pytest.importorskip("PIL.Image")

    first_png = tmp_path / "first.png"
    second_png = tmp_path / "second.png"
    _generate(monkeypatch, "first payload", first_png)
    _generate(monkeypatch, "second payload", second_png)

    with Image.open(first_png) as first, Image.open(second_png) as second:
        first = first.convert("RGB")
        second = second.convert("RGB")
        canvas = Image.new(
            "RGB", (first.width + second.width + 20, max(first.height, second.height)), "white"
        )
        canvas.paste(first, (0, 0))
        canvas.paste(second, (first.width + 20, 0))
        combined = tmp_path / "combined.png"
        canvas.save(combined)

    monkeypatch.setattr(sys, "argv", ["qr-decode", str(combined)])
    qr_decode.main()

    assert set(capsys.readouterr().out.splitlines()) == {"first payload", "second payload"}


def test_decode_errors_when_no_qr(tmp_path, monkeypatch):
    pytest.importorskip("zxingcpp")
    Image = pytest.importorskip("PIL.Image")

    blank = tmp_path / "blank.png"
    Image.new("RGB", (100, 100), "white").save(blank)

    monkeypatch.setattr(sys, "argv", ["qr-decode", str(blank)])
    with pytest.raises(SystemExit) as exc:
        qr_decode.main()

    assert exc.value.code == 1
