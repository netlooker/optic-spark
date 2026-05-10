"""Tests for engine.py: model discovery, resolution mapping, singleton behaviour."""
import os
import importlib
import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────
# get_gguf_file
# ─────────────────────────────────────────────

class TestGetGgufFile:
    def test_exact_path_override_used_when_set_and_exists(self, tmp_path):
        gguf = tmp_path / "model.Q4_K_M.gguf"
        gguf.write_bytes(b"fake")

        with patch.dict(os.environ, {"GGUF_MODEL_PATH": str(gguf), "MODEL_PATH": str(tmp_path)}):
            import src.engine as engine
            importlib.reload(engine)
            assert engine.get_gguf_file() == str(gguf)

    def test_exact_path_override_ignored_when_file_missing(self, tmp_path):
        ghost = str(tmp_path / "ghost.gguf")

        with patch.dict(os.environ, {"GGUF_MODEL_PATH": ghost, "MODEL_PATH": str(tmp_path)}):
            import src.engine as engine
            importlib.reload(engine)
            result = engine.get_gguf_file()
            # Should fall through to auto-discovery and return None (no GGUF in tmp_path)
            assert result is None

    def test_auto_discovers_gguf_in_model_path(self, tmp_path):
        gguf = tmp_path / "Z-Image-Turbo-Q4_K_M.gguf"
        gguf.write_bytes(b"fake")

        with patch.dict(os.environ, {"GGUF_MODEL_PATH": "", "MODEL_PATH": str(tmp_path)}):
            import src.engine as engine
            importlib.reload(engine)
            result = engine.get_gguf_file()
            assert result == str(gguf)

    def test_returns_none_when_no_gguf_found(self, tmp_path):
        with patch.dict(os.environ, {"GGUF_MODEL_PATH": "", "MODEL_PATH": str(tmp_path)}):
            import src.engine as engine
            importlib.reload(engine)
            assert engine.get_gguf_file() is None


# ─────────────────────────────────────────────
# Resolution / aspect-ratio mapping
# ─────────────────────────────────────────────

class TestResolutionMapping:
    """Ensure every documented aspect ratio maps to the expected pixel dimensions."""

    EXPECTED = {
        "1:1":  (1024, 1024),
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "4:3":  (1024, 768),
        "3:4":  (768, 1024),
        "3:2":  (1200, 800),
        "2:3":  (800, 1200),
    }

    @pytest.mark.parametrize("ratio,expected", EXPECTED.items())
    def test_resolution(self, ratio, expected):
        """generate() must map the aspect ratio correctly before calling pipe."""
        import src.engine as engine
        importlib.reload(engine)

        captured = {}

        def fake_pipeline(**kwargs):
            captured["width"] = kwargs["width"]
            captured["height"] = kwargs["height"]
            img = MagicMock()
            img.save = MagicMock()
            result = MagicMock()
            result.images = [img]
            return result

        mock_pipe = MagicMock(side_effect=fake_pipeline)
        engine.pipeline = mock_pipe

        import io
        with patch("src.engine.io.BytesIO") as mock_buf_cls:
            buf = MagicMock()
            buf.getvalue.return_value = b"fake_bytes"
            mock_buf_cls.return_value = buf
            engine.generate(prompt="test", aspect_ratio=ratio, output_format="webp")

        assert captured["width"] == expected[0]
        assert captured["height"] == expected[1]

    def test_unknown_ratio_falls_back_to_1_1(self):
        import src.engine as engine
        importlib.reload(engine)

        captured = {}

        def fake_pipeline(**kwargs):
            captured["width"] = kwargs["width"]
            captured["height"] = kwargs["height"]
            img = MagicMock()
            img.save = MagicMock()
            result = MagicMock()
            result.images = [img]
            return result

        mock_pipe = MagicMock(side_effect=fake_pipeline)
        engine.pipeline = mock_pipe

        import io
        with patch("src.engine.io.BytesIO") as mock_buf_cls:
            buf = MagicMock()
            buf.getvalue.return_value = b"fake_bytes"
            mock_buf_cls.return_value = buf
            engine.generate(prompt="test", aspect_ratio="99:1", output_format="webp")

        assert captured["width"] == 1024
        assert captured["height"] == 1024
