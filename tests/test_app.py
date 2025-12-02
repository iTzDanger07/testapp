import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path/'test.db'}")
    app.config.update({"TESTING": True})
    client = app.test_client()

    with app.app_context():
        pass

    yield client


def test_owner_cannot_see_reservation_details(client):
    # create owner
    resp = client.post("/users", json={"name": "Owner", "email": "owner@example.com"})
    owner_id = resp.get_json()["id"]

    # create wishlist and item
    wishlist_resp = client.post("/wishlists", json={"title": "Birthday", "owner_id": owner_id})
    wishlist_id = wishlist_resp.get_json()["id"]
    item_resp = client.post(f"/wishlists/{wishlist_id}/items", json={"name": "Bike", "description": "Road bike"})
    item_id = item_resp.get_json()["id"]

    # reserve item as guest
    client.post(f"/items/{item_id}/reserve", json={"reserver_name": "Guest", "message": "Got it"})

    # owner views wishlist and should not see reservation data
    view_resp = client.get(f"/wishlists/{wishlist_id}?viewer_id={owner_id}")
    data = view_resp.get_json()
    assert data["items"][0].get("reserved") is None
    assert data["items"][0].get("reserved_by") is None

    # owner cannot access reservation endpoint
    owner_reservation = client.get(f"/items/{item_id}/reservation?viewer_id={owner_id}")
    assert owner_reservation.status_code == 403


def test_guests_can_see_reservation_status_and_prevent_double_booking(client):
    resp = client.post("/users", json={"name": "Owner", "email": "owner2@example.com"})
    owner_id = resp.get_json()["id"]

    wishlist_resp = client.post("/wishlists", json={"title": "Holiday", "owner_id": owner_id})
    wishlist_id = wishlist_resp.get_json()["id"]
    item_resp = client.post(f"/wishlists/{wishlist_id}/items", json={"name": "Camera"})
    item_id = item_resp.get_json()["id"]

    # guest can see availability
    guest_view = client.get(f"/wishlists/{wishlist_id}?viewer_id=999")
    assert guest_view.get_json()["items"][0]["reserved"] is False

    client.post(f"/items/{item_id}/reserve", json={"reserver_name": "Friend"})

    # second reservation attempt should fail
    conflict = client.post(f"/items/{item_id}/reserve", json={"reserver_name": "Another"})
    assert conflict.status_code == 409

    # guest can see reservation details
    res_details = client.get(f"/items/{item_id}/reservation?viewer_id=999")
    assert res_details.get_json()["reserved"] is True
    assert res_details.get_json()["reserver_name"] == "Friend"
