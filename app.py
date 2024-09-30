import os
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import stripe
from datetime import datetime
from sqlalchemy.sql import func
from flask_mail import Mail, Message
import re
from html import escape
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

csrf = CSRFProtect(app)

db = SQLAlchemy(app)

# Email configurations
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Your Gmail account
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Your Gmail password or App-specific password
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # The sender email address
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

VALID_ZODIAC_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Order model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    service_price = db.Column(db.Integer, nullable=False)  # Store price in cents
    message = db.Column(db.Text, nullable=True)
    zodiac_sign = db.Column(db.String(20), nullable=True)  # New Zodiac sign field
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Order {self.id} - {self.name}>"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/booking')
def booking():
    max_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('booking.html', max_date=max_date)




@app.route('/create-checkout-session', methods=['POST'])
@limiter.limit("5 per minute")
def create_checkout_session():
    


    data = request.get_json()
    
    name = data.get('name')
    email = data.get('email')
   
    session['name'] = name
    session['email'] = email

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Tarot Reading',
                        },
                        'unit_amount': int(data['servicePrice']) * 100,
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('index', _external=True),
            metadata={
                'name': data['name'],
                'email': data['email'],
                'zodiac_sign': data['zodiacSign'],
                'message': data['message'],
                'service_price': data['servicePrice']
            }
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/success')
def success():
    name = session['name']
    email = session['email']

    return render_template('success.html', name=name, email=email)

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """
    This route handles Stripe webhooks.
    It listens for the 'checkout.session.completed' event to confirm payment.
    Once confirmed, it saves the order details to the database.
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = 'whsec_a0c77d509fe6f87720e4e8e8b05e5aec892c29cfc550163fd9070ccceec88979'  # Replace with your actual webhook secret from Stripe
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        return jsonify(success=False), 400  # Invalid payload
    except stripe.error.SignatureVerificationError as e:
        return jsonify(success=False), 400  # Invalid signature

    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']

        # Retrieve name, email, and other details from session_data
        customer_email = session_data.get('metadata', {}).get('email') #session_data.get('email')
        price = session_data['amount_total'] / 100  # Convert cents to dollars
        message = session_data.get('metadata', {}).get('message', '')

        # Extract any other relevant metadata you need
        name = session_data.get('metadata', {}).get('name')
        birth_date = session_data.get('metadata', {}).get('birth_date')
        birth_time = session_data.get('metadata', {}).get('birth_time')
        birth_place = session_data.get('metadata', {}).get('birth_place')
        zodiac_sign = session_data.get('metadata', {}).get('zodiac_sign')

        # Insert the order into the database
        if name and customer_email:
            try:
                order = Order(
                    name=name,
                    email=customer_email,
                    service_price=price,
                    message=message,
                    zodiac_sign=zodiac_sign
                )
                db.session.add(order)
                db.session.commit()
                print(f"Order successfully created: {order}")
                # Send an email with the order details
                send_order_email(order)

            except Exception as e:
                db.session.rollback()  # Rollback in case of failure
                print(f"Error committing to the database: {e}")


    return jsonify(success=True)

def send_order_email(order):
    try:
        msg = Message('New Order Details',
                      recipients=['triple9.ar@gmail.com'])  # Recipient email address
        msg.body = f"""
        New order received!
        
        Name: {order.name}
        Email: {order.email}
        Service Price: {order.service_price}
        Zodiac Sign: {order.zodiac_sign}
        Message: {order.message}
        Date Created: {order.date_created}
        """
        mail.send(msg)
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database initialized and tables created.")
    app.run(debug=True)