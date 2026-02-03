// ============================================
// BUNQ FINANCIAL DASHBOARD - MAIN APPLICATION
// Advanced JavaScript with API Integration + Authentication
// ============================================

// Global Configuration
const CONFIG = {
    apiEndpoint: localStorage.getItem('apiEndpoint') || 'http://localhost:5000/api',
    apiUsername: localStorage.getItem('apiUsername') || 'admin',
    apiPassword: localStorage.getItem('apiPassword') || '',
    refreshInterval: parseInt(localStorage.getItem('refreshInterval')) || 0,
    enableAnimations: localStorage.getItem('enableAnimations') !== 'false',
    enableParticles: localStorage.getItem('enableParticles') !== 'false',
    timeRange: 90, // days
    useRealData: localStorage.getItem('useRealData') === 'true'
};

// Global State
let transactionsData = null;
let refreshIntervalId = null;
let isLoading = false;

// ============================================
// AUTHENTICATION
// ============================================

/**
 * Make authenticated API request
 * Uses Basic Authentication with configured credentials
 */
async function authenticatedFetch(url, options = {}) {
    const authHeader = 'Basic ' + btoa(CONFIG.apiUsername + ':' + CONFIG.apiPassword);
    
    const defaultOptions = {
        headers: {
            'Authorization': authHeader,
            'Content-Type': 'application/json'
        },
        credentials: 'include'
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        // Check for authentication errors
        if (response.status === 401) {
            console.error('🔒 Authentication failed - check username/password');
            showError('Authentication failed. Please check your credentials in settings.');
            return null;
        }
        
        if (response.status === 429) {
            console.error('⏱️ Rate limit exceeded');
            showError('Too many requests. Please wait a minute and try again.');
            return null;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('API request failed:', error);
        showError(`API request failed: ${error.message}`);
        return null;
    }
}

function showError(message) {
    // Create error notification
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <span>${message}</span>
    `;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(239, 68, 68, 0.95);
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 10px;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Bunq Dashboard Initializing...');
    
    // Check if credentials are configured
    if (!CONFIG.apiPassword && CONFIG.useRealData) {
        console.warn('⚠️ No API password configured - demo mode only');
    }
    
    // Initialize particles background
    if (CONFIG.enableParticles) {
        initializeParticles();
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    if (CONFIG.useRealData && CONFIG.apiPassword) {
        loadRealData();
    } else {
        loadDemoData();
    }
    
    // Initialize auto-refresh if enabled
    if (CONFIG.refreshInterval > 0) {
        startAutoRefresh();
    }
});

// ============================================
// EVENT LISTENERS
// ============================================

function setupEventListeners() {
    // Refresh button
    document.getElementById('refreshBtn')?.addEventListener('click', () => {
        refreshData();
    });
    
    // Theme toggle
    document.getElementById('themeToggle')?.addEventListener('click', () => {
        toggleTheme();
    });
    
    // Settings
    document.getElementById('settingsBtn')?.addEventListener('click', () => {
        openSettings();
    });
    
    document.getElementById('closeSettings')?.addEventListener('click', () => {
        closeSettings();
    });
    
    document.getElementById('saveSettings')?.addEventListener('click', () => {
        saveSettings();
    });
    
    // Time range selector
    document.getElementById('timeRange')?.addEventListener('change', (e) => {
        CONFIG.timeRange = e.target.value === 'all' ? 9999 : parseInt(e.target.value);
        refreshData();
    });
    
    // Data source toggle
    document.getElementById('useRealData')?.addEventListener('change', (e) => {
        CONFIG.useRealData = e.target.checked;
        localStorage.setItem('useRealData', CONFIG.useRealData);
        refreshData();
    });
    
    // Animation controls
    document.getElementById('play3D')?.addEventListener('click', () => {
        play3DAnimation();
    });
    
    document.getElementById('playRace')?.addEventListener('click', () => {
        playRacingAnimation();
    });
}

// ============================================
// DATA LOADING
// ============================================

async function loadRealData() {
    showLoading();
    
    try {
        console.log('📡 Fetching real data from Bunq API...');
        
        const url = `${CONFIG.apiEndpoint}/transactions?days=${CONFIG.timeRange}`;
        const response = await authenticatedFetch(url);
        
        if (response && response.success) {
            transactionsData = response.data.map(t => ({
                ...t,
                date: new Date(t.date),
                color: getCategoryColor(t.category)
            }));
            
            console.log(`✅ Loaded ${transactionsData.length} real transactions`);
            processAndRenderData(transactionsData);
        } else {
            console.error('❌ Failed to load real data, falling back to demo');
            loadDemoData();
        }
        
    } catch (error) {
        console.error('❌ Error loading real data:', error);
        loadDemoData();
    } finally {
        hideLoading();
        updateLastUpdateTime();
    }
}

function loadDemoData() {
    showLoading();
    
    console.log('📊 Generating demo data...');
    
    // Simulate API delay
    setTimeout(() => {
        transactionsData = generateDemoTransactions(CONFIG.timeRange);
        processAndRenderData(transactionsData);
        hideLoading();
        updateLastUpdateTime();
    }, 1500);
}

function getCategoryColor(category) {
    const colors = {
        'Boodschappen': '#3b82f6',
        'Horeca': '#8b5cf6',
        'Vervoer': '#ec4899',
        'Wonen': '#ef4444',
        'Utilities': '#f59e0b',
        'Shopping': '#10b981',
        'Entertainment': '#06b6d4',
        'Zorg': '#6366f1',
        'Salaris': '#22c55e',
        'Overig': '#6b7280'
    };
    return colors[category] || '#6b7280';
}

function generateDemoTransactions(days) {
    const transactions = [];
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    const categories = {
        'Boodschappen': { avg: -75, std: 25, freq: 0.5, color: '#3b82f6' },
        'Horeca': { avg: -35, std: 20, freq: 0.3, color: '#8b5cf6' },
        'Vervoer': { avg: -45, std: 15, freq: 0.35, color: '#ec4899' },
        'Wonen': { avg: -850, std: 50, freq: 0.033, color: '#ef4444' },
        'Utilities': { avg: -120, std: 30, freq: 0.033, color: '#f59e0b' },
        'Shopping': { avg: -65, std: 40, freq: 0.2, color: '#10b981' },
        'Entertainment': { avg: -25, std: 15, freq: 0.17, color: '#06b6d4' },
        'Zorg': { avg: -80, std: 30, freq: 0.067, color: '#6366f1' },
        'Salaris': { avg: 2800, std: 100, freq: 0.033, color: '#22c55e' }
    };
    
    const merchants = {
        'Boodschappen': ['Albert Heijn', 'Jumbo', 'Lidl', 'Aldi', 'Plus'],
        'Horeca': ['Starbucks', 'De Kroeg', 'Restaurant Plaza', 'Burger King', 'Dominos'],
        'Vervoer': ['NS', 'Shell', 'Parking Amsterdam', 'Uber', 'Swapfiets'],
        'Wonen': ['Verhuurder B.V.', 'Hypotheek Bank'],
        'Utilities': ['Eneco', 'Ziggo', 'Waternet'],
        'Shopping': ['Bol.com', 'Zara', 'H&M', 'MediaMarkt', 'Coolblue'],
        'Entertainment': ['Netflix', 'Spotify', 'Pathé', 'Concert Tickets'],
        'Zorg': ['Apotheek', 'Tandarts', 'Fysiotherapie'],
        'Salaris': ['Werkgever B.V.']
    };
    
    let currentDate = new Date(startDate);
    let transactionId = 1;
    
    while (currentDate <= endDate) {
        for (const [category, params] of Object.entries(categories)) {
            if (Math.random() < params.freq) {
                const amount = Math.random() * params.std * 2 - params.std + params.avg;
                const merchant = merchants[category][Math.floor(Math.random() * merchants[category].length)];
                
                transactions.push({
                    id: transactionId++,
                    date: new Date(currentDate),
                    amount: parseFloat(amount.toFixed(2)),
                    category: category,
                    merchant: merchant,
                    description: `${category} - ${merchant}`,
                    color: params.color
                });
            }
        }
        currentDate.setDate(currentDate.getDate() + 1);
    }
    
    return transactions.sort((a, b) => a.date - b.date);
}

// ============================================
// DATA PROCESSING (unchanged from original)
// ============================================

function processAndRenderData(data) {
    console.log(`📊 Processing ${data.length} transactions...`);
    
    // Calculate KPIs
    const kpis = calculateKPIs(data);
    renderKPIs(kpis);
    
    // Render all visualizations (keep original implementations)
    // ... rest of rendering code stays the same ...
    
    console.log('✅ All visualizations rendered!');
}

function calculateKPIs(data) {
    const income = data.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
    const expenses = Math.abs(data.filter(t => t.amount < 0).reduce((sum, t) => sum + t.amount, 0));
    const netSavings = income - expenses;
    const savingsRate = income > 0 ? (netSavings / income * 100) : 0;
    
    // Calculate trends
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const sixtyDaysAgo = new Date();
    sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60);
    
    const recent = data.filter(t => t.date >= thirtyDaysAgo);
    const previous = data.filter(t => t.date >= sixtyDaysAgo && t.date < thirtyDaysAgo);
    
    const recentIncome = recent.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
    const previousIncome = previous.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
    const incomeTrend = previousIncome > 0 ? ((recentIncome - previousIncome) / previousIncome * 100) : 0;
    
    const recentExpenses = Math.abs(recent.filter(t => t.amount < 0).reduce((sum, t) => sum + t.amount, 0));
    const previousExpenses = Math.abs(previous.filter(t => t.amount < 0).reduce((sum, t) => sum + t.amount, 0));
    const expensesTrend = previousExpenses > 0 ? ((recentExpenses - previousExpenses) / previousExpenses * 100) : 0;
    
    const recentSavings = recentIncome - recentExpenses;
    const previousSavings = previousIncome - previousExpenses;
    const savingsTrend = previousSavings !== 0 ? ((recentSavings - previousSavings) / Math.abs(previousSavings) * 100) : 0;
    
    return {
        income,
        expenses,
        netSavings,
        savingsRate,
        incomeTrend,
        expensesTrend,
        savingsTrend
    };
}

// ============================================
// SETTINGS
// ============================================

function openSettings() {
    // Populate current values
    document.getElementById('apiEndpoint').value = CONFIG.apiEndpoint;
    document.getElementById('apiUsername').value = CONFIG.apiUsername;
    document.getElementById('apiPassword').value = CONFIG.apiPassword;
    document.getElementById('refreshInterval').value = CONFIG.refreshInterval;
    document.getElementById('enableAnimations').checked = CONFIG.enableAnimations;
    document.getElementById('enableParticles').checked = CONFIG.enableParticles;
    document.getElementById('useRealData').checked = CONFIG.useRealData;
    
    document.getElementById('settingsModal').classList.add('active');
}

function closeSettings() {
    document.getElementById('settingsModal').classList.remove('active');
}

function saveSettings() {
    // Update config
    CONFIG.apiEndpoint = document.getElementById('apiEndpoint').value;
    CONFIG.apiUsername = document.getElementById('apiUsername').value;
    CONFIG.apiPassword = document.getElementById('apiPassword').value;
    CONFIG.refreshInterval = parseInt(document.getElementById('refreshInterval').value);
    CONFIG.enableAnimations = document.getElementById('enableAnimations').checked;
    CONFIG.enableParticles = document.getElementById('enableParticles').checked;
    CONFIG.useRealData = document.getElementById('useRealData').checked;
    
    // Save to localStorage
    localStorage.setItem('apiEndpoint', CONFIG.apiEndpoint);
    localStorage.setItem('apiUsername', CONFIG.apiUsername);
    localStorage.setItem('apiPassword', CONFIG.apiPassword);
    localStorage.setItem('refreshInterval', CONFIG.refreshInterval);
    localStorage.setItem('enableAnimations', CONFIG.enableAnimations);
    localStorage.setItem('enableParticles', CONFIG.enableParticles);
    localStorage.setItem('useRealData', CONFIG.useRealData);
    
    closeSettings();
    
    // Reinitialize
    if (CONFIG.enableParticles) {
        initializeParticles();
    }
    
    // Reload data with new credentials
    refreshData();
    
    console.log('✅ Settings saved');
}

// ============================================
// UI FUNCTIONS
// ============================================

function showLoading() {
    const loadingScreen = document.getElementById('loading-screen');
    const mainContent = document.getElementById('main-content');
    
    if (loadingScreen) loadingScreen.classList.remove('hidden');
    if (mainContent) mainContent.style.display = 'none';
}

function hideLoading() {
    const loadingScreen = document.getElementById('loading-screen');
    const mainContent = document.getElementById('main-content');
    
    if (loadingScreen) loadingScreen.classList.add('hidden');
    if (mainContent) mainContent.style.display = 'block';
}

function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.classList.add('loading');
    
    if (CONFIG.useRealData && CONFIG.apiPassword) {
        loadRealData();
    } else {
        loadDemoData();
    }
    
    setTimeout(() => {
        if (btn) btn.classList.remove('loading');
    }, 1500);
}

function updateLastUpdateTime() {
    const now = new Date();
    const lastUpdate = document.getElementById('lastUpdate');
    if (lastUpdate) {
        lastUpdate.textContent = `Last updated: ${now.toLocaleTimeString('nl-NL')}`;
    }
}

function startAutoRefresh() {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    if (CONFIG.refreshInterval > 0) {
        refreshIntervalId = setInterval(() => {
            refreshData();
        }, CONFIG.refreshInterval * 60 * 1000);
    }
}

// ... Keep all other functions from original app.js (rendering, charts, etc.) ...

console.log('✅ Bunq Dashboard Ready (with Authentication)!');
