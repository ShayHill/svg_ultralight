"""Test functions in string_conversion.py.

:author: Shay Hill
:created: 2023-09-23
"""

# pyright: reportPrivateUsage=false
import itertools as it
import random
import string
from collections.abc import Iterator

import pytest

import svg_ultralight.string_conversion as mod

_FLOAT_ITERATIONS = 100


def random_floats() -> Iterator[float]:
    """Yield random float values within(-ish) precision limits.

    Value may exceed the precision limits of the system.
    """
    for _ in range(_FLOAT_ITERATIONS):
        yield random.uniform(1e-20, 1e20)


def low_numbers() -> Iterator[float]:
    """Yield random float values below precision limits.

    Value may exceed the precision limits of the system.
    """
    for _ in range(_FLOAT_ITERATIONS):
        yield random.uniform(1e-25, 1e-24)


def high_numbers() -> Iterator[float]:
    """Yield random float values above precision limits.

    Value may exceed the precision limits of the system.
    """
    for _ in range(_FLOAT_ITERATIONS):
        yield random.uniform(1e24, 1e25)


def random_ints() -> Iterator[int]:
    """Yield random integer values."""
    big_int = 2**63 - 1
    for _ in range(_FLOAT_ITERATIONS):
        yield random.randint(-big_int, big_int)


def random_numbers() -> Iterator[float]:
    """Yield random numbers values."""
    return it.chain(random_floats(), low_numbers(), high_numbers(), random_ints())


class TestFormatNuber:
    """Test format_number function."""

    def test_negative_zero(self):
        """Remove "-" from "-0"."""
        assert mod.format_number(-0.0000000001) == "0"

    def test_round_to_int(self):
        """Round to int if no decimal values !- 0."""
        assert mod.format_number(1.0000000001) == "1"


class TestFormatNumbers:
    """Test format_numbers function."""

    def test_empty(self):
        """Return empty list."""
        assert mod.format_numbers([]) == []

    def test_explicit(self):
        """Return list of formatted strings."""
        assert mod.format_numbers([1, 2, 3]) == ["1", "2", "3"]


class TestFormatAttrDict:
    """Test format_attr_dict function."""

    def test_float(self):
        """Return string of float."""
        assert mod.format_attr_dict(x=1.0) == {"x": "1"}

    def test_exponential_float(self):
        """Return string of float."""
        assert mod.format_attr_dict(x=1.0e-10) == {"x": "0"}

    def test_trailing_underscore(self):
        """Remove trailing underscore from key."""
        assert mod.format_attr_dict(x_=1) == {"x": "1"}

    def test_replace_underscore(self):
        """Replace underscore with hyphen."""
        assert mod.format_attr_dict(x_y=1) == {"x-y": "1"}


def _generate_random_utf8_string():
    length = random.randint(11, 99)
    additional_chars = "éçüäößñáàâêëíìîïóòôõúùûñãõåøæœçÿžčšćđž"
    characters = (
        string.ascii_letters
        + string.digits
        + string.punctuation
        + string.whitespace
        + additional_chars
    )
    return "".join(random.choice(characters) for _ in range(length))


@pytest.fixture(params=range(100))
def random_utf8_string(request: pytest.FixtureRequest) -> str:
    """Generate a random UTF-8 string for testing."""
    _ = request.param
    return _generate_random_utf8_string()


class TestEncodeCssClassName:
    """Test encode_to_css_class_name and decode_from_css_class_name functions."""

    def test_encode_decode(self, random_utf8_string: str):
        """Encode - decode will return the original string."""
        encoded = mod.encode_to_css_class_name(random_utf8_string)
        decoded = mod.decode_from_css_class_name(encoded)
        assert decoded == random_utf8_string, (
            f"Decoded string '{decoded}' does not match original '{random_utf8_string}'"
        )

    def test_encode_valid(self, random_utf8_string: str):
        """All encoded strings will be ascii, _, and -."""
        encoded = mod.encode_to_css_class_name(random_utf8_string)
        assert all(c.isascii() or c in {"_", "-"} for c in encoded)
