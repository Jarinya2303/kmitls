import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import logging

def connect_db():
    return sqlite3.connect('database.db')

class Admin(UserMixin):
    def __init__(self, admin_id, name, email, phone, password):
        self.admin_id = admin_id
        self.name = name
        self.email = email
        self.phone = phone
        self.password = password
        self.user_type = 'admin'  # เพิ่ม user_type สำหรับ admin

    def get_id(self):
        return self.admin_id


class Driver(UserMixin):
    def __init__(self, driver_id, name, email, phone, license, password):
        self.driver_id = driver_id
        self.name = name
        self.email = email
        self.phone = phone
        self.license = license
        self.password = password
        self.user_type = 'driver'  # เพิ่ม user_type สำหรับ driver

    def get_id(self):
        return self.driver_id
def get_admin_by_email(email):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE email = ?", (email,))
        admin_data = cursor.fetchone()
        if admin_data:
            admin = Admin(*admin_data)
            admin.user_type = 'admin'  # กำหนด user_type เป็น 'admin'
            return admin
        return None


def get_driver_by_email(email):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM driver_users WHERE email = ?", (email,))
        driver_data = cursor.fetchone()
        if driver_data:
            driver = Driver(*driver_data)
            driver.user_type = 'driver'  # กำหนด user_type เป็น 'driver'
            return driver
        return None

def save_admin(name, email, phone, password):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO admin_users (name, email, phone, password) VALUES (?, ?, ?, ?)",
                           (name, email, phone, hashed_password))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        logging.error(f"Email {email} already exists.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Error saving admin: {e}")
        return False


def save_driver(name, email, phone, license, password):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO driver_users (name, email, phone, license, password) VALUES (?, ?, ?, ?, ?)",
                           (name, email, phone, license, hashed_password))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        logging.error(f"Email {email} already exists.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Error saving driver: {e}")
        return False


def save_customer(first_name, last_name, address, province, phone, latitude, longitude, coordinate):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO customers (first_name, last_name, address, phone, coordinate,latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (first_name, last_name, address,  phone, coordinate, latitude, longitude))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Error saving customer: {e}")
        return False




def save_product(brand, weight_per_bag, price):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (brand, weight_per_bag, price) VALUES (?, ?, ?)",
                           (brand, weight_per_bag, price))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Error saving product: {e}")
        return False

def save_route(first_name, last_name, address, phone, latitude, longitude, product, order):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO routes (first_name, last_name, address, phone, latitude, longitude, product, order) VALUES (?, ?, ?, ?, ?, ?)",
                           (first_name, last_name, address, phone, latitude, longitude, product, order))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Error saving route: {e}")
        return False

def get_places():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, latitude, longitude FROM customers")
        places = cursor.fetchall()
        return places

# ไม่มีการเรียกใช้งาน initialize_db() ในโค้ดนี้
