from flask import Flask, render_template, request, redirect, url_for, session, flash
import qrcode
import os
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management

# In-memory storage for daily submissions
submissions = {}
random_numbers_generated = False
next_sequential_number = None

# Admin credentials (for simplicity, hardcoded here)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Generate QR code for form URL
def generate_qr_code(url):
    qr = qrcode.make(url)
    qr.save("static/qr_code.png")

@app.route('/')
def home():
    """Home route redirects to login."""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True  # Set session variable to indicate logged-in status
            return redirect(url_for('admin_panel'))
        else:
            flash('Invalid credentials. Please try again.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout route to clear session and redirect to login."""
    session.pop('logged_in', None)  # Remove logged-in status from session
    return redirect(url_for('login'))

@app.route('/admin')
def admin_panel():
    """Admin panel route protected by login."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    global random_numbers_generated
    return render_template('admin.html', submissions=submissions, random_generated=random_numbers_generated)

@app.route('/open_form', methods=['POST'])
def open_form():
    """Open form for customers."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Protect this route
    
    global submissions, random_numbers_generated, next_sequential_number
    submissions.clear()
    random_numbers_generated = False
    next_sequential_number = None
    
    generate_qr_code(request.url_root + 'customer_options')
    
    return redirect(url_for('admin_panel'))

@app.route('/customer_options', methods=['GET'])
def customer_options():
    """Customer options page: Fill a form or view your token."""
    return render_template('customer_options.html')

@app.route('/form', methods=['GET', 'POST'])
def customer_form():
    """Customer form submission."""
    global submissions, next_sequential_number
    
    if request.method == 'POST':
        email = request.form['email']
        fullname = request.form['fullname']
        phone = request.form['phone']
        
        if email in submissions:
            return "You have already submitted this form today."
        
        if random_numbers_generated:
            next_sequential_number += 1
            submissions[email] = {
                'fullname': fullname,
                'phone': phone,
                'ticket_number': next_sequential_number
            }
        else:
            submissions[email] = {
                'fullname': fullname,
                'phone': phone,
                'ticket_number': None  # Will be assigned later by admin
            }
        
        return "Form submitted successfully!"
    
    return render_template('customer_form.html')

@app.route('/generate_random_numbers', methods=['POST'])
def generate_random_numbers():
    """Generate random numbers for all current submissions."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Protect this route
    
    global random_numbers_generated, next_sequential_number
    
    if not random_numbers_generated:
        emails = list(submissions.keys())
        n = len(emails)
        random_numbers = random.sample(range(1, n + 1), n)
        
        for i, email in enumerate(emails):
            submissions[email]['ticket_number'] = random_numbers[i]
        
        random_numbers_generated = True
        next_sequential_number = n
    
    return redirect(url_for('admin_panel'))

@app.route('/check_number', methods=['GET', 'POST'])
def check_number():
    """Check your assigned token."""
    global random_numbers_generated
    
    if request.method == 'POST':
        email = request.form['email']
        
        if email in submissions:
            ticket_number = submissions[email]['ticket_number']
            
            if ticket_number is not None:
                return f"Your assigned number is: {ticket_number}"
            else:
                return "Tokens haven't been distributed yet, wait for our volunteers to start."
        
        return "No record found with this email. Please fill out the form first."
    
    return render_template('check_number.html')

@app.route('/close_form', methods=['POST'])
def close_form():
    """Close form and reset data at end of day."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Protect this route
    
    global submissions, random_numbers_generated, next_sequential_number
    
    submissions.clear()
    random_numbers_generated = False
    next_sequential_number = None
    
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Bind the app to host 0.0.0.0 and the specified port
    app.run(host='0.0.0.0', port=port)
