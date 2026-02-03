#!/usr/bin/env python3
"""
Bunq Dashboard API Proxy - Production Edition
================================================
Flask backend with Vaultwarden secret management
READ-ONLY Bunq API access for maximum security
Serves both API and Frontend on port 5000 (single origin)

SECURITY FEATURES:
- Vaultwarden integration for secret management
- READ-ONLY Bunq API access (no write operations)
- Single-origin architecture (eliminates CORS issues)
- VPN-only access recommended (no port forwarding!)
- Demo mode fallback for testing
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.model.generated import endpoint
from datetime import datetime, timedelta
import os
import json
import requests
import logging
import random

# ============================================
# LOGGING CONFIGURATION
# ============================================

os.makedirs('logs', exist_ok=True)

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
# FLASK APP INITIALIZATION (Single Origin)
# ============================================

# Serve static files from current directory
# This eliminates CORS issues and simplifies mobile access
app = Flask(__name__, static_url_path='', static_folder='.')

# CORS kept for defense-in-depth
CORS(app)

logger.info("🌐 Flask configured for single-origin architecture")
logger.info("   Frontend + API both on port 5000")

# ============================================
# STATIC FILE SERVING (Frontend)
# ============================================

@app.route('/')
def serve_dashboard():
    """Serve the main dashboard HTML"""
    try:
        logger.debug("📄 Serving index.html")
        return send_from_directory('.', 'index.html')
    except Exception as e:
        logger.error(f"❌ Error serving index.html: {e}")
        return jsonify({'error': 'Dashboard not found. Ensure index.html is in the same directory.'}), 404

@app.route('/<path:path>')
def serve_static(path):
    """
    Serve static assets (CSS, JS, images)
    Security: Prevents directory traversal
    """
    # Security check
    if '..' in path or path.startswith('/'):
        logger.warning(f"⚠️ Blocked suspicious path: {path}")
        return jsonify({'error': 'Invalid path'}), 400
    
    try:
        logger.debug(f"📦 Serving: {path}")
        return send_from_directory('.', path)
    except Exception as e:
        logger.error(f"❌ File not found: {path}")
        return jsonify({'error': 'File not found'}), 404

# ============================================
# VAULTWARDEN SECRET RETRIEVAL
# ============================================

def get_api_key_from_vaultwarden():
    """
    Securely retrieve Bunq API key from Vaultwarden vault.
    
    This is the RECOMMENDED method for production deployments.
    Benefits:
    - API key never stored in plain text
    - Easy rotation (update vault, restart container)
    - Centralized secret management
    - Audit logging
    
    Returns:
        str: Bunq API key or None if retrieval failed
    """
    
    use_vaultwarden = os.getenv('USE_VAULTWARDEN', 'false').lower() == 'true'
    
    if not use_vaultwarden:
        logger.info("📝 Vaultwarden disabled, using environment variable")
        api_key = os.getenv('BUNQ_API_KEY', '')
        if api_key:
            logger.info(f"✅ API key loaded from environment: {api_key[:10]}...")
        else:
            logger.warning("⚠️ No API key found in environment")
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
        logger.error("   Falling back to demo mode")
        return None
    
    try:
        # Step 1: Authenticate with Vaultwarden using OAuth2
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
                    logger.info(f"✅ API key retrieved from vault: {api_key[:10]}...")
                    return api_key
                else:
                    logger.error(f"❌ Item '{item_name}' found but password field is empty!")
                    return None
        
        logger.error(f"❌ Item '{item_name}' not found in vault!")
        logger.info(f"   Available items: {[item.get('name') for item in items]}")
        return None
        
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to Vaultwarden at {vault_url}")
        logger.error("   Check if Vaultwarden container is running")
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

# ============================================
# BUNQ API INITIALIZATION (READ-ONLY)
# ============================================

def init_bunq():
    """
    Initialize Bunq API context with READ-ONLY access.
    
    Security Note: This application ONLY uses:
    - endpoint.MonetaryAccountBank.list() (READ)
    - endpoint.Payment.list() (READ)
    - endpoint.User.get() (READ)
    
    NO write operations (create/update/delete) are ever called!
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not API_KEY:
        logger.warning("⚠️ No API key available, running in demo mode only")
        return False
    
    try:
        os.makedirs('config', exist_ok=True)
        
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
# API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.1.0-unified',
        'api_status': 'initialized' if API_KEY else 'demo_mode',
        'security': 'READ-ONLY',
        'architecture': 'single-origin (port 5000)',
        'vaultwarden_enabled': os.getenv('USE_VAULTWARDEN', 'false').lower() == 'true'
    })

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """
    Get transactions (READ-ONLY)
    
    Query Parameters:
    - timeRange: Number of days to fetch (default: 90)
    - account_id: Specific account ID (optional)
    
    Returns demo data if Bunq API is unavailable.
    """
    
    # Get time range parameter (supports both names for compatibility)
    days = int(request.args.get('timeRange', request.args.get('days', 90)))
    
    # Check if we have API key
    if not API_KEY:
        logger.info(f"📊 Demo mode: Generating demo transactions ({days} days)")
        return generate_demo_transactions(days)
    
    try:
        account_id = request.args.get('account_id')
        
        logger.info(f"📊 Fetching real transactions (last {days} days)...")
        
        if not account_id:
            # Fetch from all accounts
            accounts = endpoint.MonetaryAccountBank.list().value
            all_transactions = []
            
            for account in accounts:
                transactions = get_account_transactions(account.id_, days)
                for trans in transactions:
                    trans['account_id'] = account.id_
                    trans['account_name'] = account.description
                all_transactions.extend(transactions)
            
            logger.info(f"✅ Retrieved {len(all_transactions)} real transactions")
            return jsonify({
                'success': True,
                'data': all_transactions,
                'count': len(all_transactions),
                'source': 'bunq_api'
            })
        else:
            # Fetch from specific account
            transactions = get_account_transactions(account_id, days)
            return jsonify({
                'success': True,
                'data': transactions,
                'count': len(transactions),
                'source': 'bunq_api'
            })
            
    except Exception as e:
        logger.error(f"❌ Error fetching transactions: {e}")
        logger.info("⚠️ Falling back to demo data")
        return generate_demo_transactions(days)

def get_account_transactions(account_id, days=90):
    """
    Get transactions for specific account (READ-ONLY)
    
    Security: ONLY uses endpoint.Payment.list() - no write operations!
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

def generate_demo_transactions(days=90):
    """
    Generate demo transactions for testing without API key.
    This allows the dashboard to work immediately for development/testing.
    """
    transactions = []
    
    categories = {
        'Boodschappen': ['Albert Heijn', 'Jumbo', 'Lidl'],
        'Wonen': ['Vattenfall', 'Ziggo', 'Huur'],
        'Vervoer': ['Shell', 'NS', 'Uber'],
        'Uitgaan': ['Restaurant De Goudvis', 'Cinema', 'Bar 123'],
        'Verzekering': ['Interpolis', 'Zilveren Kruis']
    }
    
    # Generate expenses
    for i in range(days * 2):
        category = random.choice(list(categories.keys()))
        merchant = random.choice(categories[category])
        amount = -random.randint(10, 150)
        
        transactions.append({
            'id': i,
            'date': (datetime.now() - timedelta(days=random.randint(0, days))).isoformat(),
            'amount': amount,
            'category': category,
            'merchant': merchant,
            'description': f'{category} - {merchant}'
        })
    
    # Add salary (monthly)
    for i in range(days // 30 + 1):
        transactions.append({
            'id': 9000 + i,
            'date': (datetime.now() - timedelta(days=i * 30)).isoformat(),
            'amount': 3500,
            'category': 'Salaris',
            'merchant': 'Werkgever B.V.',
            'description': 'Monthly Salary'
        })
    
    logger.info(f"✅ Generated {len(transactions)} demo transactions")
    
    return jsonify({
        'success': True,
        'data': transactions,
        'count': len(transactions),
        'source': 'demo_data',
        'note': 'Configure Bunq API for real transactions'
    })

def categorize_transaction(description, counterparty):
    """
    Simple rule-based transaction categorization.
    Can be enhanced with ML in the future.
    """
    desc_lower = description.lower() if description else ''
    counter_lower = counterparty.display_name.lower() if counterparty and counterparty.display_name else ''
    
    combined = desc_lower + ' ' + counter_lower
    
    # Categorization rules
    if any(word in combined for word in ['albert heijn', 'ah ', 'jumbo', 'lidl', 'aldi', 'plus', 'supermarkt']):
        return 'Boodschappen'
    elif any(word in combined for word in ['restaurant', 'cafe', 'bar', 'pizza', 'burger', 'starbucks']):
        return 'Uitgaan'
    elif any(word in combined for word in ['ns ', 'train', 'bus', 'taxi', 'uber', 'parking', 'shell', 'benzine']):
        return 'Vervoer'
    elif any(word in combined for word in ['huur', 'rent', 'hypotheek', 'mortgage']):
        return 'Wonen'
    elif any(word in combined for word in ['eneco', 'energie', 'gas', 'water', 'ziggo', 'kpn', 'telecom']):
        return 'Wonen'
    elif any(word in combined for word in ['interpolis', 'verzekering', 'insurance', 'zilveren kruis']):
        return 'Verzekering'
    elif any(word in combined for word in ['salaris', 'salary', 'loon', 'wage']):
        return 'Salaris'
    else:
        return 'Overig'

# ============================================
# STARTUP
# ============================================

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 Bunq Financial Dashboard - Starting...")
    print("=" * 70)
    print(f"📡 Environment:       {ENVIRONMENT}")
    print(f"🔒 Security:          READ-ONLY API access")
    print(f"🌐 Architecture:      Single-origin (port 5000 only)")
    print(f"🔑 Secret Management: {'Vaultwarden' if os.getenv('USE_VAULTWARDEN') == 'true' else 'Environment Variables'}")
    print("=" * 70)
    
    # Initialize Bunq API
    if init_bunq():
        print("✅ Bunq API initialized - Live data mode")
    else:
        print("⚠️  Running in demo mode - Configure Vaultwarden for live data")
    
    print("=" * 70)
    print("🌐 Dashboard accessible at:")
    print("   📱 Local:   http://localhost:5000")
    print("   🏠 LAN:     http://192.168.x.x:5000")
    print("   🔐 VPN:     http://10.8.0.x:5000")
    print("=" * 70)
    print("⚠️  SECURITY REMINDER:")
    print("   - Access ONLY via VPN for security")
    print("   - DO NOT forward port 5000 on your router")
    print("   - All banking data travels encrypted via VPN tunnel")
    print("=" * 70)
    
    # Start Flask (serves both API and Frontend)
    app.run(
        host='0.0.0.0',  # Required for Docker
        port=5000,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
