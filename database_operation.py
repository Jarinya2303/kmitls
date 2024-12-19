import sqlite3
from werkzeug.security import generate_password_hash
import logging
import datetime
from flask_login import UserMixin
# Connect to database
def connect_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Utility functions
def hashed_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256')


# ฟังก์ชันเปรียบเทียบรหัสผ่าน
def check_password(hashed_pw, password):
    return check_password_hash(hashed_pw, password)

# User class
class User(UserMixin):
    def __init__(self, user_id, user_type, name, email, phone, password=None, license=None):
        self.user_id = user_id
        self.user_type = user_type  # ใช้ user_type แทน role
        self.name = name
        self.email = email
        self.phone = phone
        self.password = password
        self.license = license  # สำหรับ driver ที่มี license เท่านั้น

    def get_id(self):
        return self.user_id

    def __repr__(self):
        return f"User({self.user_id}, {self.user_type}, {self.name}, {self.email})"


# Admin class (สืบทอดมาจาก User)
class Admin(User):
    def __init__(self, user_id, name, email, phone, password, can_delete=False):
        super().__init__(user_id, user_type="admin", name=name, email=email, phone=phone, password=password)
        self.can_delete = can_delete  # เพิ่ม can_delete เพื่อบ่งบอกว่าผู้ใช้แอดมินสามารถลบข้อมูลได้หรือไม่

# Driver class (สืบทอดมาจาก User)
class Driver(User):
    def __init__(self, user_id, name, email, phone, license, password):
        super().__init__(user_id, user_type="driver", name=name, email=email, phone=phone, license=license, password=password)



# ฟังก์ชันสร้าง dictionary ของผู้ใช้จากข้อมูลฐานข้อมูล
def create_admin_driver_from_dict(user, user_type):
    if user_type == 'admin':
        return Admin(
            user_id=user[0],
            name=user[1],
            email=user[2],
            phone=user[3],
            password=user[4]
        )
    elif user_type == 'driver':
        return Driver(
            user_id=user[0],
            name=user[1],
            email=user[2],
            phone=user[3],
            license=user[4],
            password=user[5]
        )
    else:
        raise ValueError("Invalid user type")



# ฟังก์ชันการดึงข้อมูลผู้ใช้จากอีเมล
# ฟังก์ชันดึงข้อมูลผู้ใช้จากอีเมล
def get_user_by_email(email):
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # ตรวจสอบในตาราง admin_users
        cursor.execute("SELECT * FROM admin_users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_type = user['user_type']
            if user_type == 'admin' and email == 'charoen@charoen.com':
                return Admin(user['id'], user['name'], user['email'], user['phone'], user['password'], can_delete=True)
            return Admin(user['id'], user['name'], user['email'], user['phone'], user['password'], can_delete=False)

        # ตรวจสอบในตาราง driver_users
        cursor.execute("SELECT * FROM driver_users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            return Driver(user['id'], user['name'], user['email'], user['phone'], user['license'], user['password'])

        return None  # ถ้าไม่พบผู้ใช้
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()


def register_user(user_data):
    """ฟังก์ชันสำหรับสมัครสมาชิก"""
    hashed_pw = generate_password_hash(user_data['password'], method='pbkdf2:sha256')  # แฮชรหัสผ่าน

    # ตรวจสอบ user_type จากอีเมล
    user_type = get_user_type_by_email(user_data['email'])

    # ตรวจสอบว่าอีเมลมีอยู่ในระบบหรือไม่
    existing_user = get_user_by_email(user_data['email'])
    if existing_user:
        print(f"Error: User with email {user_data['email']} already exists.")
        return

    try:
        with connect_db() as conn:
            cursor = conn.cursor()

            if user_type == 'admin' or user_type == 'admin_with_delete':  # สำหรับแอดมิน
                cursor.execute("INSERT INTO admin_users (name, email, phone, password, user_type) VALUES (?, ?, ?, ?, ?)",
                               (user_data['name'], user_data['email'], user_data['phone'], hashed_pw, user_type))

            elif user_type == 'driver':  # สำหรับคนขับ
                cursor.execute("INSERT INTO driver_users (name, email, phone, license, password, user_type) VALUES (?, ?, ?, ?, ?, ?)",
                               (user_data['name'], user_data['email'], user_data['phone'], user_data.get('license', None), hashed_pw, 'driver'))

            conn.commit()
            print(f"User {user_data['name']} registered successfully.")
    except sqlite3.Error as e:
        print(f"Error saving user: {e}")


def get_user_type_by_email(email):
    email = email.strip().lower()  # ลบช่องว่างและแปลงเป็นตัวพิมพ์เล็ก

    # กรณีที่อีเมลลงท้าย @charoen.com เป็นแอดมิน
    if email.endswith('@charoen.com'):
        if email == 'charoen@charoen.com':
            return 'admin_with_delete'  # แอดมินที่สามารถลบข้อมูลได้
        return 'admin'  # แอดมินทั่วไป

    # กรณีที่อีเมลลงท้าย @driver.com เป็นคนขับ
    elif email.endswith('@driver.com'):
        return 'driver'  # คนขับ

    # อีเมลอื่นๆ ถือว่าไม่สามารถสมัครได้
    return 'user'



# ฟังก์ชันตรวจสอบสิทธิ์ในการแก้ไขหรือลบข้อมูล
def can_edit_or_delete(user):
    if user.user_type == 'admin_with_delete':
        return True  # แอดมินที่สามารถลบข้อมูลได้ (charoen@charoen.com)
    return False  # แอดมินทั่วไปหรือผู้ใช้อื่นๆ จะไม่สามารถลบข้อมูลได้




# ฟังก์ชันดึงข้อมูลผู้ใช้จาก ID
def get_user_by_id(user_id):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if user:
                return create_admin_driver_from_dict(user, 'admin')
            cursor.execute("SELECT * FROM driver_users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            return create_admin_driver_from_dict(user, 'driver') if user else None
    except sqlite3.Error as e:
        print(f"Error fetching user by id: {e}")
        return None


# Customer management
def customer_exists(first_name, last_name):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM customers WHERE first_name = ? AND last_name = ?",
            (first_name, last_name)
        )
        return cursor.fetchone()[0] > 0



def insert_customer_to_database(customer):
    with connect_db() as conn:
        cursor = conn.cursor()

        # ตรวจสอบว่ามีชื่อซ้ำในฐานข้อมูลหรือไม่
        cursor.execute(
            "SELECT COUNT(*) FROM customers WHERE first_name = ? AND last_name = ?",
            (customer['first_name'], customer['last_name'])
        )
        result = cursor.fetchone()
        if result[0] > 0:
            raise ValueError("มีลูกค้าที่มีชื่อนี้อยู่ในระบบแล้ว")  # โยนข้อผิดพลาด

        # เพิ่มข้อมูลลูกค้าใหม่
        cursor.execute(
            "INSERT INTO customers (first_name, last_name, address, phone, coordinate,latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer['first_name'], customer['last_name'], customer['address'], customer['phone'],customer['coordinate'],customer['latitude'], customer['longitude'])
        )
        conn.commit()
        print("ข้อมูลลูกค้าถูกบันทึกลงฐานข้อมูลแล้ว")



def edit_customer_in_database(customer_id, customer):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE customers SET first_name=?, last_name=?, address=?, phone=?, coordinate=?,latitude=?, longitude=? WHERE id=?",
            (customer['first_name'], customer['last_name'], customer['address'], customer['phone'], customer['coordinate'],customer['latitude'], customer['longitude'], customer_id)
        )
        conn.commit()
        print(f"อัปเดตข้อมูลลูกค้าหมายเลข {customer_id} แล้ว")


def delete_customer_in_database(customer_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        conn.commit()
        print(f"ลบข้อมูลลูกค้าหมายเลข {customer_id} แล้ว")



def get_customer_from_database():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers")
        rows = cursor.fetchall()
        print(f"พบข้อมูลลูกค้าจำนวน: {len(rows)}")  # ตรวจสอบจำนวนลูกค้า
        customers = [
            {
                "id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "address": row[3],
                "phone": row[4],
                "coordinate": row[5],
                "latitude": row[6],
                "longitude": row[7],
                
            }
            for row in rows
        ]
        return customers



def get_customer_by_id(customer_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "address": row[3],
                "phone": row[4],
                "coordinate": row[5],
                "latitude": row[6],
                "longitude": row[7],
            }
        else:
            return None  # กรณีไม่พบข้อมูล


# Product management
def get_products_from_database():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        return cursor.fetchall()

def insert_product_to_database(product):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (brand, weight_per_bag, price) VALUES (?, ?, ?)",
            (product['brand'], product['weight_per_bag'], product['price'])
        )
        conn.commit()

def edit_product_in_database(product_id, product):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET brand=?, weight_per_bag=?, price=? WHERE id=?",
            (product['brand'], product['weight_per_bag'], product['price'], product_id)
        )
        conn.commit()

def delete_product_in_database(product_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()

def drop_and_recreate_table():
    conn = None
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        logging.debug("Connected to the database.")

        # ลบตาราง routes หากมีอยู่
        cursor.execute('DROP TABLE IF EXISTS routes')

        logging.debug("Dropped the existing 'routes' table.")

        # สร้างตารางใหม่
        cursor.execute(''' 
            CREATE TABLE routes (
                first_name TEXT,
                last_name TEXT,
                address TEXT,
                phone TEXT,
                latitude REAL,
                longitude REAL,
                date DATE,
                product TEXT,
                order_id TEXT,
                group_id INTEGER,
                total_distance REAL
            )
        ''')

        logging.debug("Created a new 'routes' table.")

        # บันทึกการเปลี่ยนแปลงในฐานข้อมูล
        conn.commit()
        logging.debug("Changes committed to the database.")

    except sqlite3.Error as e:
        logging.error("Database error: %s", str(e))
        # ถ้ามีข้อผิดพลาด ให้ rollback การทำงาน
        if conn:
            conn.rollback()

    except Exception as e:
        logging.error("Unexpected error: %s", str(e))

    finally:
        if conn:
            conn.close()
            logging.debug("Database connection closed.")

# Map management
def sendMapToDatabase(group_id, ordered_data, total_distance):
    conn = None
    try:
        # เชื่อมต่อกับฐานข้อมูล
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        logging.debug("Connected to database")

        # สร้างตารางหากยังไม่มี
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT,
                last_name TEXT,
                address TEXT,
                phone TEXT,
                latitude REAL,
                longitude REAL,
                date TEXT,
                product TEXT,
                order_id TEXT,
                group_id INTEGER,
                total_distance REAL
            )
        ''')

        # บันทึกข้อมูลลงฐานข้อมูล
        for row in ordered_data:
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            address = row.get('address', '').strip()
            # ตรวจสอบค่า phone ว่ามีหรือไม่ และแปลงให้เป็น string
            phone = row.get('phone', '').strip()  # แปลงให้เป็น string เสมอ
            latitude = row.get('latitude', 0.0)
            longitude = row.get('longitude', 0.0)
            date = row.get('date', '')
            product = row.get('product', '').strip()
            order_id = row.get('order_id', '').strip()

            # ตรวจสอบข้อมูลที่สำคัญ ถ้าขาดข้อมูลจะข้ามแถวนี้
            if not first_name or not order_id:
                logging.warning(f"Skipping row due to missing required data: {row}")
                continue

            # บันทึกข้อมูลลงฐานข้อมูล
            cursor.execute(''' 
                INSERT INTO routes (first_name, last_name, address, phone, latitude, longitude, date, product, order_id, group_id, total_distance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (first_name, last_name, address, phone, latitude, longitude, date, product, order_id, group_id, total_distance))

        # คอมมิตการเปลี่ยนแปลง
        conn.commit()
        logging.debug(f"Data committed to database for group_id {group_id}")

        # ดึงข้อมูลที่บันทึกจากฐานข้อมูลเพื่อส่งกลับมา
        cursor.execute(''' 
            SELECT first_name, last_name, address, phone, latitude, longitude, product, order_id, group_id, total_distance
            FROM routes WHERE group_id = ?
        ''', (group_id,))
        rows = cursor.fetchall()

        data = [
            {
                'first_name': row[0],
                'last_name': row[1],
                'address': row[2],
                'phone': row[3],
                'latitude': row[4],
                'longitude': row[5],
                'product': row[6],
                'order_id': row[7],
                'group_id': row[8],
                'total_distance': row[9]
            } for row in rows
        ]

        logging.debug(f"Data fetched for group_id {group_id}: {data}")

        # ส่งข้อมูลกลับในรูปแบบที่ใช้ในการแสดงแผนที่
        return {'status': 'success', 'message': 'Data successfully inserted into database', 'data': data}

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return {'status': 'error', 'message': f"Database error: {e}"}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {'status': 'error', 'message': f"Error: {e}"}
    finally:
        if conn:
            conn.close()
            logging.debug("Database connection closed")


def getMapFromDatabase():
    conn = None
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # ดึงข้อมูลจากวันที่ล่าสุดที่มีในฐานข้อมูล
        cursor.execute(''' 
            SELECT MAX(date) FROM routes
        ''')
        latest_date = cursor.fetchone()[0]

        if not latest_date:
            logging.info("No data found in the database.")
            return {'message': 'No data found'}

        logging.debug(f"Latest upload date: {latest_date}")

        # คิวรีข้อมูลจากฐานข้อมูลสำหรับวันที่ล่าสุด
        cursor.execute(''' 
            SELECT first_name, last_name, address, phone, latitude, longitude, product, order_id, group_id, total_distance
            FROM routes WHERE date = ?
        ''', (latest_date,))

        rows = cursor.fetchall()

        if not rows:
            logging.info("No data found for the latest upload date.")
            return {'message': 'No data found for the specified date.'}

        data = [
            {
                'first_name': row[0],
                'last_name': row[1],
                'address': row[2],
                'phone': row[3],
                'latitude': row[4],
                'longitude': row[5],
                'product': row[6],
                'order_id': row[7],
                'group_id': row[8],
                'total_distance': row[9]
            } for row in rows
        ]

        # จัดกลุ่มข้อมูลตาม group_id
        grouped_data = {}
        for item in data:
            group_id = item['group_id']
            if group_id not in grouped_data:
                grouped_data[group_id] = []
            grouped_data[group_id].append(item)

        logging.debug("Grouped data: %s", grouped_data)

        return {'grouped_data': grouped_data}

    except sqlite3.Error as db_error:
        logging.error("Database error while retrieving data: %s", db_error)
        return {'error': str(db_error)}

    except Exception as e:
        logging.error("Unexpected error while retrieving data: %s", e)
        return {'error': str(e)}

    finally:
        if conn:
            conn.close()
            logging.debug("Database connection closed")



# ฟังก์ชันเพื่อสร้างตารางในฐานข้อมูล
def initialize_db():
    with connect_db() as conn:
        # สร้างตาราง admin_users โดยใช้คอลัมน์ user_type
        conn.execute('''CREATE TABLE IF NOT EXISTS admin_users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            email TEXT UNIQUE NOT NULL,
                            phone TEXT,
                            password TEXT NOT NULL,
                            user_type TEXT NOT NULL)''')  # เปลี่ยนจาก role เป็น user_type

        # สร้างตาราง driver_users โดยใช้คอลัมน์ user_type
        conn.execute('''CREATE TABLE IF NOT EXISTS driver_users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            email TEXT UNIQUE,
                            phone TEXT,
                            license TEXT,
                            password TEXT,
                            user_type TEXT NOT NULL)''')  # เปลี่ยนจาก role เป็น user_type



        conn.execute('''CREATE TABLE IF NOT EXISTS customers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            first_name TEXT,
                            last_name TEXT,
                            address TEXT,
                            phone TEXT,
                            coordinate TEXT,
                            latitude REAL,
                            longitude REAL)''')

        conn.execute('''CREATE TABLE IF NOT EXISTS products (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            brand TEXT,
                            weight_per_bag REAL,
                            price REAL)''')

        conn.execute('''CREATE TABLE IF NOT EXISTS routes (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           first_name TEXT NOT NULL,
                           last_name TEXT NOT NULL,
                           address TEXT NOT NULL,
                           phone TEXT,
                           latitude REAL NOT NULL,
                           longitude REAL NOT NULL,
                           date TEXT NOT NULL,
                           product TEXT,
                           order_id INTEGER NOT NULL,  
                           group_id INTEGER NOT NULL,
                           total_distance REAL NOT NULL)''')       
# เรียกใช้งานฟังก์ชัน initialize_db เพื่อสร้างตาราง
initialize_db()
