import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.Application.Exception.application_error import ProfileEmbeddingMissingError
from src.Infrastructure.Commands.match_missions import parse_args, main

_VALID_UUID = str(uuid4())


class TestParseArgs:
    def test_profile_id_required(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_profile_id_parsed(self):
        args = parse_args(["--profile-id", _VALID_UUID])
        assert args.profile_id == _VALID_UUID

    def test_default_min_score(self):
        args = parse_args(["--profile-id", _VALID_UUID])
        assert args.min_score == 0.50

    def test_default_top_n(self):
        args = parse_args(["--profile-id", _VALID_UUID])
        assert args.top_n == 20

    def test_custom_min_score(self):
        args = parse_args(["--profile-id", _VALID_UUID, "--min-score", "0.70"])
        assert args.min_score == 0.70

    def test_custom_top_n(self):
        args = parse_args(["--profile-id", _VALID_UUID, "--top-n", "5"])
        assert args.top_n == 5


class TestMain:
    def test_success_passes_correct_args_to_run(self):
        with patch(
            "src.Infrastructure.Commands.match_missions._run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None
            main(["--profile-id", _VALID_UUID])
        from uuid import UUID
        mock_run.assert_awaited_once_with(UUID(_VALID_UUID), 0.50, 20)

    def test_custom_options_passed_to_run(self):
        with patch(
            "src.Infrastructure.Commands.match_missions._run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None
            main(["--profile-id", _VALID_UUID, "--min-score", "0.70", "--top-n", "5"])
        from uuid import UUID
        mock_run.assert_awaited_once_with(UUID(_VALID_UUID), 0.70, 5)

    def test_invalid_uuid_exits_with_code_1(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--profile-id", "not-a-uuid"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid UUID" in captured.err

    def test_profile_embedding_missing_exits_with_code_1(self, capsys):
        with patch(
            "src.Infrastructure.Commands.match_missions._run",
            side_effect=ProfileEmbeddingMissingError("no embedding"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main(["--profile-id", _VALID_UUID])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "no embedding" in captured.err

    def test_generic_error_exits_with_code_1(self, capsys):
        with patch(
            "src.Infrastructure.Commands.match_missions._run",
            side_effect=Exception("db connection refused"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main(["--profile-id", _VALID_UUID])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error while matching missions" in captured.err
        assert "db connection refused" in captured.err
