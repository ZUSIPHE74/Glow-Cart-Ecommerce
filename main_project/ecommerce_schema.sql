-- GlowCart Database Schema
-- This file shows what the database structure looks like in SQL format.
-- Django creates these tables automatically through migrations.

-- Store table
CREATE TABLE ecommerce_store (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    owner_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (owner_id) REFERENCES auth_user(id)
);

-- Product table
CREATE TABLE ecommerce_product (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    store_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    image_url VARCHAR(500),
    FOREIGN KEY (store_id) REFERENCES ecommerce_store(id)
);

-- Order table
CREATE TABLE ecommerce_order (
    id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    total_amount DECIMAL(10, 2) DEFAULT 0,
    shipping_address TEXT NOT NULL,
    invoice_sent BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (buyer_id) REFERENCES auth_user(id)
);

-- Order Item table
CREATE TABLE ecommerce_orderitem (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price_at_time DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES ecommerce_order(id),
    FOREIGN KEY (product_id) REFERENCES ecommerce_product(id)
);

-- Review table
CREATE TABLE ecommerce_review (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT NOT NULL,
    comment TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    UNIQUE (product_id, user_id),
    FOREIGN KEY (product_id) REFERENCES ecommerce_product(id),
    FOREIGN KEY (user_id) REFERENCES auth_user(id)
);
