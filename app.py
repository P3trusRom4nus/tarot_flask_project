import os
import enum
import logging
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from datetime import datetime, timedelta, timezone
from sqlalchemy.sql import func
import stripe
from dotenv import load_dotenv
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv('SECRET_KEY'),
    MAIL_SERVER=os.getenv('MAIL_SERVER'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', '587')),
    MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'True').lower() == 'true',
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER'),
    MAIL_USE_SSL=False
)

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
mail = Mail(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Constants
VALID_ZODIAC_SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

#asyncronous mail sending
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

# Models
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    service_price = db.Column(db.Integer, nullable=False)  
    message = db.Column(db.Text, nullable=True)
    zodiac_sign = db.Column(db.String(20), nullable=True)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc) - timedelta(hours=3))
    stripe_session_id = db.Column(db.String(200), unique=True)
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_intent_id = db.Column(db.String(200), unique=True)

    def __repr__(self):
        return f"<Order {self.id} - {self.name}>"

# Services
class OrderService:
    @staticmethod
    def create_pending_order(name, email, service_price, message, zodiac_sign, stripe_session_id):
        try:
            order = Order(
                name=name,
                email=email,
                service_price=service_price,
                message=message,
                zodiac_sign=zodiac_sign,
                stripe_session_id=stripe_session_id,
                payment_status=PaymentStatus.PENDING
            )
            db.session.add(order)
            db.session.commit()
            logger.info(f"Created pending order for {email} with session ID {stripe_session_id}")
            return order
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating pending order: {str(e)}")
            raise

    @staticmethod
    def complete_order(stripe_session_id, payment_intent_id):
        try:
            order = Order.query.filter_by(stripe_session_id=stripe_session_id).first()
            if order:
                order.payment_status = PaymentStatus.COMPLETED
                order.payment_intent_id = payment_intent_id
                db.session.commit()
                logger.info(f"Completed order for session ID {stripe_session_id}")
                return order
            return None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error completing order: {str(e)}")
            raise

    @staticmethod
    def get_order_by_session_id(session_id):
        return Order.query.filter_by(stripe_session_id=session_id).first()

# Email Service
def send_order_email(order):
    try:
        msg = Message('New Order Details',
                     recipients=[os.getenv('ADMIN_EMAIL', 'triple9.ar@gmail.com')])
        msg.body = f"""
        New order received!
        
        Order ID: {order.id}
        Name: {order.name}
        Email: {order.email}
        Service Price: ${order.service_price}
        Zodiac Sign: {order.zodiac_sign}
        Message: {order.message}
        Date Created: {order.date_created}
        Payment Status: {order.payment_status.value}
        Stripe Session ID: {order.stripe_session_id}
        """
        Thread(target=send_async_email, args=(app, msg)).start()
        logger.info(f"Sent order email for order ID {order.id}")
    except Exception as e:
        logger.error(f"Error sending email for order ID {order.id}: {str(e)}")
        raise

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/booking')
def booking():
    max_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('booking.html', 
                         max_date=max_date, 
                         stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY'))

@app.route('/create-checkout-session', methods=['POST'])
@limiter.limit("300 per day; 50 per hour", key_func=get_remote_address)
def create_checkout_session():
    try:
        data = request.get_json()
        
        # Store user data in session
        session['name'] = data.get('name')
        session['email'] = data.get('email')

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Tarot Reading',
                    },
                    'unit_amount': int(data['servicePrice']) * 100,
                },
                'quantity': 1,
            }],
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

        # Create pending order
        OrderService.create_pending_order(
            name=data['name'],
            email=data['email'],
            service_price=int(data['servicePrice']),
            message=data['message'],
            zodiac_sign=data['zodiacSign'],
            stripe_session_id=checkout_session.id
        )

        return jsonify({'id': checkout_session.id})
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify(error=str(e)), 403

@app.route('/success')
@limiter.exempt
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        logger.warning("Success route accessed without session ID")
        return redirect(url_for('index'))
    
    try:
        # Retrieve the order and session
        order = OrderService.get_order_by_session_id(session_id)
        if not order:
            logger.warning(f"No order found for session ID {session_id}")
            return redirect(url_for('index'))

        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify payment status
        if checkout_session['payment_status'] == 'paid':
            if order.payment_status != PaymentStatus.COMPLETED:
                # Complete the order if not already completed
                order = OrderService.complete_order(
                    session_id, 
                    checkout_session.payment_intent
                )
                try:
                    send_order_email(order)
                except Exception as e:
                    logger.error(f"Error sending success email: {str(e)}")
            return render_template('success.html', name=order.name, email=order.email)
        return redirect(url_for('index'))
            
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in success route: {str(e)}")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Unexpected error in success route: {str(e)}")
        return redirect(url_for('index'))

@app.route('/stripe-webhook', methods=['POST'])
@csrf.exempt
@limiter.exempt
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        
        try:
            # Complete the order
            order = OrderService.complete_order(
                stripe_session_id=session_data['id'],
                payment_intent_id=session_data['payment_intent']
            )
            
            if order and order.payment_status == PaymentStatus.COMPLETED:
                try:
                    send_order_email(order)
                except Exception as e:
                    logger.error(f"Error sending webhook email: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return jsonify(success=False), 500

    return jsonify(success=True)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        logger.info("Database initialized and tables created.")
    app.run(debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true')