from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime
import math

app = Flask(__name__)

# Latest weight received from the ESP32 (grams)
latest_weight = None


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect("stockwise.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL,
            supplier TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id TEXT PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            transaction_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def home():
    conn = get_connection()

    total_products = conn.execute("""
        SELECT COUNT(*) FROM products
    """).fetchone()[0]

    total_quantity = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0) FROM products
    """).fetchone()[0]

    low_stock_count = conn.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE quantity <= minimum_stock
    """).fetchone()[0]

    total_suppliers = conn.execute("""
        SELECT COUNT(*) FROM suppliers
    """).fetchone()[0]

    total_transactions = conn.execute("""
        SELECT COUNT(*) FROM transactions
    """).fetchone()[0]

    products = conn.execute("""
        SELECT product_name, quantity, minimum_stock
        FROM products
        ORDER BY product_id
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_products=total_products,
        total_quantity=total_quantity,
        low_stock_count=low_stock_count,
        total_suppliers=total_suppliers,
        total_transactions=total_transactions,
        products=products
    )


# =========================================================
# PRODUCT REGISTRATION
# =========================================================

@app.route("/product-registration", methods=["GET", "POST"])
def product_registration():
    message = ""

    if request.method == "POST":
        product_id = request.form["product_id"].strip()
        product_name = request.form["product_name"].strip()
        category = request.form["category"].strip()
        price = request.form["price"]
        quantity = request.form["quantity"]
        minimum_stock = request.form["minimum_stock"]
        supplier = request.form["supplier"].strip()

        try:
            price = float(price)
            quantity = int(quantity)
            minimum_stock = int(minimum_stock)

            if (
                not math.isfinite(price)
                or price < 0
                or quantity < 0
                or minimum_stock < 0
            ):
                raise ValueError

        except ValueError:
            message = "Please enter valid numeric values."
        else:
            conn = get_connection()

            try:
                conn.execute("""
                    INSERT INTO products (
                        product_id,
                        product_name,
                        category,
                        price,
                        quantity,
                        minimum_stock,
                        supplier
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_id,
                    product_name,
                    category,
                    price,
                    quantity,
                    minimum_stock,
                    supplier
                ))

                conn.commit()
                message = "Product added successfully!"

            except sqlite3.IntegrityError:
                message = "Product ID already exists!"

            finally:
                conn.close()

    conn = get_connection()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY product_id
    """).fetchall()

    conn.close()

    return render_template(
        "product_registration.html",
        products=products,
        message=message,
        edit_product=None
    )


# =========================================================
# EDIT PRODUCT
# =========================================================

@app.route("/edit-product/<product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_connection()

    product = conn.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,)).fetchone()

    conn.close()

    if not product:
        return redirect(url_for("product_registration"))

    if request.method == "POST":
        product_name = request.form["product_name"].strip()
        category = request.form["category"].strip()
        supplier = request.form["supplier"].strip()

        try:
            price = float(request.form["price"])
            quantity = int(request.form["quantity"])
            minimum_stock = int(request.form["minimum_stock"])

            if (
                not math.isfinite(price)
                or price < 0
                or quantity < 0
                or minimum_stock < 0
            ):
                raise ValueError

        except ValueError:
            return redirect(
                url_for("edit_product", product_id=product_id)
            )

        conn = get_connection()

        conn.execute("""
            UPDATE products
            SET product_name = ?,
                category = ?,
                price = ?,
                quantity = ?,
                minimum_stock = ?,
                supplier = ?
            WHERE product_id = ?
        """, (
            product_name,
            category,
            price,
            quantity,
            minimum_stock,
            supplier,
            product_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("product_registration"))

    conn = get_connection()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY product_id
    """).fetchall()

    conn.close()

    return render_template(
        "product_registration.html",
        products=products,
        message="",
        edit_product=product
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route("/delete-product/<product_id>", methods=["POST"])
def delete_product(product_id):
    conn = get_connection()

    conn.execute("""
        DELETE FROM products
        WHERE product_id = ?
    """, (product_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("product_registration"))


# =========================================================
# SUPPLIER MANAGEMENT
# =========================================================

@app.route("/supplier-management", methods=["GET", "POST"])
def supplier_management():
    message = ""

    if request.method == "POST":
        supplier_id = request.form["supplier_id"].strip()
        supplier_name = request.form["supplier_name"].strip()
        contact = request.form["contact"].strip()
        email = request.form["email"].strip()
        address = request.form["address"].strip()

        conn = get_connection()

        try:
            conn.execute("""
                INSERT INTO suppliers (
                    supplier_id,
                    supplier_name,
                    contact,
                    email,
                    address
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                supplier_id,
                supplier_name,
                contact,
                email,
                address
            ))

            conn.commit()
            message = "Supplier added successfully!"

        except sqlite3.IntegrityError:
            message = "Supplier ID already exists!"

        finally:
            conn.close()

    conn = get_connection()

    suppliers = conn.execute("""
        SELECT *
        FROM suppliers
        ORDER BY supplier_id
    """).fetchall()

    conn.close()

    return render_template(
        "supplier_management.html",
        suppliers=suppliers,
        message=message,
        edit_supplier=None
    )
# =========================================================
# EDIT SUPPLIER
# =========================================================

@app.route("/edit-supplier/<supplier_id>", methods=["GET", "POST"])
def edit_supplier(supplier_id):
    conn = get_connection()

    supplier = conn.execute("""
        SELECT *
        FROM suppliers
        WHERE supplier_id = ?
    """, (supplier_id,)).fetchone()

    conn.close()

    if not supplier:
        return redirect(url_for("supplier_management"))

    if request.method == "POST":
        supplier_name = request.form["supplier_name"].strip()
        contact = request.form["contact"].strip()
        email = request.form["email"].strip()
        address = request.form["address"].strip()

        conn = get_connection()

        conn.execute("""
            UPDATE suppliers
            SET supplier_name = ?,
                contact = ?,
                email = ?,
                address = ?
            WHERE supplier_id = ?
        """, (
            supplier_name,
            contact,
            email,
            address,
            supplier_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("supplier_management"))

    conn = get_connection()

    suppliers = conn.execute("""
        SELECT *
        FROM suppliers
        ORDER BY supplier_id
    """).fetchall()

    conn.close()

    return render_template(
        "supplier_management.html",
        suppliers=suppliers,
        message="",
        edit_supplier=supplier
    )


# =========================================================
# DELETE SUPPLIER
# =========================================================

@app.route("/delete-supplier/<supplier_id>", methods=["POST"])
def delete_supplier(supplier_id):
    conn = get_connection()

    conn.execute("""
        DELETE FROM suppliers
        WHERE supplier_id = ?
    """, (supplier_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("supplier_management"))


# =========================================================
# PURCHASE ENTRY
# =========================================================

@app.route("/purchase-entry", methods=["GET", "POST"])
def purchase_entry():
    message = ""

    if request.method == "POST":
        product_id = request.form["product_id"].strip()

        try:
            purchase_quantity = int(
                request.form["purchase_quantity"]
            )
        except ValueError:
            purchase_quantity = 0

        conn = get_connection()

        product = conn.execute("""
            SELECT product_name, quantity
            FROM products
            WHERE product_id = ?
        """, (product_id,)).fetchone()

        if not product:
            message = "Product ID not found!"

        elif purchase_quantity <= 0:
            message = "Purchase quantity must be greater than 0."

        else:
            new_quantity = product["quantity"] + purchase_quantity

            conn.execute("""
                UPDATE products
                SET quantity = ?
                WHERE product_id = ?
            """, (new_quantity, product_id))

            conn.execute("""
                INSERT INTO transactions (
                    transaction_type,
                    product_id,
                    product_name,
                    quantity,
                    transaction_date
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                "PURCHASE",
                product_id,
                product["product_name"],
                purchase_quantity,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()

            message = (
                f"Purchase added successfully! "
                f"{product['product_name']} stock "
                f"updated to {new_quantity}."
            )

        conn.close()

    return render_template(
        "purchase_entry.html",
        message=message
    )


# =========================================================
# STOCK UPDATE
# =========================================================

@app.route("/stock-update", methods=["GET", "POST"])
def stock_update():
    message = ""

    if request.method == "POST":
        product_id = request.form["product_id"].strip()

        try:
            new_quantity = int(request.form["new_quantity"])
        except ValueError:
            new_quantity = -1

        conn = get_connection()

        product = conn.execute("""
            SELECT product_name, quantity
            FROM products
            WHERE product_id = ?
        """, (product_id,)).fetchone()

        if not product:
            message = "Product ID not found!"

        elif new_quantity < 0:
            message = "Quantity cannot be negative."

        else:
            old_quantity = product["quantity"]

            conn.execute("""
                UPDATE products
                SET quantity = ?
                WHERE product_id = ?
            """, (new_quantity, product_id))

            conn.execute("""
                INSERT INTO transactions (
                    transaction_type,
                    product_id,
                    product_name,
                    quantity,
                    transaction_date
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                "STOCK ADJUSTMENT",
                product_id,
                product["product_name"],
                new_quantity - old_quantity,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()

            message = (
                f"Stock updated successfully! "
                f"{product['product_name']} quantity "
                f"is now {new_quantity}."
            )

        conn.close()

    return render_template(
        "stock_update.html",
        message=message
    )


# =========================================================
# SALES ENTRY
# =========================================================

@app.route("/sales-entry", methods=["GET", "POST"])
def sales_entry():
    message = ""

    if request.method == "POST":
        product_id = request.form["product_id"].strip()

        try:
            sales_quantity = int(request.form["sales_quantity"])
        except ValueError:
            sales_quantity = 0

        conn = get_connection()

        product = conn.execute("""
            SELECT product_name, quantity
            FROM products
            WHERE product_id = ?
        """, (product_id,)).fetchone()

        if not product:
            message = "Product ID not found!"

        elif sales_quantity <= 0:
            message = "Sales quantity must be greater than 0."

        elif sales_quantity > product["quantity"]:
            message = (
                f"Insufficient stock! "
                f"{product['product_name']} has only "
                f"{product['quantity']} units available."
            )

        else:
            new_quantity = product["quantity"] - sales_quantity

            conn.execute("""
                UPDATE products
                SET quantity = ?
                WHERE product_id = ?
            """, (new_quantity, product_id))

            conn.execute("""
                INSERT INTO transactions (
                    transaction_type,
                    product_id,
                    product_name,
                    quantity,
                    transaction_date
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                "SALE",
                product_id,
                product["product_name"],
                sales_quantity,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()

            message = (
                f"Sale added successfully! "
                f"{product['product_name']} stock "
                f"updated to {new_quantity}."
            )

        conn.close()

    return render_template(
        "sales_entry.html",
        message=message
    )


# =========================================================
# LOW STOCK ALERT
# =========================================================

@app.route("/low-stock-alert")
def low_stock_alert():
    conn = get_connection()

    products = conn.execute("""
        SELECT *
        FROM products
        WHERE quantity <= minimum_stock
        ORDER BY product_id
    """).fetchall()

    conn.close()

    return render_template(
        "low_stock_alert.html",
        products=products
    )


# =========================================================
# INVENTORY REPORTS
# =========================================================

@app.route("/inventory-reports")
def inventory_reports():
    conn = get_connection()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY product_id
    """).fetchall()

    total_products = conn.execute("""
        SELECT COUNT(*) FROM products
    """).fetchone()[0]

    total_quantity = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM products
    """).fetchone()[0]

    low_stock_count = conn.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE quantity <= minimum_stock
    """).fetchone()[0]

    total_inventory_value = conn.execute("""
        SELECT COALESCE(SUM(price * quantity), 0)
        FROM products
    """).fetchone()[0]

    conn.close()

    return render_template(
        "inventory_reports.html",
        products=products,
        total_products=total_products,
        total_quantity=total_quantity,
        low_stock_count=low_stock_count,
        total_inventory_value=total_inventory_value
    )


# =========================================================
# TRANSACTION HISTORY
# =========================================================

@app.route("/transaction-history")
def transaction_history():
    conn = get_connection()

    transactions = conn.execute("""
        SELECT *
        FROM transactions
        ORDER BY transaction_id DESC
    """).fetchall()

    total_transactions = conn.execute("""
        SELECT COUNT(*) FROM transactions
    """).fetchone()[0]

    total_purchases = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM transactions
        WHERE transaction_type = 'PURCHASE'
    """).fetchone()[0]

    total_sales = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM transactions
        WHERE transaction_type = 'SALE'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "transaction_history.html",
        transactions=transactions,
        total_transactions=total_transactions,
        total_purchases=total_purchases,
        total_sales=total_sales
    )


# =========================================================
# ESP32 WEIGHT API
# =========================================================

@app.route("/api/weight", methods=["POST"])
def receive_weight():
    global latest_weight

    data = request.get_json(silent=True) or {}

    try:
        weight = float(data.get("weight"))

        if not math.isfinite(weight):
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Send a valid weight value in grams."
        }), 400

    if not 0 <= weight <= 20000:
        return jsonify({
            "success": False,
            "message": "Weight must be between 0 and 20000 grams."
        }), 400

    latest_weight = round(weight, 1)

    print(f"ESP32 weight received: {latest_weight:.1f} g")

    return jsonify({
        "success": True,
        "weight": latest_weight,
        "unit": "g",
        "message": "Weight received successfully. Inventory was not changed."
    }), 200


@app.route("/api/weight", methods=["GET"])
def get_latest_weight():
    return jsonify({
        "success": True,
        "received": latest_weight is not None,
        "weight": latest_weight,
        "unit": "g",
        "message": (
            "Latest ESP32 reading"
            if latest_weight is not None
            else "Waiting for the first ESP32 reading"
        )
    }), 200

    # =========================================================
# WEIGHT-BASED INVENTORY COUNT
# =========================================================

@app.route("/weight-inventory", methods=["GET", "POST"])
def weight_inventory():
    global latest_weight

    message = ""
    success = False

    conn = get_connection()

    products = conn.execute("""
        SELECT product_id, product_name, quantity, price
        FROM products
        ORDER BY product_name
    """).fetchall()

    if request.method == "POST":

        product_id = request.form.get("product_id", "").strip()

        try:
            unit_weight = float(
                request.form.get("unit_weight", "")
            )
            tare_weight = float(
                request.form.get("tare_weight", "0")
            )

            if (
                not math.isfinite(unit_weight)
                or not math.isfinite(tare_weight)
            ):
                raise ValueError

        except (TypeError, ValueError):
            unit_weight = 0
            tare_weight = -1

        product = conn.execute("""
            SELECT product_id, product_name, quantity
            FROM products
            WHERE product_id = ?
        """, (product_id,)).fetchone()

        if not product:
            message = "Please select a valid product."

        elif unit_weight <= 0 or tare_weight < 0:
            message = "Enter valid package and tare weights."

        elif latest_weight is None:
            message = "No ESP32 reading received yet."

        elif latest_weight < tare_weight:
            message = "Measured weight is below the tare weight."

        else:
            net_weight = latest_weight - tare_weight

            calculated_quantity = int(
                net_weight // unit_weight
            )

            if calculated_quantity <= 0:
                message = (
                    "Weight is too low for one complete package."
                )

            else:
                # Save the calculated quantity only after
                # the user submits the confirmation form.
                old_quantity = product["quantity"]

                conn.execute("""
                    UPDATE products
                    SET quantity = ?
                    WHERE product_id = ?
                """, (
                    calculated_quantity,
                    product_id
                ))

                conn.execute("""
                    INSERT INTO transactions (
                        transaction_type,
                        product_id,
                        product_name,
                        quantity,
                        transaction_date
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    "WEIGHT STOCK COUNT",
                    product_id,
                    product["product_name"],
                    calculated_quantity - old_quantity,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ))

                conn.commit()

                success = True

                message = (
                    f"Stock updated successfully! "
                    f"{product['product_name']} quantity changed "
                    f"from {old_quantity} to "
                    f"{calculated_quantity} packages."
                )
            conn.close()

    return render_template(
        "weight_inventory.html",
        products=products,
        latest_weight=latest_weight,
        message=message,
        success=success
    )
# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)