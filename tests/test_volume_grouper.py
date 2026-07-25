import pytest

from src.volume_grouper import VolumeGroup, VolumeGrouper


@pytest.mark.asyncio
async def test_groups_tickers_and_skips_malformed_rows() -> None:
    grouper = VolumeGrouper()
    await grouper.refresh_groups(
        [
            {"symbol": "HIGHUSDT", "quoteVolume": "100000000"},
            {"symbol": "MIDUSDT", "quoteVolume": "10000000"},
            {"symbol": "LOWUSDT", "quoteVolume": "500000"},
            {"symbol": "SMALLUSDT", "quoteVolume": "499999"},
            {"symbol": "BROKENUSDT"},
        ],
        [],
    )

    assert grouper.get_group_info("HIGHUSDT", "spot").group is VolumeGroup.HIGH
    assert grouper.get_group_info("MIDUSDT", "spot").group is VolumeGroup.MID
    assert grouper.get_group_info("LOWUSDT", "spot").group is VolumeGroup.LOW
    assert grouper.get_group_info("SMALLUSDT", "spot") is None
    assert grouper.get_group_info("BROKENUSDT", "spot") is None


def test_unknown_market_fails_closed() -> None:
    grouper = VolumeGrouper()
    with pytest.raises(ValueError):
        grouper.get_all_symbols("options")


def test_thresholds_must_be_positive() -> None:
    grouper = VolumeGrouper()
    with pytest.raises(ValueError):
        grouper.update_spot_thresholds(2.5, 6.0, 0)
