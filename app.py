from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import razorpay
import os
import random
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'my_secret_key'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Razorpay keys
RAZORPAY_KEY_ID = "rzp_test_AMP6EsdBZy7cZK"#id
RAZORPAY_KEY_SECRET = "TxeUxSIGdymuf1o7yAV7AyCF"#password
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# DB connection
try:
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)
    print("\u2705 DB connected")
except Exception as e:
    print("\u274C DB connection failed:", e)

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/farmer_dashboard' if session['role'] == 'farmer' else '/browse_products')
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            return "Username exists."

        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                       (username, password, role))
        db.commit()
        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect('/')
        return "Invalid credentials"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/farmer_dashboard')
def farmer_dashboard():
    if session.get('role') != 'farmer':
        return redirect('/')
    cursor.execute("SELECT * FROM products WHERE farmer_id=%s", (session['user_id'],))
    products = cursor.fetchall()
    return render_template('farmer_dashboard.html', products=products)

@app.route('/upload_product', methods=['GET', 'POST'])
def upload_product():
    if session.get('role') != 'farmer':
        return redirect('/')

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        quantity = request.form['quantity']
        description = request.form['description']
        image = request.files.get('image')

        image_filename = ''
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = f"uploads/{filename}"

        cursor.execute("INSERT INTO products (farmer_id, name, category, price, quantity, description, product_image) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                       (session['user_id'], name, category, float(price), int(quantity), description, image_filename))
        db.commit()
        return redirect('/farmer_dashboard')

    return render_template('upload_product.html')

@app.route('/browse_products')
def browse_products():
    if session.get('role') != 'consumer':
        return redirect('/')
    cursor.execute("SELECT p.*, u.username AS farmer FROM products p JOIN users u ON p.farmer_id = u.id")
    products = cursor.fetchall()
    return render_template('browse_products.html', products=products)

@app.route('/pay/<int:product_id>')
def pay(product_id):
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    if not product:
        return "Product not found", 404

    order_data = {
        'amount': int(product['price'] * 100),
        'currency': 'INR',
        'payment_capture': 1
    }
    order = razorpay_client.order.create(data=order_data)
    return render_template('pay.html', product=product, order_id=order['id'], razorpay_key=RAZORPAY_KEY_ID)

@app.route('/payment_success', methods=['POST'])
def payment_success():
    data = request.get_json()

    cursor.execute("SELECT * FROM products WHERE id = %s", (data['product_id'],))
    product = cursor.fetchone()
    if not product or product['quantity'] < 1:
        return {'error': 'Out of stock or not found'}, 400

    cursor.execute("UPDATE products SET quantity = quantity - 1 WHERE id = %s", (data['product_id'],))
    cursor.execute("INSERT INTO payments (user_id, product_id, razorpay_payment_id, razorpay_order_id, amount) VALUES (%s, %s, %s, %s, %s)",
                   (session['user_id'], data['product_id'], data['razorpay_payment_id'], data['razorpay_order_id'], data['amount'] / 100))
    db.commit()
    return '', 204

@app.route('/verify_order/<int:product_id>', methods=['POST'])
def verify_order(product_id):
    quantity = int(request.form['quantity'])
    order_type = request.form.get('order_type')
    otp = str(random.randint(100000, 999999))

    session.update({
        'otp': otp,
        'product_id': product_id,
        'quantity': quantity,
        'order_type': order_type
    })

    return render_template('verify_otp.html', otp=otp)

@app.route('/confirm_otp', methods=['POST'])
def confirm_otp():
    if request.form['otp'] != session.get('otp'):
        return "\u274C Incorrect OTP"

    product_id = session['product_id']
    quantity = session['quantity']
    order_type = session['order_type']

    if order_type == 'nopayment':
        cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cursor.fetchone()
        if product and quantity <= product['quantity']:
            total_price = quantity * product['price']
            cursor.execute("INSERT INTO orders (consumer_id, product_id, quantity, total_price) VALUES (%s, %s, %s, %s)",
                           (session['user_id'], product_id, quantity, total_price))
            cursor.execute("UPDATE products SET quantity = quantity - %s WHERE id = %s", (quantity, product_id))
            db.commit()
            return redirect('/browse_products')
        return "\u274C Not enough stock", 400
    return redirect(f'/pay/{product_id}')

if __name__ == '__main__':
    app.run(debug=True)











n=5
for row in range(n,0):
    
    
    for space in range(n-row):
        print(" ",end=" ")
    for star in range(2*row-1):
        print("*",end=" ")     
    print()