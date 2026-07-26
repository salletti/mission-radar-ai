import pytest
from unittest.mock import AsyncMock, patch

from src.Infrastructure.Commands.collect_posts import parse_args, main


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.query == "symfony freelance paris"
        assert args.limit == 10

    def test_custom_query(self):
        args = parse_args(["--query", "python freelance paris"])
        assert args.query == "python freelance paris"
        assert args.limit == 10

    def test_custom_limit(self):
        args = parse_args(["--limit", "5"])
        assert args.limit == 5

    def test_custom_query_and_limit(self):
        args = parse_args(["--query", "react freelance", "--limit", "3"])
        assert args.query == "react freelance"
        assert args.limit == 3

    def test_default_provider_is_mock(self):
        args = parse_args([])
        assert args.provider == "mock"

    def test_provider_mock(self):
        args = parse_args(["--provider", "mock"])
        assert args.provider == "mock"

    def test_provider_real(self):
        args = parse_args(["--provider", "real"])
        assert args.provider == "real"

    def test_save_flag_defaults_to_false(self):
        args = parse_args([])
        assert args.save is False

    def test_save_flag_set_to_true(self):
        args = parse_args(["--save"])
        assert args.save is True


class TestMain:
    def test_success_with_default_params(self):
        with patch(
            "src.Infrastructure.Commands.collect_posts._run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None
            main([])
        mock_run.assert_awaited_once_with("symfony freelance paris", 10, "mock", False, None)

    def test_success_with_custom_params(self):
        with patch(
            "src.Infrastructure.Commands.collect_posts._run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None
            main(["--query", "python freelance paris", "--limit", "5"])
        mock_run.assert_awaited_once_with("python freelance paris", 5, "mock", False, None)

    def test_provider_real_passed_to_run(self):
        with patch(
            "src.Infrastructure.Commands.collect_posts._run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None
            main(["--provider", "real"])
        mock_run.assert_awaited_once_with("symfony freelance paris", 10, "real", False, None)

    def test_save_flag_passed_to_run(self):
        with patch(
            "src.Infrastructure.Commands.collect_posts._run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None
            main(["--save"])
        mock_run.assert_awaited_once_with("symfony freelance paris", 10, "mock", True, None)

    def test_error_exits_with_code_1(self, capsys):
        with patch(
            "src.Infrastructure.Commands.collect_posts._run",
            side_effect=Exception("connection refused"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main([])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error while collecting posts" in captured.err
        assert "connection refused" in captured.err
