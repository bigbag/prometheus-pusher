import tomllib
from pathlib import Path


def test_project_metadata_declares_the_1_0_support_policy() -> None:
    with Path("pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]

    assert project["version"] == "1.0.0"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == ["prometheus-client>=0.23,<1"]
