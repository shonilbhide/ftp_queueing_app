import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import qrcode
import random
from mailersend import emails

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management

# Retrieve the admin username and password from environment variables
ADMIN_USERNAME = os.environ.get('USERNAME')
ADMIN_PASSWORD = os.environ.get('PASSWORD')

# In-memory storage for daily submissions
submissions = {}
random_numbers_generated = False
next_sequential_number = None

# Generate QR code for form URL
def generate_qr_code(url):
    qr = qrcode.make(url)
    qr.save("static/qr_code.png")

# Function to send email using MailerSend API
def send_email(to_emails, subject, html_content, text_content):
    # Initialize MailerSend email client with your API key
    mailer = emails.NewEmailApiClient(api_key=os.environ.get('MAILERSEND_API_KEY'))

    # Prepare email data
    email_data = {
        'from': {
            'email': 'ftp@ncsu.edu',  # Replace with your verified sender email from MailerSend
            'name': 'Feed the Pack'
        },
        'to': [{'email': email} for email in to_emails],
        'subject': subject,
        'html': html_content,
        'text': text_content,
    }

    # Send email using the MailerSend API client
    try:
        response = mailer.send(email_data)
        print(f"Email sent successfully to {to_emails}")
    except Exception as e:
        print(f"Error sending email: {e}")


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
    sorted_submissions = None
    
    # If tokens have been generated, sort submissions by ticket_number
    if random_numbers_generated:
        sorted_submissions = sorted(submissions.items(), key=lambda x: x[1]['ticket_number'])
    
    return render_template('admin.html', submissions=submissions, random_generated=random_numbers_generated, sorted_submissions=sorted_submissions)

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
    """Generate random numbers for all current submissions and send emails."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Protect this route
    
    global random_numbers_generated, next_sequential_number
    
    if not random_numbers_generated:
        emails_list = list(submissions.keys())
        n = len(emails_list)
        random_numbers = random.sample(range(1, n + 1), n)
        
        # Prepare data for sending emails via MailerSend API
        recipients_list = []
        
        for i, email in enumerate(emails_list):
            submissions[email]['ticket_number'] = random_numbers[i]
            
            fullname = submissions[email]['fullname']
            token_number = submissions[email]['ticket_number']
            
            # Prepare email content (HTML and text versions)
            subject = "Your Token Number"
            text_content = f"Hello {fullname},\n\nYour assigned token number is: {token_number}.\n\nThank you!"
            html_content = f"<p>Hello {fullname},</p><p>Your assigned token number is: <strong>{token_number}</strong>.</p><p>Thank you!</p>"
            
            # Add recipient email to list for batch sending (MailerSend supports batch sending)
            recipients_list.append(email)
            
            # Send individual email using MailerSend (or you can batch send all at once after the loop)
            send_email([email], subject, html_content, text_content)
        
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)