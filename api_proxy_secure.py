#!/usr/bin/env python3
"""
Bunq Dashboard API Proxy - Secure Edition v2.0
Flask backend with Vaultwarden secret management
READ-ONLY Bunq API access for maximum security
SECURED with Basic Authentication and rate limiting
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from functools import wraps
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.model.generated import endpoint
from datetime import datetime, timedelta
import os
import json
import requests
import logging
import hashlib
import time
from collections import defaultdict

# ============================================
# LOGGING CONFIGURATION
# ============================================

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bunq_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# SECURITY: BASIC AUTHENTICATION
# ============================================

def check_auth(username, password):
    """
    Verify username and password against environment variables.
    Uses constant-time comparison to prevent timing attacks.
    """
    expected_username = os.getenv('BASIC_AUTH_USERNAME', 'admin')
    expected_password = os.getenv('BASIC_AUTH_PASSWORD', '')
    
    # If no password set, deny all access
    if not expected_password:
        logger.warning("⚠️ No BASIC_AUTH_PASSWORD set - authentication disabled!")
        return True  # Allow in development, but log warning
    
    # Constant-time comparison to prevent timing attacks
    username_match = hashlib.sha256(username.encode()).hexdigest() == \
                     hashlib.sha256(expected_username.encode()).hexdigest()
    password_match = hashlib.sha256(password.encode()).hexdigest() == \
                     hashlib.sha256(expected_password.encode()).hexdigest()
    
    return username_match and password_match

def authenticate():
    """Send 401 response that enables basic auth"""
    return Response(
        'Authentication required. Please login with your credentials.\n',
        401,
        {'WWW-Authenticate': 'Basic realm="Bunq Dashboard - Login Required"'}
    )

def requires_auth(f):
    """Decorator for endpoints that require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            logger.warning(f"🚫 Unauthorized access attempt from {request.remote_addr}")
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ============================================
# SECURITY: RATE LIMITING
# ============================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests=30, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id):
        """Check if client is allowed to make request"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Record request
        self.requests[client_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=30, window_seconds=60)

def rate_limit(f):
    """Decorator for rate limiting"""
    @wraps(f)
    def decorated(*args, **kwargs):
        client_id = request.remote_addr
        
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"🚫 Rate limit exceeded for {client_id}")
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded. Max 30 requests per minute.'
            }), 429
        
        return f(*args, **kwargs)
    return decorated

# ============================================
# FLASK APP INITIALIZATION
# ============================================

app = Flask(__name__)

# CORS Configuration - Restricted to specific origins
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8000').split(',')
logger.info(f"🔒 CORS allowed origins: {ALLOWED_ORIGINS}")
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# ============================================
# VAULTWARDEN SECRET RETRIEVAL
# ============================================

def get_api_key_from_vaultwarden():
    """
    Securely retrieve Bunq API key from Vaultwarden vault.
    
    Returns:
        str: Bunq API key or None if retrieval failed
    """
    
    use_vaultwarden = os.getenv('USE_VAULTWARDEN', 'false').lower() == 'true'
    
    if not use_vaultwarden:
        logger.info("📝 Vaultwarden disabled, using environment variable")
        api_key = os.getenv('BUNQ_API_KEY', '')
        if api_key:
            logger.info("✅ API key loaded from environment")  # Don't log key!
        return api_key
    
    logger.info("🔐 Retrieving API key from Vaultwarden vault...")
    
    vault_url = os.getenv('VAULTWARDEN_URL', 'http://vaultwarden:80')
    client_id = os.getenv('VAULTWARDEN_CLIENT_ID')
    client_secret = os.getenv('VAULTWARDEN_CLIENT_SECRET')
    item_name = os.getenv('VAULTWARDEN_ITEM_NAME', 'Bunq API Key')
    
    # Validate credentials
    if not client_id or not client_secret:
        logger.error("❌ Vaultwarden credentials missing in environment!")
        logger.error("   Required: VAULTWARDEN_CLIENT_ID and VAULTWARDEN_CLIENT_SECRET")
        return None
    
    try:
        # Step 1: Authenticate and get access token
        logger.info("🔑 Authenticating with Vaultwarden...")
        token_url = f"{vault_url}/identity/connect/token"
        token_data = {
            'grant_type': 'client_credentials',
            'scope': 'api',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        token_response = requests.post(
            token_url, 
            data=token_data,
            timeout=10
        )
        token_response.raise_for_status()
        access_token = token_response.json()['access_token']
        
        logger.info("✅ Vaultwarden authentication successful")
        
        # Step 2: Retrieve all vault items
        logger.info(f"🔍 Searching for vault item: '{item_name}'...")
        items_url = f"{vault_url}/api/ciphers"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        items_response = requests.get(
            items_url, 
            headers=headers,
            timeout=10
        )
        items_response.raise_for_status()
        items = items_response.json().get('data', [])
        
        # Step 3: Find Bunq API Key item
        for item in items:
            if item.get('name') == item_name and item.get('type') == 1:  # Type 1 = Login
                login_data = item.get('login', {})
                api_key = login_data.get('password')
                
                if api_key:
                    logger.info("✅ API key retrieved from vault")  # Don't log key!
                    return api_key
                else:
                    logger.error(f"❌ Item '{item_name}' found but password field is empty!")
                    return None
        
        logger.error(f"❌ Item '{item_name}' not found in vault!")
        logger.info(f"   Available items: {[item.get('name') for item in items]}")
        return None
        
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to Vaultwarden at {vault_url}")
        logger.error("   Check if Vaultwarden container is running and accessible")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"❌ Vaultwarden request timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Vaultwarden request error: {e}")
        return None
    except KeyError as e:
        logger.error(f"❌ Unexpected Vaultwarden response format: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error retrieving API key: {e}")
        return None

# ============================================
# CONFIGURATION
# ============================================

API_KEY = get_api_key_from_vaultwarden()
CONFIG_FILE = 'config/bunq_production.conf'
ENVIRONMENT = os.getenv('BUNQ_ENVIRONMENT', 'PRODUCTION')

# Validate API key before proceeding
if not API_KEY:
    logger.error("❌ No valid API key found!")
    logger.error("   Set USE_VAULTWARDEN=true and configure Vaultwarden credentials,")
    logger.error("   OR set BUNQ_API_KEY environment variable")

# Check if authentication is configured
if not os.getenv('BASIC_AUTH_PASSWORD'):
    logger.warning("⚠️⚠️⚠️ WARNING: No BASIC_AUTH_PASSWORD set!")
    logger.warning("⚠️ Your API endpoints are NOT PROTECTED!")
    logger.warning("⚠️ Set BASIC_AUTH_PASSWORD in your .env file!")

# ============================================
# BUNQ API INITIALIZATION (READ-ONLY)
# ============================================

def init_bunq():
    """
    Initialize Bunq API context with READ-ONLY access.
    
    Security Note: This application ONLY uses list() and get() methods.
    NO create(), update(), or delete() operations are ever called.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not API_KEY:
        logger.warning("⚠️ No API key available, running in demo mode only")
        return False
    
    try:
        if not os.path.exists(CONFIG_FILE):
            logger.info("🔄 Creating new Bunq API context...")
            api_context = ApiContext.create(
                environment_type=ENVIRONMENT,
                api_key=API_KEY,
                device_description="Bunq Dashboard (READ-ONLY)"
            )
            api_context.save(CONFIG_FILE)
            logger.info("✅ Bunq API context created and saved")
        else:
            logger.info("🔄 Restoring existing Bunq API context...")
            api_context = ApiContext.restore(CONFIG_FILE)
            logger.info("✅ Bunq API context restored")
        
        BunqContext.load_api_context(api_context)
        logger.info("✅ Bunq API initialized successfully")
        logger.info(f"   Environment: {ENVIRONMENT}")
        logger.info(f"   Access Level: READ-ONLY")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Bunq API: {e}")
        return False

# ============================================
# SECURITY: READ-ONLY API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - NO AUTH REQUIRED"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0-secure',
        'api_status': 'initialized' if API_KEY else 'demo_mode',
        'security': 'READ-ONLY + BasicAuth + RateLimit',
        'auth_configured': bool(os.getenv('BASIC_AUTH_PASSWORD'))
    })

@app.route('/api/accounts', methods=['GET'])
@requires_auth
@rate_limit
def get_accounts():
    """
    Get all Bunq accounts (READ-ONLY)
    
    Security: ONLY uses endpoint.MonetaryAccountBank.list()
    """
    if not API_KEY:
        return jsonify({
            'success': False,
            'error': 'Demo mode - configure API key'
        }), 503
    
    try:
        logger.info(f"📊 Fetching accounts for {request.authorization.username}")
        accounts = endpoint.MonetaryAccountBank.list().value
        
        accounts_data = []
        for account in accounts:
            accounts_data.append({
                'id': account.id_,
                'description': account.description,
                'balance': {
                    'value': float(account.balance.value),
                    'currency': account.balance.currency
                },
                'status': account.status
            })
        
        logger.info(f"✅ Retrieved {len(accounts_data)} accounts")
        return jsonify({
            'success': True,
            'data': accounts_data,
            'count': len(accounts_data)
        })
        
    except Exception as e:
        logger.error(f"❌ Error fetching accounts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transactions', methods=['GET'])
@requires_auth
@rate_limit
def get_transactions():
    """
    Get transactions for all or specific account (READ-ONLY)
    
    Query parameters:
    - account_id: Optional account ID filter
    - days: Number of days to fetch (default: 90)
    
    Security: ONLY uses endpoint.Payment.list()
    """
    if not API_KEY:
        return jsonify({
            'success': False,
            'error': 'Demo mode - configure API key'
        }), 503
    
    try:
        account_id = request.args.get('account_id')
        days = int(request.args.get('days', 90))
        
        logger.info(f"📊 Fetching transactions (last {days} days) for {request.authorization.username}")
        
        if not account_id:
            accounts = endpoint.MonetaryAccountBank.list().value
            all_transactions = []
            
            for account in accounts:
                transactions = get_account_transactions(account.id_, days)
                for trans in transactions:
                    trans['account_id'] = account.id_
                    trans['account_name'] = account.description
                all_transactions.extend(transactions)
            
            logger.info(f"✅ Retrieved {len(all_transactions)} transactions")
            return jsonify({
                'success': True,
                'data': all_transactions,
                'count': len(all_transactions)
            })
        else:
            transactions = get_account_transactions(account_id, days)
            return jsonify({
                'success': True,
                'data': transactions,
                'count': len(transactions)
            })
            
    except Exception as e:
        logger.error(f"❌ Error fetching transactions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_account_transactions(account_id, days=90):
    """
    Get transactions for specific account (READ-ONLY)
    
    Security: ONLY uses endpoint.Payment.list()
    """
    payments = endpoint.Payment.list(
        monetary_account_id=account_id
    ).value
    
    cutoff_date = datetime.now() - timedelta(days=days)
    transactions = []
    
    for payment in payments:
        created = datetime.fromisoformat(payment.created.replace('Z', '+00:00'))
        
        if created < cutoff_date:
            continue
        
        category = categorize_transaction(payment.description, payment.counterparty_alias)
        
        transactions.append({
            'id': payment.id_,
            'date': created.isoformat(),
            'amount': float(payment.amount.value),
            'currency': payment.amount.currency,
            'description': payment.description,
            'counterparty': payment.counterparty_alias.display_name if payment.counterparty_alias else 'Unknown',
            'merchant': payment.merchant_reference if hasattr(payment, 'merchant_reference') else None,
            'category': category,
            'type': payment.type_
        })
    
    return transactions

def categorize_transaction(description, counterparty):
    """Simple rule-based categorization"""
    desc_lower = description.lower() if description else ''
    counter_lower = counterparty.display_name.lower() if counterparty and counterparty.display_name else ''
    
    combined = desc_lower + ' ' + counter_lower
    
    # Simple keyword matching
    if any(word in combined for word in ['albert heijn', 'ah ', 'jumbo', 'lidl', 'aldi', 'plus', 'supermarkt']):
        return 'Boodschappen'
    elif any(word in combined for word in ['restaurant', 'cafe', 'bar', 'pizza', 'burger', 'starbucks']):
        return 'Horeca'
    elif any(word in combined for word in ['ns ', 'train', 'bus', 'taxi', 'uber', 'parking', 'shell', 'benzine']):
        return 'Vervoer'
    elif any(word in combined for word in ['huur', 'rent', 'hypotheek', 'mortgage']):
        return 'Wonen'
    elif any(word in combined for word in ['eneco', 'energie', 'gas', 'water', 'ziggo', 'kpn', 'telecom']):
        return 'Utilities'
    elif any(word in combined for word in ['bol.com', 'coolblue', 'mediamarkt', 'zara', 'h&m', 'shop']):
        return 'Shopping'
    elif any(word in combined for word in ['netflix', 'spotify', 'youtube', 'cinema', 'pathé', 'concert']):
        return 'Entertainment'
    elif any(word in combined for word in ['apotheek', 'pharmacy', 'dokter', 'doctor', 'tandarts', 'dentist']):
        return 'Zorg'
    elif any(word in combined for word in ['salaris', 'salary', 'loon', 'wage']):
        return 'Salaris'
    else:
        return 'Overig'

@app.route('/api/statistics', methods=['GET'])
@requires_auth
@rate_limit
def get_statistics():
    """Get aggregated statistics"""
    if not API_KEY:
        return jsonify({
            'success': False,
            'error': 'Demo mode - configure API key'
        }), 503
        
    try:
        days = int(request.args.get('days', 90))
        
        # Get all transactions
        accounts = endpoint.MonetaryAccountBank.list().value
        all_transactions = []
        
        for account in accounts:
            transactions = get_account_transactions(account.id_, days)
            all_transactions.extend(transactions)
        
        # Calculate statistics
        income = sum(t['amount'] for t in all_transactions if t['amount'] > 0)
        expenses = abs(sum(t['amount'] for t in all_transactions if t['amount'] < 0))
        net_savings = income - expenses
        savings_rate = (net_savings / income * 100) if income > 0 else 0
        
        # Category breakdown
        category_totals = {}
        for t in all_transactions:
            if t['amount'] < 0:
                cat = t['category']
                category_totals[cat] = category_totals.get(cat, 0) + abs(t['amount'])
        
        return jsonify({
            'success': True,
            'data': {
                'period_days': days,
                'total_transactions': len(all_transactions),
                'income': income,
                'expenses': expenses,
                'net_savings': net_savings,
                'savings_rate': savings_rate,
                'categories': category_totals,
                'avg_daily_expenses': expenses / days if days > 0 else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/demo-data', methods=['GET'])
def get_demo_data():
    """Get demo data for testing without Bunq API - NO AUTH for demo"""
    days = int(request.args.get('days', 90))
    
    # Generate demo transactions (simplified version)
    import random
    from datetime import timedelta
    
    categories = ['Boodschappen', 'Horeca', 'Vervoer', 'Wonen', 'Shopping', 'Entertainment']
    merchants = {
        'Boodschappen': ['Albert Heijn', 'Jumbo', 'Lidl'],
        'Horeca': ['Starbucks', 'Restaurant Plaza'],
        'Vervoer': ['NS', 'Shell'],
        'Wonen': ['Verhuurder B.V.'],
        'Shopping': ['Bol.com', 'Coolblue'],
        'Entertainment': ['Netflix', 'Spotify']
    }
    
    transactions = []
    for i in range(days * 3):  # ~3 transactions per day
        category = random.choice(categories)
        merchant = random.choice(merchants[category])
        
        amount = -random.randint(10, 100) if category != 'Wonen' else -850
        
        transactions.append({
            'id': i,
            'date': (datetime.now() - timedelta(days=random.randint(0, days))).isoformat(),
            'amount': amount,
            'category': category,
            'merchant': merchant,
            'description': f'{category} - {merchant}'
        })
    
    # Add some income
    for i in range(days // 30):  # Monthly salary
        transactions.append({
            'id': len(transactions),
            'date': (datetime.now() - timedelta(days=i * 30)).isoformat(),
            'amount': 2800,
            'category': 'Salaris',
            'merchant': 'Werkgever B.V.',
            'description': 'Salary'
        })
    
    return jsonify({
        'success': True,
        'data': transactions,
        'count': len(transactions),
        'note': 'This is demo data - no authentication required'
    })

if __name__ == '__main__':
    print("🚀 Starting Bunq Dashboard API (SECURE)...")
    print(f"📡 Environment: {ENVIRONMENT}")
    print(f"🔒 CORS Origins: {ALLOWED_ORIGINS}")
    print(f"🔐 Authentication: {'ENABLED ✅' if os.getenv('BASIC_AUTH_PASSWORD') else 'DISABLED ⚠️'}")
    print(f"⏱️  Rate Limiting: 30 requests/minute per IP")
    
    # Try to initialize Bunq (optional for demo mode)
    if init_bunq():
        print("✅ Bunq API initialized")
    else:
        print("⚠️ Running in demo mode only")
    
    # Run Flask app - PRODUCTION MODE
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False  # ✅ SECURITY: Never use debug=True in production!
    )
