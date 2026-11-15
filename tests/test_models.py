import pytest
from pydantic import ValidationError

from article_writer.models import WriterSelectionInfo


def test_valid_selection():
    info = WriterSelectionInfo(which_writer="journalist_agent", reason="contested topic")
    assert info.which_writer == "journalist_agent"


def test_json_round_trip():
    info = WriterSelectionInfo.model_validate_json(
        '{"which_writer": "storyteller_agent", "reason": "human story"}')
    assert info.reason == "human story"


@pytest.mark.parametrize("data", [
    {},
    {"which_writer": "journalist_agent"},
    {"reason": "no writer"},
    {"which_writer": None, "reason": "x"},
])
def test_invalid_selection_is_rejected(data):
    with pytest.raises(ValidationError):
        WriterSelectionInfo(**data)
