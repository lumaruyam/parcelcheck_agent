from src.agent.vision import damage_type_from_facts as m


def test_mapping():
    assert m({"photo_usable": False, "packaging_damaged": True}) == "unclear_photo"
    assert m({"photo_usable": True, "item_visible": True, "item_damaged": True}) == "content_damaged"
    assert m({"photo_usable": True, "packaging_damaged": True, "item_visible": False}) == "packaging_only"
    assert m({"photo_usable": True, "packaging_damaged": False}) == "no_visible_damage"
    # an item that is not visible is never "content damaged", whatever Gemini says
    assert m({"photo_usable": True, "item_visible": False, "item_damaged": True}) == "no_visible_damage"
