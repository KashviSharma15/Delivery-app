from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import sqlite3
import hashlib
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'deliveryhub-secret-key-2024-keep-this-same'

# File paths for data storage
SHOPS_FILE = 'shops.json'
ORDERS_FILE = 'orders.json'
DATABASE_FILE = 'users.db'

PHARMACIES_FILE = 'pharmacies.json'
MEDICINE_ORDERS_FILE = 'medicine_orders.json'

# Initialize data files if they don't exist
def init_data_files():
    if not os.path.exists(SHOPS_FILE):
        with open(SHOPS_FILE, 'w') as f:
            json.dump({}, f)
    
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'w') as f:
            json.dump([], f)

    if not os.path.exists(PHARMACIES_FILE):
            with open(PHARMACIES_FILE, 'w') as f:
                json.dump({}, f)
    
    if not os.path.exists(MEDICINE_ORDERS_FILE):
        with open(MEDICINE_ORDERS_FILE, 'w') as f:
            json.dump([], f)
            
def init_database():
    """Initialize SQLite database for users"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Create users table for both food and medicine services
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type TEXT NOT NULL CHECK (service_type IN ('food', 'medicine')),
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT,
            pincode TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            verified BOOLEAN DEFAULT TRUE,
            
            -- Food service specific fields
            restaurant_name TEXT,
            cuisine_type TEXT,
            vehicle_type TEXT,
            license_number TEXT,
            
            -- Medicine service specific fields
            pharmacy_name TEXT,
            registration_number TEXT,
            qualification TEXT,
            experience TEXT,
            license_document_path TEXT,
            
            UNIQUE(email, service_type, role)
        )
    ''')
    
    conn.commit()
    conn.close()

def load_shops():
    try:
        with open(SHOPS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_shops(shops):
    with open(SHOPS_FILE, 'w') as f:
        json.dump(shops, f, indent=2)

def load_orders():
    try:
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_orders(orders):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f, indent=2)

def load_pharmacies():
    try:
        with open(PHARMACIES_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_pharmacies(pharmacies):
    with open(PHARMACIES_FILE, 'w') as f:
        json.dump(pharmacies, f, indent=2)

def load_medicine_orders():
    try:
        with open(MEDICINE_ORDERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_medicine_orders(orders):
    with open(MEDICINE_ORDERS_FILE, 'w') as f:
        json.dump(orders, f, indent=2)
        
def hash_password(password):
    """No password hashing - store plain text"""
    return password

def check_user_exists(email, service_type, role):
    """Check if user already exists for given service and role"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM users WHERE email = ? AND service_type = ? AND role = ?', 
        (email, service_type, role)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def verify_user(email, password, service_type, role):
    """Verify user credentials"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM users WHERE email = ? AND service_type = ? AND role = ?', 
        (email, service_type, role)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user and user[5] == password:  # Direct password comparison
        return {
            'id': user[0],
            'name': user[2],
            'email': user[3],
            'role': user[6],
            'verified': bool(user[12])
        }
    return None

def init_admin_user():
    """Create default admin user if not exists"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Check if admin already exists with correct email
    cursor.execute('''
        SELECT id FROM users 
        WHERE email = 'admin@admin' AND role = 'admin'
    ''')
    
    if cursor.fetchone() is None:
        # Delete any old admin entries first
        cursor.execute("DELETE FROM users WHERE role = 'admin'")
        
        cursor.execute('''
            INSERT INTO users (
                service_type, full_name, email, phone, password_hash, role,
                address, city, state, pincode, verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'medicine',  # service_type for managing pharmacies
            'Administrator',  # full_name
            'admin@admin',  # email
            'admin',  # phone
            'admin',  # password_hash (plain text)
            'admin',  # role
            'Admin Office',  # address
            'Admin City',  # city
            'Admin State',  # state
            '000000',  # pincode
            1  # verified (True)
        ))
        
        conn.commit()
        print("✅ Default admin user created: admin@admin/admin")
    else:
        print("ℹ️  Admin user already exists")
    
    conn.close()
    
def find_user_by_credentials(email, password, service_type):
    """Find user by email and password across all roles"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM users WHERE email = ? AND service_type = ? AND password_hash = ?', 
        (email, service_type, password)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'name': user[2],
            'email': user[3],
            'role': user[6],
            'verified': bool(user[12])
        }
    return None

# Initialize data files and database on startup
init_data_files()
init_database()
init_admin_user()

# Retailer credentials (in production, use proper authentication)
RETAILER_CREDENTIALS = {
    'admin': 'admin'
}

@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard for managing pharmacy verifications"""
    # Check if admin is logged in
    if session.get('user_role') != 'admin' or session.get('service_type') != 'medicine':
        return redirect(url_for('admin_login'))
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
        
        # Check admin credentials
        if email == 'admin@admin' and password == 'admin':
            session['user_role'] = 'admin'
            session['username'] = 'Administrator'
            session['service_type'] = 'medicine'
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'user': {'role': 'admin'},
                    'redirect': '/admin/dashboard'  
                })
            else:
                return redirect(url_for('admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Invalid admin credentials'
                })
            else:
                return render_template('admin.html', error='Invalid credentials')
    
    return render_template('admin.html')


@app.route('/api/admin/pharmacists', methods=['GET'])
def get_pharmacists():
    """Get all pharmacists for admin approval"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Get all pharmacy users
        cursor.execute('''
            SELECT id, full_name, email, phone, address, city, state, pincode,
                   verified, pharmacy_name, license_number, registration_number,
                   qualification, experience, created_at
            FROM users 
            WHERE service_type = 'medicine' AND role = 'pharmacy'
            ORDER BY created_at DESC
        ''')
        
        pharmacists = []
        for row in cursor.fetchall():
            pharmacists.append({
                'id': row[0],
                'username': row[2],
                'full_name': row[1],
                'email': row[2],
                'phone': row[3],
                'address': row[4],
                'city': row[5],
                'state': row[6],
                'pincode': row[7],
                'status': 'approved' if row[8] else 'pending',
                'pharmacyName': row[9],
                'license': row[10],
                'registration': row[11],
                'qualification': row[12],
                'experience': row[13],
                'registeredAt': row[14]
            })
        
        conn.close()
        return jsonify({'success': True, 'pharmacists': pharmacists})
        
    except Exception as e:
        print(f"Error getting pharmacists: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/pharmacists/<int:user_id>/approve', methods=['POST'])
def approve_pharmacist(user_id):
    """Approve a pharmacist"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET verified = 1 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Pharmacist approved'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/pharmacists/<int:user_id>/reject', methods=['POST'])
def reject_pharmacist(user_id):
    """Reject a pharmacist"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET verified = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Pharmacist rejected'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def home():
    """Landing page with service selection"""
    return render_template('home.html')

# ============== FOOD SERVICE ROUTES ==============

@app.route('/food')
def food_service():
    """Food delivery service - check if user is logged in"""
    if 'user_role' not in session or session.get('service_type') != 'food':
        return redirect(url_for('food_login'))
    
    # Redirect to appropriate dashboard based on role
    user_role = session.get('user_role')
    if user_role == 'customer':
        return render_template('food_customer.html')
    elif user_role == 'retailer':
        return render_template('food_retailer.html')
    elif user_role == 'delivery':
        return render_template('food_delivery.html')
    else:
        # Fallback to login if role not recognized
        return redirect(url_for('food_login'))

@app.route('/food/login', methods=['GET', 'POST'])
def food_login():
    """Food service login page"""
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
        
        # Handle retailer/restaurant login with old credentials for compatibility
        if email == 'admin' and password == 'admin':
            session['user_role'] = 'retailer'
            session['username'] = 'admin'
            session['service_type'] = 'food'
            return jsonify({
                'success': True,
                'user': {'role': 'retailer'}
            })
        
        # Find user by email and password across all roles
        user = find_user_by_credentials(email, password, 'food')
        
        if user:
            session['user_role'] = user['role']
            session['username'] = user['name']
            session['user_id'] = user['id']
            session['service_type'] = 'food'
            return jsonify({
                'success': True,
                'user': {'role': user['role']}
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Invalid email or password. Please try again.'
            })
    
    return render_template('food_login.html')

@app.route('/food/register', methods=['GET', 'POST'])
def food_register():
    """Food service registration page"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            email = data.get('email')
            role = data.get('role')
            
            # Check if user already exists
            if check_user_exists(email, 'food', role):
                return jsonify({
                    'success': False, 
                    'message': 'Email already registered for this service. Please go to login page.',
                    'redirect': True
                })
            
            # Insert new user
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (
                    service_type, full_name, email, phone, password_hash, role,
                    address, city, pincode, restaurant_name, cuisine_type,
                    vehicle_type, license_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'food',
                data.get('full_name'),
                email,
                data.get('phone'),
                hash_password(data.get('password')),
                role,
                data.get('address'),
                data.get('city'),
                data.get('pincode'),
                data.get('restaurant_name'),
                data.get('cuisine_type'),
                data.get('vehicle_type'),
                data.get('license_number')
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Registration successful! You can now login.'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Registration failed. Please try again.'
            })
    
    return render_template('food_register.html')

# Individual Food Dashboard Routes
@app.route('/food/customer-dashboard')
def food_customer_dashboard():
    """Food service customer dashboard"""
    if session.get('service_type') != 'food' or session.get('user_role') != 'customer':
        return redirect(url_for('food_login'))
    return render_template('food_customer.html')

@app.route('/food/retailer-dashboard')
@app.route('/food/dashboard')
def food_retailer_dashboard():
    """Food service retailer dashboard"""
    if session.get('service_type') != 'food' or session.get('user_role') != 'retailer':
        return redirect(url_for('food_login'))
    return render_template('food_retailer.html')

@app.route('/food/delivery-dashboard')
def food_delivery_dashboard():
    """Food service delivery dashboard"""
    if session.get('service_type') != 'food' or session.get('user_role') != 'delivery':
        return redirect(url_for('food_login'))
    return render_template('food_delivery.html')

# ============== MEDICINE SERVICE ROUTES ==============

@app.route('/medicine')
def medicine_service():
    """Medicine delivery service - check if user is logged in"""
    if 'user_role' not in session or session.get('service_type') != 'medicine':
        return redirect(url_for('medicine_login'))
    
    # Redirect to appropriate dashboard based on role
    user_role = session.get('user_role')
    if user_role == 'customer':
        return render_template('medicine_customer.html')
    elif user_role == 'pharmacy':
        return render_template('medicine_pharmacist.html')  # Note: matches your template name
    else:
        # Fallback to login if role not recognized
        return redirect(url_for('medicine_login'))

@app.route('/medicine/login', methods=['GET', 'POST'])
def medicine_login():
    """Medicine service login page"""
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                email = data.get('email')
                password = data.get('password')
            else:
                email = request.form.get('email')
                password = request.form.get('password')
            
            print(f"Medicine login attempt: {email}")  # Debug
            # Find user by email and password across all roles (no role required)
            user = find_user_by_credentials(email, password, 'medicine')
            
            if user:
                # Pharmacist must be verified before login
                if user['role'] == 'pharmacy' and not user['verified']:
                    return jsonify({
                        'success': False,
                        'message': 'Your pharmacist account is pending verification. Please wait for approval.',
                        'pending': True
                    })
                
                session.permanent = True
                session['user_role'] = user['role']
                session['username'] = user['name']
                session['user_id'] = user['id']
                session['service_type'] = 'medicine'
                
                print(f"Medicine user login successful: {user['name']}, role: {user['role']}")  # Debug
                
                return jsonify({
                    'success': True,
                    'user': {'role': user['role']}
                })
            else:
                print(f"Medicine login failed for: {email}")  # Debug
                return jsonify({
                    'success': False, 
                    'message': 'Invalid email or password. Please try again.'
                })
        except Exception as e:
            print(f"Medicine login error: {str(e)}")  # Debug
            return jsonify({
                'success': False, 
                'message': f'Login error: {str(e)}'
            })
    
    return render_template('medicine_login.html')

@app.route('/medicine/register', methods=['GET', 'POST'])
def medicine_register():
    """Medicine service registration page"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            email = data.get('email')
            role = data.get('role')
            
            # Check if user already exists
            if check_user_exists(email, 'medicine', role):
                return jsonify({
                    'success': False,
                    'message': 'Email already registered for this service. Please go to login page.',
                    'redirect': True
                })
            
            # Set verification status (pharmacists need approval)
            verified = role == 'customer'
            
            # Insert new user
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (
                    service_type, full_name, email, phone, password_hash, role,
                    address, city, state, pincode, verified, pharmacy_name,
                    license_number, registration_number, qualification, experience
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'medicine',
                data.get('full_name'),
                email,
                data.get('phone'),
                hash_password(data.get('password')),
                role,
                data.get('address'),
                data.get('city'),
                data.get('state'),
                data.get('pincode'),
                verified,
                data.get('pharmacy_name'),
                data.get('license_number'),
                data.get('registration_number'),
                data.get('qualification'),
                data.get('experience')
            ))
            
            conn.commit()
            conn.close()
            
            message = ('Registration successful! Your documents will be verified within 24-48 hours.' 
                      if role == 'pharmacy' 
                      else 'Registration successful! You can now login.')
            
            return jsonify({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Registration failed. Please try again.'
            })
    
    return render_template('medicine_register.html')

# Individual Medicine Dashboard Routes
@app.route('/medicine/customer-dashboard')
def medicine_customer_dashboard():
    """Medicine service customer dashboard"""
    if session.get('service_type') != 'medicine' or session.get('user_role') != 'customer':
        return redirect(url_for('medicine_login'))
    return render_template('medicine_customer.html')

@app.route('/medicine/pharmacist-dashboard')
def medicine_pharmacist_dashboard():
    """Medicine service pharmacist dashboard"""
    if session.get('service_type') != 'medicine' or session.get('user_role') != 'pharmacy':
        return redirect(url_for('medicine_login'))
    return render_template('medicine_pharmacist.html')

@app.route('/medicine/dashboard')
@app.route('/medicine/delivery-dashboard')
def medical_delivery_dashboard():
    """Medical service delivery dashboard"""
    if session.get('service_type') != 'medicine' or session.get('user_role') != 'delivery':
        return redirect(url_for('medicine_login'))
    return render_template('medicine_delivery.html')

# ============== LEGACY/COMPATIBILITY ROUTES ==============

# Keep original login route for backward compatibility
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Original login page - redirect to home"""
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """Logout and redirect to appropriate service login page"""
    # Store the service type before clearing session
    service_type = session.get('service_type')
    
    # Clear the session
    session.clear()
    
    # Redirect based on service type
    if service_type == 'food':
        return redirect(url_for('food_login'))
    elif service_type == 'medicine':
        return redirect(url_for('medicine_login'))
    else:
        # Fallback to home if service type not found
        return redirect(url_for('home'))

# ============== API ROUTES ==============

@app.route('/api/user-role')
def get_user_role():
    try:
        # Debug: print session contents
        print(f"Session contents: {dict(session)}")
        
        return jsonify({
            'role': session.get('user_role'),
            'username': session.get('username'),
            'service_type': session.get('service_type'),
            'authenticated': 'user_role' in session,
            'session_keys': list(session.keys())  # For debugging
        })
    except Exception as e:
        print(f"Error in get_user_role: {str(e)}")
        return jsonify({
            'role': None,
            'username': None,
            'service_type': None,
            'authenticated': False,
            'error': str(e)
        })


# API Routes for shop management
@app.route('/api/shops', methods=['GET', 'POST'])
def manage_shops():
    try:
        if request.method == 'GET':
            # Always return valid JSON, even if empty
            shops = load_shops()
            print(f"Loaded shops: {shops}")  # Debug
            
            # Ensure all coordinates are properly formatted as numbers
            for shop_id, shop in shops.items():
                if 'latitude' in shop:
                    shop['latitude'] = float(shop['latitude'])
                if 'longitude' in shop:
                    shop['longitude'] = float(shop['longitude'])
            
            return jsonify(shops if shops else {})
        
        elif request.method == 'POST':
            # Check authentication
            if session.get('user_role') != 'retailer':
                return jsonify({'error': 'Unauthorized', 'success': False}), 401
            
            shop_data = request.json
            if not shop_data:
                return jsonify({'error': 'No data provided', 'success': False}), 400
                
            shops = load_shops()
            shop_id = shop_data.get('id', str(len(shops) + 1))
            
            # Ensure shop has required fields and coordinates are numbers
            shop_data['id'] = shop_id
            if 'restaurant_name' not in shop_data and 'name' not in shop_data:
                shop_data['name'] = f'Restaurant {shop_id}'
            
            # Convert coordinates to float to ensure proper storage
            if 'latitude' in shop_data:
                shop_data['latitude'] = float(shop_data['latitude'])
            if 'longitude' in shop_data:
                shop_data['longitude'] = float(shop_data['longitude'])
                
            shops[shop_id] = shop_data
            save_shops(shops)
            
            print(f"Saved shop: {shop_id}, Lat: {shop_data.get('latitude')}, Lng: {shop_data.get('longitude')}")
            
            return jsonify({'success': True, 'shop_id': shop_id})
    except Exception as e:
        print(f"Error in manage_shops: {str(e)}")  # Debug
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/shops/<shop_id>/items', methods=['GET', 'POST'])
def manage_shop_items(shop_id):
    try:
        shops = load_shops()
        
        if request.method == 'GET':
            # Return items for the shop, or empty list if shop doesn't exist
            if shop_id not in shops:
                return jsonify([])
            return jsonify(shops[shop_id].get('items', []))
        
        elif request.method == 'POST':
            # Check authentication
            if session.get('user_role') != 'retailer':
                return jsonify({'error': 'Unauthorized', 'success': False}), 401
            
            item_data = request.json
            if not item_data:
                return jsonify({'error': 'No data provided', 'success': False}), 400
            
            # Auto-create shop if it doesn't exist
            if shop_id not in shops:
                user_info = session.get('username', 'Restaurant Owner')
                shops[shop_id] = {
                    'id': shop_id,
                    'name': f'{user_info}\'s Restaurant',
                    'restaurant_name': f'{user_info}\'s Restaurant',
                    'cuisine_type': 'Multi Cuisine',
                    'items': []
                }
                
            if 'items' not in shops[shop_id]:
                shops[shop_id]['items'] = []
            
            # Add timestamp and ensure item has ID
            item_data['added_at'] = datetime.now().isoformat()
            if 'id' not in item_data:
                item_data['id'] = str(len(shops[shop_id]['items']) + 1)
            
            shops[shop_id]['items'].append(item_data)
            save_shops(shops)
            
            print(f"Item added to shop {shop_id}: {item_data}")  # Debug
            return jsonify({'success': True})
    except Exception as e:
        print(f"Error in manage_shop_items: {str(e)}")  # Debug
        return jsonify({'error': str(e), 'success': False}), 500

# API Routes for order management
@app.route('/api/orders', methods=['GET', 'POST'])
def manage_orders():
    try:
        if request.method == 'GET':
            orders = load_orders()
            user_role = session.get('user_role')
            
            # Return orders based on user role
            if user_role == 'customer':
                # Customer sees their own orders (if we track customer_id)
                return jsonify(orders)
            elif user_role == 'retailer':
                # Retailer sees all orders
                return jsonify(orders)
            elif user_role == 'delivery':
                # Delivery partner sees ready orders
                ready_orders = [order for order in orders if order.get('status') == 'Ready']
                return jsonify(ready_orders)
            else:
                # Not authenticated or invalid role
                return jsonify([])
        
        elif request.method == 'POST':
            order_data = request.json
            if not order_data:
                return jsonify({'error': 'No data provided', 'success': False}), 400
                
            orders = load_orders()
            
            order_data['id'] = len(orders) + 1
            order_data['timestamp'] = datetime.now().isoformat()
            order_data['status'] = 'Placed'
            
            orders.append(order_data)
            save_orders(orders)
            return jsonify({'success': True, 'order_id': order_data['id']})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/pharmacies', methods=['GET', 'POST'])
def manage_pharmacies():
    """Manage pharmacies for pharmacist"""
    try:
        if request.method == 'GET':
            pharmacies = load_pharmacies()
            if isinstance(pharmacies, dict):
                return jsonify(list(pharmacies.values()))
            return jsonify(pharmacies)
        
        elif request.method == 'POST':
            user_role = session.get('user_role')
            service_type = session.get('service_type')
            
            print(f"POST /api/pharmacies - Role: {user_role}, Service: {service_type}")
            
            if service_type != 'medicine':
                return jsonify({'success': False, 'error': 'Wrong service type. Please login to medicine service.'}), 401
            
            if user_role != 'pharmacy':
                return jsonify({'success': False, 'error': 'Only pharmacists can add pharmacies. Please login as pharmacist.'}), 401
            
            pharmacy_data = request.json
            if not pharmacy_data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            pharmacies = load_pharmacies()
            if not isinstance(pharmacies, dict):
                pharmacies = {}
            
            pharmacy_id = pharmacy_data.get('id', f'ph{int(time.time())}')
            
            pharmacy_data['ownerId'] = session.get('username', 'Unknown')
            pharmacy_data['owner'] = session.get('username', 'Unknown')
            pharmacy_data['id'] = pharmacy_id
            
            if 'medicines' not in pharmacy_data:
                pharmacy_data['medicines'] = []
            if 'items' not in pharmacy_data:
                pharmacy_data['items'] = []
            
            pharmacies[pharmacy_id] = pharmacy_data
            save_pharmacies(pharmacies)
            
            print(f"✅ Pharmacy saved: {pharmacy_id} by {session.get('username')}")
            return jsonify({'success': True, 'pharmacy_id': pharmacy_id})
    
    except Exception as e:
        print(f"❌ Error in manage_pharmacies: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/medicine-orders', methods=['GET', 'POST'])
def manage_medicine_orders():
    """Manage medicine orders"""
    try:
        if request.method == 'GET':
            orders = load_medicine_orders()
            if isinstance(orders, dict):
                orders = list(orders.values())
            return jsonify(orders)
        
        elif request.method == 'POST':
            order_data = request.json
            if not order_data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            orders = load_medicine_orders()
            if not isinstance(orders, list):
                orders = []
            
            order_id = len(orders) + 1
            order_data['id'] = order_id
            order_data['order_id'] = order_id
            order_data['timestamp'] = datetime.now().isoformat()
            order_data['status'] = order_data.get('status', 'pending')
            
            orders.append(order_data)
            save_medicine_orders(orders)
            
            print(f"Medicine order created: {order_id}")
            return jsonify({'success': True, 'order_id': order_id})
    
    except Exception as e:
        print(f"Error in manage_medicine_orders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/medicine-orders/<int:order_id>/status', methods=['PUT'])
def update_medicine_order_status(order_id):
    """Update medicine order status"""
    try:
        new_status = request.json.get('status')
        
        orders = load_medicine_orders()
        if not isinstance(orders, list):
            orders = []
        
        order = next((o for o in orders if o.get('id') == order_id or o.get('order_id') == order_id), None)
        
        if not order:
            print(f"Order not found: {order_id}")
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        old_status = order.get('status')
        order['status'] = new_status
        order['updated_at'] = datetime.now().isoformat()
        
        save_medicine_orders(orders)
        
        print(f"Order {order_id} status updated: {old_status} -> {new_status}")
        return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})
    
    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/place_order', methods=['POST'])
def place_order():
    order = request.json
    if not order:
        return jsonify({'status': 'error', 'message': 'No order data received'}), 400
    # Save using existing logic
    orders = load_orders()
    order['id'] = len(orders) + 1
    order['timestamp'] = datetime.now().isoformat()
    order['status'] = 'Placed'
    orders.append(order)
    save_orders(orders)
    return jsonify({"status": "success", "order_id": order['id']})

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    orders = load_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    new_status = request.json.get('status')
    order['status'] = new_status
    save_orders(orders)
    
    return jsonify({'success': True})

@app.route('/api/test')
def api_test():
    """Simple test endpoint to verify API is working"""
    return jsonify({
        'status': 'success',
        'message': 'API is working',
        'session_active': 'user_role' in session,
        'user_role': session.get('user_role', 'none')
    })

# API endpoints for medicine functionality
@app.route('/api/medicine/pharmacies', methods=['GET'])
def get_pharmacies():
    """Get nearby pharmacies"""
    try:
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))
        radius = float(request.args.get('radius', 5))
        
        # Demo pharmacies - in production, get from database
        demo_pharmacies = [
            {
                'id': 'p1',
                'name': 'HealthCare Pharmacy',
                'address': 'Connaught Place, New Delhi',
                'lat': lat + 0.01,
                'lng': lng + 0.01,
                'medicines': [
                    {'id': 'm1', 'name': 'Paracetamol 500mg', 'price': 25, 'stock': 100},
                    {'id': 'm2', 'name': 'Ibuprofen 400mg', 'price': 45, 'stock': 50},
                    {'id': 'm3', 'name': 'Vitamin C Tablets', 'price': 120, 'stock': 30}
                ]
            },
            {
                'id': 'p2',
                'name': 'MedPlus Pharmacy',
                'address': 'Karol Bagh, New Delhi',
                'lat': lat + 0.02,
                'lng': lng + 0.02,
                'medicines': [
                    {'id': 'm4', 'name': 'Crocin Advance', 'price': 35, 'stock': 80},
                    {'id': 'm5', 'name': 'Dolo 650', 'price': 28, 'stock': 60},
                    {'id': 'm6', 'name': 'Cetirizine 10mg', 'price': 15, 'stock': 40}
                ]
            }
        ]
        
        # Calculate distances (simplified)
        for pharmacy in demo_pharmacies:
            pharmacy['distance'] = abs(lat - pharmacy['lat']) + abs(lng - pharmacy['lng'])
        
        nearby = [p for p in demo_pharmacies if p['distance'] <= radius]
        return jsonify({'success': True, 'pharmacies': nearby})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/medicine/orders', methods=['POST'])
def create_medicine_order():
    """Create a new medicine order"""
    try:
        if session.get('service_type') != 'medicine':
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        data = request.get_json()
        
        # Create order (in production, save to database)
        order = {
            'id': 'ORD' + str(int(time.time())),
            'customer_id': session.get('user_id'),
            'items': data.get('items', []),
            'total': data.get('total', 0),
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'order': order})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/medicine/orders', methods=['GET'])
def get_medicine_orders():
    """Get orders for current user"""
    try:
        if session.get('service_type') != 'medicine':
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        # In production, fetch from database
        orders = []  # Fetch user's orders from database
        
        return jsonify({'success': True, 'orders': orders})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Configure session settings
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour
)

if __name__ == '__main__':
    app.run(debug=True, port=5000)