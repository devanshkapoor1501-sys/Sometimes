import os
import re
from decimal import Decimal, InvalidOperation
from functools import wraps
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, session, url_for
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ORDER_STATUS_OPTIONS = ["pending", "preparing", "ready", "collected"]


app = Flask(__name__)
app.secret_key = "change-this-secret-key"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "your_mysql_password"
app.config["MYSQL_DATABASE"] = "college_canteen"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def get_db_connection():
    try:
        return mysql.connector.connect(
            host=app.config["MYSQL_HOST"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
            database=app.config["MYSQL_DATABASE"],
        )
    except Error as error:
        print(f"Database connection error: {error}")
        return None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def roles_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))

            if session.get("role") not in allowed_roles:
                flash("You do not have permission to access this page.", "error")
                if session.get("role") == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("menu"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = roles_required("admin")
student_required = roles_required("student")


def allowed_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(image_file):
    if not image_file or not image_file.filename:
        return None, None

    original_name = secure_filename(image_file.filename)
    if not original_name or not allowed_image_file(original_name):
        return None, "Upload a valid image file: PNG, JPG, JPEG, GIF, or WEBP."

    extension = original_name.rsplit(".", 1)[1].lower()
    generated_name = f"dish_{uuid4().hex}.{extension}"
    destination = os.path.join(app.config["UPLOAD_FOLDER"], generated_name)
    image_file.save(destination)
    return f"/static/images/uploads/{generated_name}", None


def remove_uploaded_image(image_path):
    if not image_path or not image_path.startswith("/static/images/uploads/"):
        return

    relative_path = image_path.replace("/static/images/uploads/", "", 1)
    full_path = os.path.normpath(os.path.join(app.config["UPLOAD_FOLDER"], relative_path))

    if full_path.startswith(os.path.normpath(app.config["UPLOAD_FOLDER"])) and os.path.exists(full_path):
        os.remove(full_path)


def is_valid_email(email):
    return bool(EMAIL_PATTERN.match(email))


def parse_price(raw_price):
    try:
        price = Decimal(raw_price)
    except (InvalidOperation, TypeError):
        return None

    if price <= 0:
        return None

    return price.quantize(Decimal("0.01"))


def default_dish_form_data():
    return {
        "name": "",
        "category": "",
        "price": "",
        "image": "",
        "availability": True,
    }


def validate_registration_form(name, email, password):
    errors = []

    if len(name) < 2 or len(name) > 100:
        errors.append("Name must be between 2 and 100 characters.")
    if not is_valid_email(email):
        errors.append("Enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")

    return errors


def validate_login_form(email, password):
    errors = []

    if not is_valid_email(email):
        errors.append("Enter a valid email address.")
    if not password:
        errors.append("Password is required.")

    return errors


def validate_dish_form(form):
    name = form.get("name", "").strip()
    category = form.get("category", "").strip()
    price_raw = form.get("price", "").strip()
    availability = bool(form.get("availability"))
    existing_image = form.get("existing_image", "").strip()

    errors = []
    price = parse_price(price_raw)

    if len(name) < 2 or len(name) > 120:
        errors.append("Dish name must be between 2 and 120 characters.")
    if len(category) < 2 or len(category) > 80:
        errors.append("Category must be between 2 and 80 characters.")
    if price is None:
        errors.append("Price must be a positive number.")

    dish_data = {
        "name": name,
        "category": category,
        "price": price_raw,
        "image": existing_image,
        "availability": availability,
    }

    return dish_data, price, errors


def fetch_featured_dishes(limit=3):
    connection = get_db_connection()
    if not connection:
        return []

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT * FROM dishes
        WHERE availability = TRUE
        ORDER BY category ASC, name ASC
        LIMIT %s
        """,
        (limit,),
    )
    dishes = cursor.fetchall()
    cursor.close()
    connection.close()
    return dishes


def fetch_available_dishes():
    connection = get_db_connection()
    if not connection:
        return []

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT * FROM dishes
        WHERE availability = TRUE
        ORDER BY category ASC, name ASC
        """
    )
    dishes = cursor.fetchall()
    cursor.close()
    connection.close()
    return dishes


def fetch_menu_categories():
    connection = get_db_connection()
    if not connection:
        return []

    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT category FROM dishes ORDER BY category ASC")
    categories = [row[0] for row in cursor.fetchall() if row[0]]
    cursor.close()
    connection.close()
    return categories


def fetch_menu_dishes(search_query="", category=""):
    connection = get_db_connection()
    if not connection:
        return []

    query = """
        SELECT * FROM dishes
        WHERE 1 = 1
    """
    params = []

    if search_query:
        wildcard = f"%{search_query.lower()}%"
        query += " AND (LOWER(name) LIKE %s OR LOWER(category) LIKE %s)"
        params.extend([wildcard, wildcard])

    if category:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY availability DESC, category ASC, name ASC"

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    dishes = cursor.fetchall()
    cursor.close()
    connection.close()
    return dishes


def fetch_all_dishes():
    connection = get_db_connection()
    if not connection:
        return []

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM dishes ORDER BY dish_id DESC")
    dishes = cursor.fetchall()
    cursor.close()
    connection.close()
    return dishes


def fetch_dish_by_id(dish_id):
    connection = get_db_connection()
    if not connection:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM dishes WHERE dish_id = %s", (dish_id,))
    dish = cursor.fetchone()
    cursor.close()
    connection.close()
    return dish


def fetch_dashboard_stats():
    stats = {
        "total_dishes": 0,
        "available_dishes": 0,
        "total_orders": 0,
        "pending_orders": 0,
    }

    connection = get_db_connection()
    if not connection:
        return stats

    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(availability = TRUE), 0) FROM dishes")
    dish_stats = cursor.fetchone()
    if dish_stats:
        stats["total_dishes"] = dish_stats[0]
        stats["available_dishes"] = dish_stats[1]

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(order_status = 'pending'), 0) FROM orders")
    order_stats = cursor.fetchone()
    if order_stats:
        stats["total_orders"] = order_stats[0]
        stats["pending_orders"] = order_stats[1]

    cursor.close()
    connection.close()
    return stats


def get_cart():
    if "cart" not in session:
        session["cart"] = {}
    return session["cart"]


def build_cart_details():
    cart = get_cart()
    if not cart:
        return {
            "items": [],
            "total_amount": 0.0,
            "total_quantity": 0,
            "has_unavailable_items": False,
        }

    dish_ids = [int(dish_id) for dish_id in cart.keys()]
    placeholders = ", ".join(["%s"] * len(dish_ids))

    connection = get_db_connection()
    if not connection:
        return {
            "items": [],
            "total_amount": 0.0,
            "total_quantity": 0,
            "has_unavailable_items": False,
        }

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"SELECT * FROM dishes WHERE dish_id IN ({placeholders})",
        tuple(dish_ids),
    )
    dishes = {str(dish["dish_id"]): dish for dish in cursor.fetchall()}
    cursor.close()
    connection.close()

    items = []
    valid_cart = {}
    total_amount = 0.0
    total_quantity = 0
    has_unavailable_items = False

    for dish_id, quantity in cart.items():
        dish = dishes.get(dish_id)
        if not dish:
            continue

        valid_cart[dish_id] = quantity
        subtotal = float(dish["price"]) * quantity
        total_amount += subtotal
        total_quantity += quantity
        has_unavailable_items = has_unavailable_items or not bool(dish["availability"])

        items.append(
            {
                "dish_id": dish["dish_id"],
                "name": dish["name"],
                "category": dish["category"],
                "price": float(dish["price"]),
                "image": dish["image"],
                "availability": bool(dish["availability"]),
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )

    if len(valid_cart) != len(cart):
        session["cart"] = valid_cart
        session.modified = True

    return {
        "items": items,
        "total_amount": total_amount,
        "total_quantity": total_quantity,
        "has_unavailable_items": has_unavailable_items,
    }


def fetch_orders(user_id=None):
    connection = get_db_connection()
    if not connection:
        return []

    cursor = connection.cursor(dictionary=True)
    base_query = """
        SELECT
            o.order_id,
            o.user_id,
            o.total_amount,
            o.payment_status,
            o.order_status,
            o.token_number,
            o.order_date,
            u.name AS student_name,
            u.email AS student_email
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
    """

    if user_id is not None:
        base_query += " WHERE o.user_id = %s ORDER BY o.order_date DESC, o.order_id DESC"
        cursor.execute(base_query, (user_id,))
    else:
        base_query += " ORDER BY o.order_date DESC, o.order_id DESC"
        cursor.execute(base_query)

    orders = cursor.fetchall()
    if not orders:
        cursor.close()
        connection.close()
        return []

    order_ids = [order["order_id"] for order in orders]
    placeholders = ", ".join(["%s"] * len(order_ids))
    cursor.execute(
        f"""
        SELECT
            oi.order_id,
            oi.quantity,
            oi.subtotal,
            COALESCE(d.name, 'Removed Dish') AS name,
            COALESCE(d.category, 'Unavailable') AS category,
            d.price,
            d.image
        FROM order_items oi
        LEFT JOIN dishes d ON d.dish_id = oi.dish_id
        WHERE oi.order_id IN ({placeholders})
        ORDER BY oi.order_id DESC, oi.order_item_id ASC
        """,
        tuple(order_ids),
    )
    item_rows = cursor.fetchall()
    cursor.close()
    connection.close()

    items_by_order = {}
    for item in item_rows:
        items_by_order.setdefault(item["order_id"], []).append(item)

    for order in orders:
        order["items"] = items_by_order.get(order["order_id"], [])

    return orders


def fetch_order_details(order_id, user_id=None):
    orders = fetch_orders(user_id)
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order, "items": order["items"]}
    return None


@app.context_processor
def inject_user():
    return {
        "current_user": {
            "user_id": session.get("user_id"),
            "name": session.get("name"),
            "role": session.get("role"),
        },
        "cart_count": sum(session.get("cart", {}).values()) if session.get("role") == "student" else 0,
    }


@app.errorhandler(404)
def page_not_found(error):
    return (
        render_template(
            "error.html",
            error_code=404,
            error_title="Page not found",
            error_message="The page you requested does not exist or has been moved.",
        ),
        404,
    )


@app.errorhandler(413)
def uploaded_file_too_large(error):
    flash("Uploaded image is too large. Maximum size is 2 MB.", "error")
    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/")
def home():
    available_dishes = fetch_available_dishes()
    return render_template(
        "home.html",
        featured_dishes=available_dishes[:3],
        available_count=len(available_dishes),
    )


@app.route("/menu")
def menu():
    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()
    return render_template(
        "menu.html",
        dishes=fetch_menu_dishes(search_query, selected_category),
        categories=fetch_menu_categories(),
        search_query=search_query,
        selected_category=selected_category,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    form_data = {"name": "", "email": ""}

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        form_data = {"name": name, "email": email}

        errors = validate_registration_form(name, email, password)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("register.html", form_data=form_data)

        connection = get_db_connection()
        if not connection:
            flash("Unable to connect to the database.", "error")
            return render_template("register.html", form_data=form_data)

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email is already registered.", "error")
            cursor.close()
            connection.close()
            return render_template("register.html", form_data=form_data)

        try:
            password_hash = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO users (name, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                (name, email, password_hash, "student"),
            )
            connection.commit()
        except Error as error:
            print(f"Registration error: {error}")
            connection.rollback()
            flash("Registration could not be completed.", "error")
            cursor.close()
            connection.close()
            return render_template("register.html", form_data=form_data)

        cursor.close()
        connection.close()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form_data=form_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    form_data = {"email": ""}

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        form_data = {"email": email}

        errors = validate_login_form(email, password)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("login.html", form_data=form_data)

        connection = get_db_connection()
        if not connection:
            flash("Unable to connect to the database.", "error")
            return render_template("login.html", form_data=form_data)

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash("Login successful.", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("menu"))

        flash("Invalid email or password.", "error")

    return render_template("login.html", form_data=form_data)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/orders")
@student_required
def my_orders():
    return render_template("my_orders.html", orders=fetch_orders(session["user_id"]))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        dishes=fetch_all_dishes(),
        stats=fetch_dashboard_stats(),
    )


@app.route("/admin/orders")
@admin_required
def admin_orders():
    return render_template(
        "admin_orders.html",
        orders=fetch_orders(),
        order_status_options=ORDER_STATUS_OPTIONS,
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("order_status", "").strip().lower()
    if status not in ORDER_STATUS_OPTIONS:
        flash("Invalid order status.", "error")
        return redirect(url_for("admin_orders"))

    connection = get_db_connection()
    if not connection:
        flash("Unable to connect to the database.", "error")
        return redirect(url_for("admin_orders"))

    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE orders SET order_status = %s WHERE order_id = %s",
            (status, order_id),
        )
        connection.commit()
    except Error as error:
        print(f"Order status update error: {error}")
        connection.rollback()
        flash("Order status could not be updated.", "error")
        cursor.close()
        connection.close()
        return redirect(url_for("admin_orders"))

    cursor.close()
    connection.close()
    flash("Order status updated successfully.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/dishes/add", methods=["GET", "POST"])
@admin_required
def add_dish():
    dish_data = default_dish_form_data()

    if request.method == "POST":
        dish_data, price, errors = validate_dish_form(request.form)
        image_path = None
        saved_image = None

        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            saved_image, image_error = save_uploaded_image(image_file)
            if image_error:
                errors.append(image_error)
            else:
                image_path = saved_image

        if errors:
            for error in errors:
                flash(error, "error")
            dish_data["image"] = image_path or ""
            return render_template("dish_form.html", form_title="Add Dish", dish=dish_data)

        connection = get_db_connection()
        if not connection:
            if saved_image:
                remove_uploaded_image(saved_image)
            flash("Unable to connect to the database.", "error")
            return render_template("dish_form.html", form_title="Add Dish", dish=dish_data)

        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO dishes (name, category, price, image, availability)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    dish_data["name"],
                    dish_data["category"],
                    price,
                    image_path,
                    dish_data["availability"],
                ),
            )
            connection.commit()
        except Error as error:
            print(f"Dish insert error: {error}")
            connection.rollback()
            if saved_image:
                remove_uploaded_image(saved_image)
            flash("Dish could not be added.", "error")
            cursor.close()
            connection.close()
            return render_template("dish_form.html", form_title="Add Dish", dish=dish_data)

        cursor.close()
        connection.close()
        flash("Dish added successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("dish_form.html", form_title="Add Dish", dish=dish_data)


@app.route("/admin/dishes/edit/<int:dish_id>", methods=["GET", "POST"])
@admin_required
def edit_dish(dish_id):
    existing_dish = fetch_dish_by_id(dish_id)
    if not existing_dish:
        flash("Dish not found.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        dish_data, price, errors = validate_dish_form(request.form)
        dish_data["image"] = request.form.get("existing_image", "").strip()

        image_file = request.files.get("image_file")
        new_image_path = None

        if image_file and image_file.filename:
            new_image_path, image_error = save_uploaded_image(image_file)
            if image_error:
                errors.append(image_error)

        if errors:
            if new_image_path:
                remove_uploaded_image(new_image_path)
            for error in errors:
                flash(error, "error")
            return render_template("dish_form.html", form_title="Edit Dish", dish=dish_data)

        final_image = new_image_path or dish_data["image"] or None
        connection = get_db_connection()
        if not connection:
            if new_image_path:
                remove_uploaded_image(new_image_path)
            flash("Unable to connect to the database.", "error")
            return render_template("dish_form.html", form_title="Edit Dish", dish=dish_data)

        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE dishes
                SET name = %s, category = %s, price = %s, image = %s, availability = %s
                WHERE dish_id = %s
                """,
                (
                    dish_data["name"],
                    dish_data["category"],
                    price,
                    final_image,
                    dish_data["availability"],
                    dish_id,
                ),
            )
            connection.commit()
        except Error as error:
            print(f"Dish update error: {error}")
            connection.rollback()
            if new_image_path:
                remove_uploaded_image(new_image_path)
            flash("Dish could not be updated.", "error")
            cursor.close()
            connection.close()
            return render_template("dish_form.html", form_title="Edit Dish", dish=dish_data)

        cursor.close()
        connection.close()

        if new_image_path and existing_dish.get("image") != new_image_path:
            remove_uploaded_image(existing_dish.get("image"))

        flash("Dish updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    dish_data = {
        "name": existing_dish["name"],
        "category": existing_dish["category"],
        "price": str(existing_dish["price"]),
        "image": existing_dish["image"] or "",
        "availability": bool(existing_dish["availability"]),
    }
    return render_template("dish_form.html", form_title="Edit Dish", dish=dish_data)


@app.route("/admin/dishes/delete/<int:dish_id>", methods=["POST"])
@admin_required
def delete_dish(dish_id):
    dish = fetch_dish_by_id(dish_id)
    if not dish:
        flash("Dish not found.", "error")
        return redirect(url_for("admin_dashboard"))

    connection = get_db_connection()
    if not connection:
        flash("Unable to connect to the database.", "error")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM dishes WHERE dish_id = %s", (dish_id,))
        connection.commit()
        remove_uploaded_image(dish.get("image"))
        flash("Dish deleted successfully.", "success")
    except Error:
        connection.rollback()
        flash("This dish is part of order history. Mark it out of stock instead of deleting it.", "error")
    cursor.close()
    connection.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/dishes/toggle/<int:dish_id>", methods=["POST"])
@admin_required
def toggle_dish_availability(dish_id):
    connection = get_db_connection()
    if not connection:
        flash("Unable to connect to the database.", "error")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE dishes SET availability = NOT availability WHERE dish_id = %s",
            (dish_id,),
        )
        connection.commit()
    except Error as error:
        print(f"Availability toggle error: {error}")
        connection.rollback()
        flash("Dish availability could not be updated.", "error")
        cursor.close()
        connection.close()
        return redirect(url_for("admin_dashboard"))

    cursor.close()
    connection.close()
    flash("Dish availability updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/cart")
@student_required
def cart():
    return render_template("cart.html", cart_data=build_cart_details())


@app.route("/cart/add/<int:dish_id>", methods=["POST"])
@student_required
def add_to_cart(dish_id):
    dish = fetch_dish_by_id(dish_id)
    redirect_target = request.form.get("next_url", "").strip()

    if not redirect_target.startswith("/"):
        redirect_target = url_for("menu")

    if not dish:
        flash("Dish not found.", "error")
        return redirect(redirect_target)

    if not dish["availability"]:
        flash(f"{dish['name']} is currently out of stock.", "error")
        return redirect(redirect_target)

    cart_data = get_cart()
    dish_key = str(dish_id)
    cart_data[dish_key] = cart_data.get(dish_key, 0) + 1
    session["cart"] = cart_data
    session.modified = True

    flash(f"{dish['name']} added to cart.", "success")
    return redirect(redirect_target)


@app.route("/cart/update/<int:dish_id>", methods=["POST"])
@student_required
def update_cart(dish_id):
    quantity_raw = request.form.get("quantity", "1").strip()
    cart_data = get_cart()
    dish_key = str(dish_id)

    if dish_key not in cart_data:
        flash("Cart item not found.", "error")
        return redirect(url_for("cart"))

    try:
        quantity = int(quantity_raw)
    except ValueError:
        flash("Quantity must be a valid number.", "error")
        return redirect(url_for("cart"))

    if quantity <= 0:
        cart_data.pop(dish_key, None)
        flash("Item removed from cart.", "success")
    elif quantity > 20:
        flash("Quantity cannot be greater than 20.", "error")
        return redirect(url_for("cart"))
    else:
        cart_data[dish_key] = quantity
        flash("Cart updated.", "success")

    session["cart"] = cart_data
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:dish_id>", methods=["POST"])
@student_required
def remove_from_cart(dish_id):
    cart_data = get_cart()
    cart_data.pop(str(dish_id), None)
    session["cart"] = cart_data
    session.modified = True
    flash("Item removed from cart.", "success")
    return redirect(url_for("cart"))


@app.route("/payment")
@student_required
def payment():
    cart_data = build_cart_details()
    if not cart_data["items"]:
        flash("Your cart is empty.", "error")
        return redirect(url_for("menu"))

    return render_template("payment.html", cart_data=cart_data)


@app.route("/payment/process", methods=["POST"])
@student_required
def process_payment():
    cart_data = build_cart_details()
    if not cart_data["items"]:
        flash("Your cart is empty.", "error")
        return redirect(url_for("menu"))

    unavailable_items = [item["name"] for item in cart_data["items"] if not item["availability"]]
    if unavailable_items:
        flash("Some items in your cart are out of stock. Remove them before checkout.", "error")
        return redirect(url_for("cart"))

    connection = get_db_connection()
    if not connection:
        flash("Unable to connect to the database.", "error")
        return redirect(url_for("payment"))

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COALESCE(MAX(token_number), 0) FROM orders")
        next_token = cursor.fetchone()[0] + 1

        cursor.execute(
            """
            INSERT INTO orders (user_id, total_amount, payment_status, order_status, token_number)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session["user_id"], cart_data["total_amount"], "paid", "pending", next_token),
        )
        order_id = cursor.lastrowid

        for item in cart_data["items"]:
            cursor.execute(
                """
                INSERT INTO order_items (order_id, dish_id, quantity, subtotal)
                VALUES (%s, %s, %s, %s)
                """,
                (order_id, item["dish_id"], item["quantity"], item["subtotal"]),
            )

        cursor.execute(
            """
            INSERT INTO payments (order_id, payment_method, payment_status, transaction_id)
            VALUES (%s, %s, %s, %s)
            """,
            (order_id, "simulated", "paid", f"TXN-{order_id}-{next_token}"),
        )

        connection.commit()
    except Error as error:
        print(f"Order creation error: {error}")
        connection.rollback()
        flash("Payment could not be completed.", "error")
        cursor.close()
        connection.close()
        return redirect(url_for("payment"))

    cursor.close()
    connection.close()

    session.pop("cart", None)
    flash("Payment successful. Your order has been placed.", "success")
    return redirect(url_for("order_confirmation", order_id=order_id))


@app.route("/order/confirmation/<int:order_id>")
@student_required
def order_confirmation(order_id):
    order_data = fetch_order_details(order_id, session["user_id"])
    if not order_data:
        flash("Order not found.", "error")
        return redirect(url_for("my_orders"))

    return render_template("order_confirmation.html", order_data=order_data)


if __name__ == "__main__":
    app.run(debug=True)
