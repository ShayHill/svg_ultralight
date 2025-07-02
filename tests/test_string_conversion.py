"""Test functions in string_conversion.py.

:author: Shay Hill
:created: 2023-09-23
"""

# pyright: reportPrivateUsage=false
import random
import itertools as it
import string
from collections.abc import Iterator
from decimal import Decimal

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
        yield random.uniform(1e+24, 1e+25)


def random_ints() -> Iterator[int]:
    """Yield random integer values."""
    big_int = 2**63 - 1
    for _ in range(_FLOAT_ITERATIONS):
        yield random.randint(-big_int, big_int)

def random_numbers() -> Iterator[float]:
    """Yield random numbers values."""
    return it.chain(random_floats(), low_numbers(), high_numbers(), random_ints())


class TestFormatNuber:
    def test_negative_zero(self):
        """Remove "-" from "-0"."""
        assert mod.format_number(-0.0000000001) == "0"

    def test_round_to_int(self):
        """Round to int if no decimal values !- 0."""
        assert mod.format_number(1.0000000001) == "1"




class TestFormatNumbers:
    def test_empty(self):
        """Return empty list."""
        assert mod.format_numbers([]) == []

    def test_explicit(self):
        """Return list of formatted strings."""
        assert mod.format_numbers([1, 2, 3]) == ["1", "2", "3"]

    @pytest.mark.parametrize("num", random_numbers())
    def test_exp_vs_fp_notation(self, num: float):
        """Exponential and fp notation have the same value.

        The first assertion is a sanity check.
        """
        expect = float(str(num))
        assert expect == float(Decimal(num))
        assert expect == float(mod._format_as_fixed_point(str(num)))
        assert expect == float(mod._format_as_exponential(str(num)))

    @pytest.mark.parametrize("num", random_numbers())
    def test_exponent_integer_part_is_len_1_or_stripped(self, num: float):
        """Integer part is one digit."""
        exponential = mod._format_as_exponential(num)
        # Result is exactly one digit
        if "." not in exponential:
            assert exponential.lstrip("-").isdigit()
        # Result is nothing before decimal or one non-zero digit before decimal.
        integer = exponential.split(".")[0].lstrip("-")
        assert not integer or integer in "123456789"

class TestFormatNumbersInString:
    def test_empty(self):
        """Return empty string.."""
        assert mod.format_numbers_in_string("") == ""

    def test_no_numbers(self):
        """Return string with no changes."""
        assert mod.format_numbers_in_string("hello") == "hello"

    def test_numbers(self):
        """Return string with numbers formatted."""
        assert mod.format_numbers_in_string("1.0000000001") == "1"

    def test_skip_text(self):
        """Skip text."""
        key = "text"
        val = "1.000000000000000000"
        assert mod._fix_key_and_format_val(key, val) == (key, val)

    def test_skip_id(self):
        """Skip text."""
        key = "id"
        val = "1.000000000000000000"
        assert mod._fix_key_and_format_val(key, val) == (key, val)

    def test_skip_hex_colors(self):
        """Skip hex colors."""
        assert mod.format_numbers_in_string("#000000") == "#000000"


class TestFormatAttrDict:
    def test_float(self):
        """Return string of float."""
        assert mod.format_attr_dict(x=1.0) == {"x": "1"}

    def test_float_string(self):
        """Return string of float."""
        assert mod.format_attr_dict(x="1.0") == {"x": "1"}

    def test_exponential_float(self):
        """Return string of float."""
        assert mod.format_attr_dict(x="1.0e-10") == {"x": "0"}

    def test_exponential_float_string(self):
        """Return string of float."""
        assert mod.format_attr_dict(x=1.0e-10) == {"x": "0"}

    def test_datastring(self):
        """Find and format floats in a datastring."""
        assert mod.format_attr_dict(d="M1.0,0 Q -0,.33333333333 1,2z") == {
            "d": "M1,0 Q 0,.333333 1,2z"
        }

    def test_datastring_with_exponential_number(self):
        """Find and format floats in a datastring."""
        assert mod.format_attr_dict(d="M1.0,1.0e-10 Q -0,.33333333 1,2z") == {
            "d": "M1,0 Q 0,.333333 1,2z"
        }

    def test_format_string(self):
        """Format floats in a format SVG attribute string."""
        assert mod.format_attr_dict(transform="translate(1.0, -0) scale(1.0, 1.0)") == {
            "transform": "translate(1, 0) scale(1, 1)"
        }

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
    random_string = "".join(random.choice(characters) for _ in range(length))
    return random_string

@pytest.fixture(params=range(100))
def random_utf8_string(request: pytest.FixtureRequest) -> str:
    _ = request.param
    return _generate_random_utf8_string()


class TestEncodeCssClassName:
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
        assert all(c.isascii() or c in {'_', '-'} for c in encoded)
