"""
Tests for cleanupx_core package-level exports and status helpers.
"""

import cleanupx_core


class TestPackageMetadata:
    def test_version_is_string(self):
        assert isinstance(cleanupx_core.__version__, str)

    def test_version_non_empty(self):
        assert len(cleanupx_core.__version__) > 0

    def test_author_is_luke(self):
        assert "Luke" in cleanupx_core.__author__

    def test_license_is_mit(self):
        assert cleanupx_core.__license__ == "MIT"


class TestGetStatus:
    def test_returns_dict(self):
        status = cleanupx_core.get_status()
        assert isinstance(status, dict)

    def test_contains_version(self):
        status = cleanupx_core.get_status()
        assert "version" in status
        assert status["version"] == cleanupx_core.__version__

    def test_contains_availability_flags(self):
        status = cleanupx_core.get_status()
        assert "integrated_available" in status
        assert "xai_api_available" in status
        assert "legacy_available" in status

    def test_contains_module_path(self):
        status = cleanupx_core.get_status()
        assert "module_path" in status
        assert len(status["module_path"]) > 0

    def test_flags_are_booleans(self):
        status = cleanupx_core.get_status()
        for key in ("integrated_available", "xai_api_available", "legacy_available"):
            assert isinstance(status[key], bool), f"{key} should be bool"


class TestPrintStatus:
    def test_print_status_does_not_raise(self, capsys):
        # Should print without throwing
        cleanupx_core.print_status()
        captured = capsys.readouterr()
        assert "cleanupx" in captured.out.lower() or "Core" in captured.out
