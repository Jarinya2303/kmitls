import logging
import sqlite3
import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash
from database_operation import *
from form import CustomerForm, LoginForm, ProductForm, RegistrationForm
from model import *
from TSP_excel import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Connect to SQLite DB
def connect_db():
    return sqlite3.connect('database.db')

# ฟังก์ชันโหลดข้อมูลผู้ใช้
@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)  # ใช้ฟังก์ชันนี้เพื่อนำผู้ใช้จากฐานข้อมูลมา


# ฟังก์ชันโหลดข้อมูลผู้ใช้

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    flash_error = session.pop('flash_error', None)

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # ดึงข้อมูลผู้ใช้จากอีเมล
        user = get_user_by_email(email)

        if user is None or not check_password_hash(user.password, password):
            flash("อีเมลหรือรหัสผ่านไม่ถูกต้อง", "danger")
            return redirect(url_for('login'))

        login_user(user)  # ล็อกอินผู้ใช้

        # กำหนด user_type ใน session
        session['user_type'] = user.user_type  # เก็บ user_type ใน session

        # ตรวจสอบ user_type และนำทางไปยังหน้า dashboard ที่เหมาะสม
        if user.user_type == 'admin_with_delete':  # หากเป็นแอดมินที่สามารถลบข้อมูลได้
            return redirect(url_for('admin_dashboard'))  # ไปที่หน้าแดชบอร์ดของแอดมินที่สามารถลบข้อมูลได้
        elif user.user_type == 'admin':  # หากเป็นแอดมินทั่วไป
            return redirect(url_for('admin_dashboard'))  # ไปที่หน้าแดชบอร์ดของแอดมินทั่วไป
        elif user.user_type == 'driver':  # หากเป็นคนขับ
            return redirect(url_for('driver_dashboard'))  # ไปที่แดชบอร์ดของคนขับ
        else:  # สำหรับผู้ใช้ทั่วไป
            return redirect(url_for('user_dashboard'))  # ไปที่แดชบอร์ดของผู้ใช้ทั่วไป

    return render_template('login.html', form=form, flash_error=flash_error)
    



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    # ถ้าฟอร์มถูกส่งมาและผ่านการตรวจสอบ
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        phone = form.phone.data
        user_type = form.user_type.data
        license = form.license.data if user_type == 'driver' else None
        password = form.password.data

        # ตรวจสอบว่าอีเมลสามารถสมัครได้ไหม
        if get_user_by_email(email):
            return redirect(url_for('register'))

        # สร้างข้อมูลผู้ใช้ใหม่
        user_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'user_type': user_type,
            'license': license,
            'password': password
        }

        # บันทึกข้อมูลผู้ใช้ใหม่
        register_user(user_data)

        return redirect(url_for('login'))  # หรือไปที่หน้าอื่นที่ต้องการ

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@app.route('/home')
@login_required
def home():
    if current_user.user_type == 'admin':
        return render_template('admin_dashboard.html', user_type=current_user.user_type)  # Pass user_type to the template
    elif current_user.user_type == 'driver':
        return redirect(url_for('driver_dashboard'))  # Redirect to driver map view
    else:
        flash("ผู้ใช้ไม่ถูกต้อง", 'danger')
        return redirect(url_for('login'))



@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')  # Ensure this template exists

@app.route('/driver_dashboard')
@login_required
def driver_dashboard():
    return render_template('driver_dashboard.html')  # Ensure this template exists




# Customers
@app.route('/customer_list', methods=['GET'])
@login_required
def customer_list():
    search_query = request.args.get('search', '')
    customers = get_customer_from_database()
    if search_query:
        customers = [
            c for c in customers if search_query.lower() in (c["first_name"].lower() + " " + c["last_name"].lower())
        ]
    return render_template('customer_list.html', customers=customers, search_query=search_query)


@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        new_customer = {
            "first_name": form.first_name.data,
            "last_name": form.last_name.data,
            "address": form.address.data,
            "phone": form.phone.data,
            "coordinate": form.coordinate.data,
            "latitude": form.latitude.data,
            "longitude": form.longitude.data,
            
        }
        try:
            insert_customer_to_database(new_customer)
            flash('เพิ่มลูกค้าเรียบร้อยแล้ว!', 'success')
            return redirect(url_for('customer_list'))
        except ValueError as e:
            flash(str(e), 'danger')  # ข้อความแจ้งเตือนกรณีมีชื่อซ้ำ
    else:
        print("ฟอร์มไม่ผ่านการ Validate:", form.errors)  # Debugging
    return render_template('add_customer.html', form=form)


@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    form = CustomerForm()
    customer = get_customer_by_id(customer_id)

    if customer:
        if request.method == 'GET':
            # เติมข้อมูลลูกค้าในฟอร์ม
            form.first_name.data = customer['first_name']
            form.last_name.data = customer['last_name']
            form.address.data = customer['address']
            form.phone.data = customer['phone']
            form.coordinate.data = customer['coordinate']
            form.latitude.data = customer['latitude']
            form.longitude.data = customer['longitude']
            
        elif form.validate_on_submit():
            updated_customer = {
                "first_name": form.first_name.data,
                "last_name": form.last_name.data,
                "address": form.address.data,
                "phone": form.phone.data,
                "coordinate": form.coordinate.data,
                "latitude": form.latitude.data,
                "longitude": form.longitude.data,
                
            }
            edit_customer_in_database(customer_id, updated_customer)
            flash('อัปเดตข้อมูลลูกค้าเรียบร้อยแล้ว!', 'success')
            return redirect(url_for('customer_list'))
    else:
        flash('ไม่พบข้อมูลลูกค้า', 'danger')
        return redirect(url_for('customer_list'))

    return render_template('edit_customer.html', form=form, customer_id=customer_id)


@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    if current_user.user_type == 'admin' and current_user.email == 'charoen@charoen.com':
        delete_customer_in_database(customer_id)
        flash('ลบลูกค้าเรียบร้อยแล้ว!', 'success')
    else:
        flash('คุณไม่มีสิทธิ์ในการลบลูกค้านี้', 'danger')
    return redirect(url_for('customer_list'))



@app.route('/product_list', methods=['GET'])
@login_required
def product_list():
    products = get_products_from_database()
    return render_template('product_list.html', products=products)


@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = {
            "brand": form.brand.data,
            "weight_per_bag": form.weight_per_bag.data,
            "price": form.price.data
        }
        insert_product_to_database(new_product)
        flash('เพิ่มสินค้าเรียบร้อยแล้ว!', 'success')
        return redirect(url_for('product_list'))
    return render_template('add_product.html', form=form)


@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    form = ProductForm()
    if form.validate_on_submit():
        edit_product = {
            "brand": form.brand.data,
            "weight_per_bag": form.weight_per_bag.data,
            "price": form.price.data
        }
        edit_product_in_database(product_id, edit_product)
        flash('อัปเดตข้อมูลสินค้าเรียบร้อยแล้ว!', 'success')
        return redirect(url_for('product_list'))
    return render_template('edit_product.html', form=form, product_id=product_id)


@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    # ตรวจสอบว่า user_type เป็น admin และอีเมลตรงกับ Charoen2@gmail.com
    if current_user.user_type == 'admin' and current_user.email == 'charoen@charoen.com':
        conn = connect_db()
        cursor = conn.cursor()

        # ลบสินค้าออกจากฐานข้อมูล
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()

        flash("ลบสินค้าเรียบร้อยแล้ว", "success")
    else:
        flash("คุณไม่มีสิทธิ์ในการลบสินค้า", "danger")

    return redirect(url_for('product_list'))

# ---------------------MAP------------------------------------#
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    return render_template('upload.html')

@app.route('/map_excel', methods=['GET', 'POST'])
@login_required
def map_excel():
    if request.method == 'POST':
        try:
            # เรียกใช้ฟังก์ชันเพื่อทำการลบและสร้างตารางใหม่
            try:
                drop_and_recreate_table()  # ลบและสร้างตารางใหม่ก่อนทำการคำนวณ
                logging.debug("Successfully dropped and recreated table.")
            except Exception as e:
                flash(f"ไม่สามารถลบและสร้างตารางใหม่ได้: {str(e)}", 'danger')
                logging.error("Error in dropping and recreating table: %s", str(e))
                return redirect(request.url)

            file = request.files.get('file')
            if not file:
                flash('ไม่มีไฟล์ที่ถูกอัปโหลด', 'danger')
                logging.debug("No file uploaded")
                return redirect(request.url)

            # อ่านไฟล์ Excel
            try:
                df = pd.read_excel(file, usecols=['first_name', 'last_name', 'address', 'phone', 'latitude', 'longitude', 'date', 'product', 'order_id'])
            except Exception as e:
                flash('เกิดข้อผิดพลาดในการอ่านไฟล์ Excel', 'danger')
                logging.error("Excel reading error: %s", str(e))
                return redirect(request.url)

            logging.debug("Excel Data: \n%s", df.head())

            required_columns = ['first_name', 'last_name', 'address', 'phone', 'latitude', 'longitude', 'date', 'product', 'order_id']
            if not all(col in df.columns for col in required_columns):
                flash('ไฟล์ Excel ขาดคอลัมน์ที่จำเป็น', 'danger')
                logging.debug("Missing required columns in Excel")
                return redirect(request.url)

            data = []
            for index, row in df.iterrows():
                if pd.isna(row['first_name']) or pd.isna(row['last_name']):
                    logging.debug(f"Skipping row {index}: Missing first_name or last_name")
                    continue
                if pd.isna(row['latitude']) or pd.isna(row['longitude']):
                    logging.debug(f"Skipping row {index}: Missing latitude or longitude")
                    continue
                if pd.isna(row['order_id']):
                    logging.debug(f"Skipping row {index}: Missing order_id")
                    continue

                first_name = str(row['first_name']).strip()
                last_name = str(row['last_name']).strip()
                phone = str(row['phone']).strip()
                product = str(row['product']).strip() if isinstance(row['product'], str) else ''
                order_id = str(row['order_id']).strip()

                try:
                    date_value = pd.to_datetime(row['date'], errors='coerce', format='%d/%m/%Y').date() if not pd.isna(row['date']) else None
                except Exception as e:
                    logging.error(f"Error parsing date in row {index}: {str(e)}")
                    continue

                if date_value is None:
                    logging.debug(f"Skipping row {index}: Invalid date")
                    continue

                # ตรวจสอบว่าในฐานข้อมูลมีวันที่นี้แล้วหรือยัง
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''SELECT 1 FROM routes WHERE date = ? LIMIT 1''', (date_value,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    flash(f'ข้อมูลวันที่ {date_value} มีอยู่แล้วในฐานข้อมูล', 'info')
                    # ดึงข้อมูลที่มีอยู่จากฐานข้อมูลมาแสดง
                    existing_routes = fetch_routes_by_date(date_value)
                    session['routes'] = existing_routes
                    return redirect(url_for('map_excel'))

                # เพิ่มข้อมูลลงใน data หากครบถ้วน
                data.append({
                    'first_name': first_name,
                    'last_name': last_name,
                    'address': str(row['address']).strip() if isinstance(row['address'], str) else '',
                    'phone': phone,
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'date': date_value,
                    'product': product,
                    'order_id': order_id
                })

            if not data:
                flash('ไม่มีข้อมูลที่สมบูรณ์ในไฟล์ Excel กรุณาตรวจสอบไฟล์อีกครั้ง', 'danger')
                logging.debug("No complete data in Excel file")
                return redirect(request.url)

            logging.debug("Data to send to database: %s", data)

            try:
                route = CalculateRoutesExcel(data)
                if not route or not isinstance(route, dict):
                    logging.error("Calculated route is not valid: %s", route)
                    flash('ไม่สามารถคำนวณเส้นทางได้', 'danger')
                    return redirect(request.url)
                logging.debug("Calculated Route: %s", route)
            except Exception as e:
                logging.error("Error in CalculateRoutesExcel: %s", str(e))
                flash('ไม่สามารถคำนวณเส้นทางได้', 'danger')
                return redirect(request.url)

            grouped_routes = route
            for group_id, route_info in grouped_routes.items():
                route_places = route_info['route']
                ordered_data = [item for item in data if item['first_name'] in route_places]
                ordered_data = sorted(ordered_data, key=lambda x: route_places.index(x['first_name']))

                logging.debug(f"Group {group_id} ordered data: {ordered_data}")

                try:
                    sendMapToDatabase(group_id, ordered_data, route_info['total_distance'])
                    logging.debug(f"Group {group_id} data saved to database")
                except sqlite3.Error as e:
                    logging.error(f"Database error while saving group {group_id}: {str(e)}")
                    flash('ไม่สามารถบันทึกข้อมูลเส้นทางได้', 'danger')
                    return redirect(request.url)

            session['routes'] = grouped_routes
            flash('แผนที่ถูกสร้างและบันทึกเรียบร้อยแล้ว!', 'success')
            return redirect(url_for('map_excel'))

        except Exception as e:
            logging.error("Error in map_excel: %s", str(e))
            flash('เกิดข้อผิดพลาดในการประมวลผลไฟล์', 'danger')
            return redirect(request.url)
    else:
        routes = session.get('routes', {})
        return render_template('upload.html', data=routes)


@app.route('/map_driver', methods=['GET'])
@login_required
def map_driver():
    try:
        # ดึงข้อมูลเส้นทางจากฐานข้อมูล
        result = getMapFromDatabase()

        # ตรวจสอบว่ามีการส่งข้อผิดพลาดจากฐานข้อมูลหรือไม่
        if 'error' in result:
            flash(f"เกิดข้อผิดพลาด: {result['error']}", 'danger')
            return redirect(url_for('map_excel'))

        # ดึงข้อมูลเส้นทางที่ได้รับ
        grouped_data = result.get('grouped_data', {})

        # ตรวจสอบว่ามีข้อมูลเส้นทางหรือไม่
        if not grouped_data:
            flash('ไม่มีข้อมูลเส้นทางในฐานข้อมูล', 'warning')
            return redirect(url_for('map_excel'))

        # ส่งข้อมูลไปยังเทมเพลต
        return render_template('map_driver.html', grouped_data=grouped_data)

    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาด: {e}")
        flash('เกิดข้อผิดพลาดที่ไม่สามารถคาดการณ์ได้', 'danger')
        return redirect(url_for('map_driver'))



if __name__ == '__main__':
    initialize_db()  # Initialize the database when starting the app
    app.run(host='0.0.0.0', port=8080, debug=True)
