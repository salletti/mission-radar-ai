import pytest

from src.Domain.Exception.domain_exceptions import InvalidTJMError
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Domain.ValueObject.tjm import TJM


class TestTJM:
    def test_valid_tjm(self):
        tjm = TJM(amount=650.0)
        assert tjm.amount == 650.0
        assert tjm.currency == "EUR"
        assert tjm.unit == "day"

    def test_refuses_negative_amount(self):
        with pytest.raises(InvalidTJMError):
            TJM(amount=-100.0)

    def test_zero_is_valid(self):
        tjm = TJM(amount=0.0)
        assert tjm.amount == 0.0

    def test_custom_currency(self):
        tjm = TJM(amount=700.0, currency="USD")
        assert tjm.currency == "USD"

    def test_is_frozen(self):
        tjm = TJM(amount=600.0)
        with pytest.raises(Exception):
            tjm.amount = 700.0  # type: ignore[misc]




class TestStack:
    def test_normalizes_to_lowercase(self):
        stack = Stack.from_list(["Python", "FASTAPI"])
        assert "python" in stack.technologies
        assert "fastapi" in stack.technologies

    def test_deduplicates(self):
        stack = Stack.from_list(["Python", "python", "PYTHON"])
        assert stack.technologies == ("python",)

    def test_from_list_normalizes_and_deduplicates(self):
        stack = Stack.from_list(["Python", "FASTAPI", "python", "FastApi"])
        assert stack.technologies == ("fastapi", "python")

    def test_sorted_alphabetically(self):
        stack = Stack.from_list(["react", "python", "docker"])
        assert stack.technologies == ("docker", "python", "react")

    def test_contains(self):
        stack = Stack.from_list(["Python", "FastAPI"])
        assert stack.contains("Python") is True
        assert stack.contains("java") is False

    def test_len(self):
        stack = Stack.from_list(["python", "fastapi", "docker"])
        assert len(stack) == 3

    def test_is_frozen(self):
        stack = Stack.from_list(["python"])
        with pytest.raises(Exception):
            stack.technologies = ("java",)  # type: ignore[misc]


class TestContractType:
    def test_valid_values(self):
        assert ContractType("freelance")      == ContractType.FREELANCE
        assert ContractType("permanent")      == ContractType.PERMANENT
        assert ContractType("fixed_term")     == ContractType.FIXED_TERM
        assert ContractType("internship")     == ContractType.INTERNSHIP
        assert ContractType("apprenticeship") == ContractType.APPRENTICESHIP
        assert ContractType("unknown")        == ContractType.UNKNOWN

    def test_refuses_old_french_values(self):
        for v in ("cdi", "cdd"):
            with pytest.raises(ValueError):
                ContractType(v)

    def test_refuses_other_invalid_values(self):
        for v in ("consultant", "employee", "invalid_contract"):
            with pytest.raises(ValueError):
                ContractType(v)


class TestRemoteMode:
    def test_valid_values(self):
        assert RemoteMode("full_remote") == RemoteMode.FULL_REMOTE
        assert RemoteMode("hybrid") == RemoteMode.HYBRID
        assert RemoteMode("onsite") == RemoteMode.ONSITE
        assert RemoteMode("unknown") == RemoteMode.UNKNOWN

    def test_refuses_invalid_value(self):
        with pytest.raises(ValueError):
            RemoteMode("invalid_mode")
