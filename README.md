# Wishlist Reservation API

A small Flask API for managing wishlists where guests can view and reserve items while keeping purchases hidden from the wishlist owner.

## Features
- Create users and wishlists
- Add items to a wishlist
- Let guests view availability and reserve items
- Hide reservation details from the wishlist owner to preserve surprises

## Setup
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   flask --app app run
   ```
   The API will start on `http://127.0.0.1:5000`.

## Key Endpoints
- `POST /users` — create a user. Body: `{ "name": "Alice", "email": "alice@example.com" }`
- `POST /wishlists` — create a wishlist. Body: `{ "title": "Birthday", "owner_id": 1 }`
- `POST /wishlists/<wishlist_id>/items` — add an item. Body: `{ "name": "Camera", "description": "Mirrorless" }`
- `GET /wishlists/<wishlist_id>?viewer_id=<id>` — view a wishlist. Owners do **not** see reservation details; guests do.
- `POST /items/<item_id>/reserve?viewer_id=<id>` — reserve an item as a guest.
- `GET /items/<item_id>/reservation?viewer_id=<id>` — view reservation details (blocked for owners).

## Testing
Install dev dependencies and run pytest:
```bash
pip install -r requirements.txt
pip install pytest
pytest
```
