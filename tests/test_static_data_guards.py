import hashlib
import json

from cli.countrycodes import country_codes


def test_countrycodes_snapshot_guard():
    normalized = json.dumps(country_codes, sort_keys=True, separators=(",", ":"))
    by_code = {entry["c"]: entry["n"] for entry in country_codes}

    assert len(country_codes) == 249
    assert by_code["DE"] == "Germany"
    assert by_code["US"] == "United States"
    assert by_code["JP"] == "Japan"
    assert hashlib.sha256(normalized.encode()).hexdigest() == "efe89ec0eb41a86eeb0b1254ccc5c8f3868f1194120984d8b306584a7d11a037"
