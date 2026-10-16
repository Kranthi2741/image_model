CREATE DATABASE IF NOT EXISTS marketai;
USE marketai;

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    email       VARCHAR(255) NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,          -- bcrypt hash
    role        ENUM('admin','user') NOT NULL DEFAULT 'user',
    must_change  TINYINT(1) NOT NULL DEFAULT 1, -- 1 = force password setup on first login
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create the initial admin through the application using ADMIN_EMAIL and
-- ADMIN_INITIAL_PASSWORD environment variables. Never store credentials here.
