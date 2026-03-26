CREATE DATABASE IF NOT EXISTS college_canteen;
USE college_canteen;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS dishes (
    dish_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    image VARCHAR(255),
    availability BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_status ENUM('pending', 'paid', 'failed', 'refunded') NOT NULL DEFAULT 'pending',
    order_status ENUM('pending', 'preparing', 'ready', 'collected') NOT NULL DEFAULT 'pending',
    token_number INT NOT NULL UNIQUE,
    order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    dish_id INT NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_dish
        FOREIGN KEY (dish_id) REFERENCES dishes(dish_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status ENUM('pending', 'paid', 'failed', 'refunded') NOT NULL DEFAULT 'pending',
    transaction_id VARCHAR(120),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE
);

INSERT INTO users (name, email, password, role)
VALUES
    ('Canteen Admin', 'admin@canteen.com', 'pbkdf2:sha256:600000$canteenadmin$0bc537c0ba00248664f44d73c349913ae60207bf27c927fccdd8bfaad8d5b573', 'admin'),
    ('Aarav Student', 'student@canteen.com', 'pbkdf2:sha256:600000$canteenstudent$c36b9c43207f7422674fd6dbbfb8e4d18203990c1f49301f9e9a8e4132735af6', 'student')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    password = VALUES(password),
    role = VALUES(role);

INSERT INTO dishes (name, category, price, image, availability)
SELECT 'Veg Burger', 'Fast Food', 85.00, NULL, TRUE
WHERE NOT EXISTS (SELECT 1 FROM dishes WHERE name = 'Veg Burger');

INSERT INTO dishes (name, category, price, image, availability)
SELECT 'Masala Dosa', 'South Indian', 60.00, NULL, TRUE
WHERE NOT EXISTS (SELECT 1 FROM dishes WHERE name = 'Masala Dosa');

INSERT INTO dishes (name, category, price, image, availability)
SELECT 'Cold Coffee', 'Beverages', 55.00, NULL, TRUE
WHERE NOT EXISTS (SELECT 1 FROM dishes WHERE name = 'Cold Coffee');

INSERT INTO dishes (name, category, price, image, availability)
SELECT 'Paneer Wrap', 'Snacks', 95.00, NULL, FALSE
WHERE NOT EXISTS (SELECT 1 FROM dishes WHERE name = 'Paneer Wrap');

INSERT INTO orders (user_id, total_amount, payment_status, order_status, token_number, order_date)
SELECT user_id, 145.00, 'paid', 'ready', 1001, NOW()
FROM users
WHERE email = 'student@canteen.com'
  AND NOT EXISTS (SELECT 1 FROM orders WHERE token_number = 1001);

INSERT INTO order_items (order_id, dish_id, quantity, subtotal)
SELECT o.order_id, d.dish_id, 1, 85.00
FROM orders o
JOIN dishes d ON d.name = 'Veg Burger'
WHERE o.token_number = 1001
  AND NOT EXISTS (
      SELECT 1 FROM order_items oi
      WHERE oi.order_id = o.order_id AND oi.dish_id = d.dish_id
  );

INSERT INTO order_items (order_id, dish_id, quantity, subtotal)
SELECT o.order_id, d.dish_id, 1, 60.00
FROM orders o
JOIN dishes d ON d.name = 'Masala Dosa'
WHERE o.token_number = 1001
  AND NOT EXISTS (
      SELECT 1 FROM order_items oi
      WHERE oi.order_id = o.order_id AND oi.dish_id = d.dish_id
  );

INSERT INTO payments (order_id, payment_method, payment_status, transaction_id)
SELECT o.order_id, 'simulated', 'paid', 'TXN-SAMPLE-1001'
FROM orders o
WHERE o.token_number = 1001
  AND NOT EXISTS (
      SELECT 1 FROM payments p
      WHERE p.order_id = o.order_id
  );
