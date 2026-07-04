import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from lib.tag_lifecycle import version_sort_key, is_cert, line_key


def test_version_sort_key_stable():
    assert version_sort_key("22.10.1") == (22, 10, 1, 0)
    assert version_sort_key("20.19.0") == (20, 19, 0, 0)
    assert version_sort_key("1.8.32.3") == (1, 8, 32, 0)


def test_version_sort_key_cert():
    assert version_sort_key("20.7-cert11") == (20, 7, 0, 11)
    assert version_sort_key("22.8-cert3") == (22, 8, 0, 3)


def test_version_sort_key_git_highest():
    assert version_sort_key("git") == (999, 0, 0, 0)
    assert version_sort_key("git-forky") == (999, 0, 0, 0)


def test_version_sort_key_orders_cert_numerically():
    assert version_sort_key("20.7-cert11") > version_sort_key("20.7-cert10")


def test_version_sort_key_raises_on_garbage():
    with pytest.raises(ValueError):
        version_sort_key("not-a-version")


def test_is_cert():
    assert is_cert("20.7-cert11") is True
    assert is_cert("22.10.1") is False


def test_line_key():
    assert line_key("22.10.1") == "22"
    assert line_key("23.4.1") == "23"
    assert line_key("20.7-cert11") == "20-cert"   # major only
    assert line_key("22.8-cert3") == "22-cert"
    assert line_key("1.8.32.3") == "1.8"          # legacy: major.minor
    assert line_key("1.2.40") == "1.2"
    assert line_key("10.12.4") == "10"
