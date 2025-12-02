import datetime
from typing import Optional

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError


def create_app(database_uri: Optional[str] = None) -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri or "sqlite:///wishlist.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db = SQLAlchemy(app)

    class User(db.Model):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)

        wishlists = db.relationship("Wishlist", backref="owner", cascade="all, delete")

    class Wishlist(db.Model):
        __tablename__ = "wishlists"
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

        items = db.relationship("Item", backref="wishlist", cascade="all, delete")

    class Item(db.Model):
        __tablename__ = "items"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text, nullable=True)
        wishlist_id = db.Column(db.Integer, db.ForeignKey("wishlists.id"), nullable=False)

        reservation = db.relationship("Reservation", backref="item", uselist=False, cascade="all, delete")

    class Reservation(db.Model):
        __tablename__ = "reservations"
        id = db.Column(db.Integer, primary_key=True)
        item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False, unique=True)
        reserver_name = db.Column(db.String(120), nullable=False)
        message = db.Column(db.Text, nullable=True)
        reserved_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def serialize_item(item: Item, is_owner_view: bool):
        reserved = item.reservation is not None
        payload = {
            "id": item.id,
            "name": item.name,
            "description": item.description,
        }
        if not is_owner_view:
            payload.update(
                {
                    "reserved": reserved,
                    "reserved_by": item.reservation.reserver_name if reserved else None,
                    "reserved_message": item.reservation.message if reserved else None,
                }
            )
        return payload

    @app.before_first_request
    def create_tables() -> None:
        db.create_all()

    @app.route("/users", methods=["POST"])
    def create_user():
        data = request.get_json(force=True)
        user = User(name=data.get("name"), email=data.get("email"))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Email already exists"}), 400
        return jsonify({"id": user.id, "name": user.name, "email": user.email}), 201

    @app.route("/wishlists", methods=["POST"])
    def create_wishlist():
        data = request.get_json(force=True)
        owner_id = data.get("owner_id")
        owner = User.query.get(owner_id)
        if not owner:
            return jsonify({"error": "Owner not found"}), 404
        wishlist = Wishlist(title=data.get("title"), owner=owner)
        db.session.add(wishlist)
        db.session.commit()
        return jsonify({"id": wishlist.id, "title": wishlist.title, "owner_id": owner.id}), 201

    @app.route("/wishlists/<int:wishlist_id>/items", methods=["POST"])
    def add_item(wishlist_id: int):
        wishlist = Wishlist.query.get(wishlist_id)
        if not wishlist:
            return jsonify({"error": "Wishlist not found"}), 404
        data = request.get_json(force=True)
        item = Item(name=data.get("name"), description=data.get("description"), wishlist=wishlist)
        db.session.add(item)
        db.session.commit()
        return jsonify({"id": item.id, "name": item.name, "description": item.description}), 201

    @app.route("/wishlists/<int:wishlist_id>", methods=["GET"])
    def view_wishlist(wishlist_id: int):
        wishlist = Wishlist.query.get(wishlist_id)
        if not wishlist:
            return jsonify({"error": "Wishlist not found"}), 404
        viewer_id = request.args.get("viewer_id", type=int)
        is_owner_view = viewer_id == wishlist.owner_id
        items = [serialize_item(item, is_owner_view) for item in wishlist.items]
        response = {"id": wishlist.id, "title": wishlist.title, "owner_id": wishlist.owner_id, "items": items}
        return jsonify(response)

    @app.route("/items/<int:item_id>/reserve", methods=["POST"])
    def reserve_item(item_id: int):
        item = Item.query.get(item_id)
        if not item:
            return jsonify({"error": "Item not found"}), 404
        viewer_id = request.args.get("viewer_id", type=int)
        if viewer_id and viewer_id == item.wishlist.owner_id:
            return jsonify({"error": "Owners cannot reserve their own items"}), 400
        if item.reservation:
            return jsonify({"error": "Item already reserved"}), 409
        data = request.get_json(force=True)
        reservation = Reservation(
            item=item,
            reserver_name=data.get("reserver_name"),
            message=data.get("message"),
        )
        db.session.add(reservation)
        db.session.commit()
        return (
            jsonify(
                {
                    "id": reservation.id,
                    "item_id": item.id,
                    "reserver_name": reservation.reserver_name,
                    "message": reservation.message,
                }
            ),
            201,
        )

    @app.route("/items/<int:item_id>/reservation", methods=["GET"])
    def get_reservation(item_id: int):
        item = Item.query.get(item_id)
        if not item:
            return jsonify({"error": "Item not found"}), 404
        viewer_id = request.args.get("viewer_id", type=int)
        if viewer_id == item.wishlist.owner_id:
            return jsonify({"error": "Owners cannot view reservation details"}), 403
        reservation = item.reservation
        if not reservation:
            return jsonify({"reserved": False})
        return jsonify(
            {
                "reserved": True,
                "reserver_name": reservation.reserver_name,
                "message": reservation.message,
                "reserved_at": reservation.reserved_at.isoformat(),
            }
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
