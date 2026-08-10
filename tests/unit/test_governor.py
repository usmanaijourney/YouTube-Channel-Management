import asyncio

from master_orchestrator.governor import Governor


async def test_acquire_slot_grants_up_to_max():
    gov = Governor(max_slots=2)
    slot1 = await gov.acquire_slot("channel-001")
    slot2 = await gov.acquire_slot("channel-002")
    assert slot1 is not None
    assert slot2 is not None
    assert gov.active_count == 2


async def test_acquire_slot_denies_beyond_max():
    gov = Governor(max_slots=1)
    slot1 = await gov.acquire_slot("channel-001")
    slot2 = await gov.acquire_slot("channel-002")
    assert slot1 is not None
    assert slot2 is None


async def test_release_slot_frees_capacity():
    gov = Governor(max_slots=1)
    slot1 = await gov.acquire_slot("channel-001")
    assert await gov.acquire_slot("channel-002") is None

    released = await gov.release_slot(slot1)
    assert released is True
    assert gov.active_count == 0

    slot2 = await gov.acquire_slot("channel-002")
    assert slot2 is not None


async def test_release_unknown_slot_returns_false():
    gov = Governor(max_slots=1)
    assert await gov.release_slot("nonexistent") is False


async def test_active_channels_reports_who_holds_slots():
    gov = Governor(max_slots=3)
    await gov.acquire_slot("channel-001")
    await gov.acquire_slot("channel-002")
    assert sorted(gov.active_channels()) == ["channel-001", "channel-002"]


async def test_concurrent_acquire_never_exceeds_max_slots():
    gov = Governor(max_slots=3)
    results = await asyncio.gather(*[gov.acquire_slot(f"channel-{i}") for i in range(10)])
    granted = [r for r in results if r is not None]
    assert len(granted) == 3
    assert gov.active_count == 3
