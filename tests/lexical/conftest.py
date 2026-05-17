"""Bridge conftest for tests/lexical/.

When a test requests the `fake_driver` fixture, this module monkeypatches
`ingest.lexical._common.get_lexical_driver` (and any per-adapter local
import of the same symbol) to return that test's FakeDriver instance.
It also stubs `neo4j.GraphDatabase` so adapters that bypass the helper
and call GraphDatabase.driver directly also land on the FakeDriver.
Tests that do not use fake_driver are unaffected (autouse guard at top).
"""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

_ADAPTER_NAMES = [
    "bhsa",
    "coptic_scriptorium",
    "etcbc_parallels",
    "etcbc_phono",
    "macula_greek",
    "macula_hebrew",
    "morphgnt",
    "open_cbgm_3_john",
    "openbible",
    "oshb",
    "peshitta",
    "stepbible_morph_codes",
    "stepbible_proper_nouns",
    "stepbible_tagnt",
    "stepbible_tahot",
    "stepbible_tbesg",
    "stepbible_tbesh",
    "stepbible_tflsj",
    "stepbible_ttesv",
    "stepbible_tvtms",
    "theographic",
    "tsk",
    "vulgate_clementine",
]


class _FakeGraphDatabase:
    """Minimal neo4j.GraphDatabase stand-in."""

    def __init__(self, fake_driver_instance: object) -> None:
        self._fd = fake_driver_instance

    def driver(self, *_args: object, **_kwargs: object) -> object:
        return self._fd


@pytest.fixture(autouse=True, scope="function")
def _patch_lexical_driver(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect get_lexical_driver to the FakeDriver when it is in scope.

    If the current test does not use fake_driver, this fixture is a no-op
    so the 8 GROUP 2 fixture-validation tests continue to pass unmodified.
    """
    if "fake_driver" not in request.fixturenames:
        return

    fake_driver = request.getfixturevalue("fake_driver")

    monkeypatch.setattr(
        "ingest.lexical._common.get_lexical_driver",
        lambda _settings: fake_driver,
    )

    neo4j_stub = _FakeGraphDatabase(fake_driver)
    monkeypatch.setattr("neo4j.GraphDatabase", neo4j_stub, raising=False)

    for name in _ADAPTER_NAMES:
        module_path = f"ingest.lexical.{name}"
        mod = sys.modules.get(module_path)
        if mod is None:
            try:
                mod = importlib.import_module(module_path)
            except ImportError:
                continue
        if hasattr(mod, "get_lexical_driver"):
            monkeypatch.setattr(
                mod,
                "get_lexical_driver",
                lambda _settings: fake_driver,
                raising=False,
            )
