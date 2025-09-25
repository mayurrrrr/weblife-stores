// Laptop Intelligence Engine - Frontend JavaScript

// Global variables
let laptops = [];
let selectedLaptops = [];
let conversationId = null;
let priceChart = null;
let ratingsChart = null;

// API base URL
const API_BASE = 'http://localhost:8000/api/v1';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Set up tab navigation
    setupTabNavigation();
    
    // Load initial data
    loadLaptops();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize charts
    initializeCharts();
}

function setupTabNavigation() {
    const navLinks = document.querySelectorAll('.nav-link[data-tab]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    console.log('[DEBUG] Switching to tab:', tabId);
    
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const targetTab = document.getElementById(`${tabId}-tab`);
    console.log('[DEBUG] Target tab element:', targetTab);
    
    if (targetTab) {
        targetTab.classList.add('active');
        console.log('[DEBUG] Tab activated successfully');
    } else {
        console.error('[DEBUG] Tab element not found:', `${tabId}-tab`);
    }
    
    // Load tab-specific data
    console.log('[DEBUG] Loading tab data for:', tabId);
    loadTabData(tabId);
}

function loadTabData(tabId) {
    console.log('[DEBUG] loadTabData called with tabId:', tabId);
    
    switch(tabId) {
        case 'trends':
            console.log('[DEBUG] Loading trends data');
            ensureTrendsDropdown();
            loadPriceTrends();
            break;
        case 'reviews':
            console.log('[DEBUG] Loading reviews data');
            // Ensure ratings chart is initialized before loading data
            if (!ratingsChart) {
                console.log('[DEBUG] Ratings chart not found, reinitializing...');
                initializeRatingsChart();
            }
            // Populate laptop dropdown
            populateLaptopDropdown();
            // Default to 'all' and load via unified path
            setTimeout(() => {
                const sel = document.getElementById('laptopSelect');
                if (sel) sel.value = 'all';
                console.log('[DEBUG] Calling loadSelectedLaptopReviews after setup');
                loadSelectedLaptopReviews();
                if (ratingsChart) {
                    ratingsChart.resize();
                }
            }, 50);
            break;
        case 'compare':
            console.log('[DEBUG] Loading comparison data');
            ensureCompareSelector();
            updateComparisonView();
            break;
        default:
            console.log('[DEBUG] Unknown tab:', tabId);
    }
}

// Inject a "Show all reviews" toggle next to the laptop dropdown if missing
function ensureShowAllToggle() {
    try {
        const reviewsHeader = document.querySelector('#reviews-tab .d-flex.justify-content-between');
        // Fallback to the known header container
        const headerContainer = reviewsHeader || document.querySelector('#reviews-tab .d-flex.justify-content-between.align-items-center');
        if (!headerContainer) return;
        if (document.getElementById('showAllReviews')) return;
        const toggleWrapper = document.createElement('div');
        toggleWrapper.className = 'ms-3';
        toggleWrapper.innerHTML = `
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="showAllReviews">
                <label class="form-check-label" for="showAllReviews">Show all reviews</label>
            </div>
        `;
        headerContainer.appendChild(toggleWrapper);
        const checkbox = toggleWrapper.querySelector('#showAllReviews');
        checkbox.addEventListener('change', () => {
            // Re-load based on current selection
            if (typeof loadSelectedLaptopReviews === 'function') {
                loadSelectedLaptopReviews();
            } else {
                loadReviewsData();
            }
        });
    } catch (e) {
        console.error('[DEBUG] ensureShowAllToggle error:', e);
    }
}

function isShowAllEnabled() {
    const cb = document.getElementById('showAllReviews');
    return !!(cb && cb.checked);
}

function setupEventListeners() {
    // View mode toggle
    document.getElementById('gridView').addEventListener('change', function() {
        if (this.checked) {
            displayLaptops(laptops, 'grid');
        }
    });
    
    document.getElementById('listView').addEventListener('change', function() {
        if (this.checked) {
            displayLaptops(laptops, 'list');
        }
    });
}

// API Functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call error:', error);
        showError(`API Error: ${error.message}`);
        return null;
    }
}

// Laptop Functions
async function loadLaptops() {
    console.log('[DEBUG] Loading laptops from API...');
    showLoading(true);
    
    try {
        const data = await apiCall('/laptops');
        console.log('[DEBUG] API response:', data);
        if (data) {
            laptops = data;
            console.log('[DEBUG] Loaded', laptops.length, 'laptops');
            displayLaptops(laptops);
        } else {
            console.log('[DEBUG] No data received from API');
            showError('No laptop data received from server');
        }
    } catch (error) {
        console.error('[DEBUG] Error loading laptops:', error);
        showError('Failed to load laptops: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function displayLaptops(laptopsData, viewMode = 'grid') {
    console.log('[DEBUG] Displaying laptops:', laptopsData?.length, 'items, view mode:', viewMode);
    const container = document.getElementById('laptops-container');
    
    if (!laptopsData || laptopsData.length === 0) {
        console.log('[DEBUG] No laptops to display');
        container.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle"></i> No laptops found matching your criteria.
                </div>
            </div>
        `;
        return;
    }
    
    if (viewMode === 'grid') {
        container.className = 'row';
        container.innerHTML = laptopsData.map(laptop => createLaptopCard(laptop)).join('');
    } else {
        container.className = '';
        container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Brand & Model</th>
                            <th>Price</th>
                            <th>CPU</th>
                            <th>RAM</th>
                            <th>Storage</th>
                            <th>Rating</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${laptopsData.map(laptop => createLaptopRow(laptop)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
}

function createLaptopCard(laptop) {
    const specs = laptop.specifications || {};
    const cpu = Array.isArray(specs.cpu) ? specs.cpu[0] : 'Not specified';
    const ram = Array.isArray(specs.ram) ? specs.ram[0] : 'Not specified';
    const storage = Array.isArray(specs.storage) ? specs.storage[0] : 'Not specified';
    
    return `
        <div class="col-md-4 col-lg-3 mb-4">
            <div class="card laptop-card" onclick="showLaptopDetails(${laptop.id})">
                <div class="laptop-image">
                    <i class="fas fa-laptop"></i>
                </div>
                <div class="card-body">
                    <h6 class="laptop-title">${laptop.brand} ${laptop.model_name}</h6>
                    <div class="laptop-price">$999</div>
                    <div class="laptop-specs">
                        <small><i class="fas fa-microchip"></i> ${cpu}</small><br>
                        <small><i class="fas fa-memory"></i> ${ram}</small><br>
                        <small><i class="fas fa-hdd"></i> ${storage}</small>
                    </div>
                    <div class="laptop-rating">
                        <span class="rating-stars">★★★★☆</span>
                        <small class="text-muted">(4.2)</small>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function createLaptopRow(laptop) {
    const specs = laptop.specifications || {};
    const cpu = Array.isArray(specs.cpu) ? specs.cpu[0] : 'Not specified';
    const ram = Array.isArray(specs.ram) ? specs.ram[0] : 'Not specified';
    const storage = Array.isArray(specs.storage) ? specs.storage[0] : 'Not specified';
    
    return `
        <tr onclick="showLaptopDetails(${laptop.id})" style="cursor: pointer;">
            <td>
                <strong>${laptop.brand}</strong><br>
                <small class="text-muted">${laptop.model_name}</small>
            </td>
            <td><span class="text-success fw-bold">$999</span></td>
            <td><small>${cpu}</small></td>
            <td><small>${ram}</small></td>
            <td><small>${storage}</small></td>
            <td>
                <span class="rating-stars">★★★★☆</span>
                <small class="text-muted">(4.2)</small>
            </td>
        </tr>
    `;
}

async function showLaptopDetails(laptopId) {
    try {
        const laptop = await apiCall(`/laptops/${laptopId}`);
        if (laptop) {
            displayLaptopModal(laptop);
        }
    } catch (error) {
        showError('Failed to load laptop details');
    }
}

function displayLaptopModal(laptop) {
    const modal = document.getElementById('laptopModal');
    const title = document.getElementById('laptopModalTitle');
    const body = document.getElementById('laptopModalBody');
    
    title.textContent = `${laptop.brand} ${laptop.model_name}`;
    
    const specs = laptop.specifications || {};
    const latestOffer = laptop.latest_offer;
    
    body.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="laptop-image mb-3" style="height: 250px;">
                    <i class="fas fa-laptop"></i>
                </div>
                ${latestOffer ? `
                    <div class="card">
                        <div class="card-header">Current Offer</div>
                        <div class="card-body">
                            <h4 class="text-success">$${latestOffer.price}</h4>
                            <p class="mb-1">
                                <span class="badge ${latestOffer.is_available ? 'bg-success' : 'bg-danger'}">
                                    ${latestOffer.is_available ? 'Available' : 'Out of Stock'}
                                </span>
                            </p>
                            ${latestOffer.promotions && latestOffer.promotions.length > 0 ? `
                                <div class="mt-2">
                                    <small class="text-muted">Promotions:</small><br>
                                    ${latestOffer.promotions.map(promo => `<span class="badge bg-warning text-dark">${promo}</span>`).join(' ')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
            </div>
            <div class="col-md-6">
                <h5>Specifications</h5>
                <table class="table table-sm">
                    ${Object.entries(specs).map(([key, value]) => `
                        <tr>
                            <td class="fw-bold">${key.charAt(0).toUpperCase() + key.slice(1)}:</td>
                            <td>${Array.isArray(value) ? value.join(', ') : value}</td>
                        </tr>
                    `).join('')}
                </table>
                
                ${laptop.review_summary ? `
                    <h5 class="mt-3">Reviews</h5>
                    <div class="d-flex align-items-center">
                        <span class="rating-stars me-2">★★★★☆</span>
                        <span>${laptop.review_summary.average_rating}/5</span>
                        <span class="text-muted ms-2">(${laptop.total_reviews} reviews)</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    // Hide modal compare button to enforce Compare tab usage
    const addToCompareBtn = document.getElementById('addToCompareBtn');
    if (addToCompareBtn) {
        addToCompareBtn.style.display = 'none';
        addToCompareBtn.onclick = null;
    }
    
    new bootstrap.Modal(modal).show();
}

// Filter Functions
async function applyFilters() {
    const brand = document.getElementById('brandFilter').value;
    const minPrice = document.getElementById('minPrice').value;
    const maxPrice = document.getElementById('maxPrice').value;
    const searchTerm = document.getElementById('searchTerm').value;
    const availableOnly = document.getElementById('availableOnly').checked;
    
    const params = new URLSearchParams();
    if (brand) params.append('brand', brand);
    if (minPrice) params.append('min_price', minPrice);
    if (maxPrice) params.append('max_price', maxPrice);
    if (searchTerm) params.append('search_term', searchTerm);
    params.append('available_only', availableOnly);
    
    showLoading(true);
    
    try {
        const data = await apiCall(`/laptops?${params.toString()}`);
        if (data) {
            laptops = data;
            displayLaptops(laptops);
        }
    } catch (error) {
        showError('Failed to apply filters');
    } finally {
        showLoading(false);
    }
}

// Comparison Functions
function addToCompare(laptopId) {
    const laptop = laptops.find(l => l.id === laptopId);
    if (laptop && !selectedLaptops.find(l => l.id === laptopId)) {
        selectedLaptops.push(laptop);
        updateComparisonView();
        showSuccess(`${laptop.brand} ${laptop.model_name} added to comparison`);
    }
}

function removeFromCompare(laptopId) {
    selectedLaptops = selectedLaptops.filter(l => l.id !== laptopId);
    updateComparisonView();
}

function updateComparisonView() {
    const container = document.getElementById('comparison-container');
    
    if (selectedLaptops.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i> Select laptops from the Explore tab to compare them here.
            </div>
        `;
        return;
    }
    
    // Create comparison table
    const specs = ['cpu', 'ram', 'storage', 'display', 'graphics', 'battery'];
    
    container.innerHTML = `
        <div class="table-responsive">
            <table class="table comparison-table">
                <thead>
                    <tr>
                        <th>Specification</th>
                        ${selectedLaptops.map(laptop => `
                            <th>
                                ${laptop.brand} ${laptop.model_name}
                                <button class="btn btn-sm btn-outline-light ms-2" onclick="removeFromCompare(${laptop.id})">
                                    <i class="fas fa-times"></i>
                                </button>
                            </th>
                        `).join('')}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="fw-bold">Price</td>
                        ${selectedLaptops.map(() => '<td class="text-success fw-bold">$999</td>').join('')}
                    </tr>
                    ${specs.map(spec => `
                        <tr>
                            <td class="fw-bold">${spec.charAt(0).toUpperCase() + spec.slice(1)}</td>
                            ${selectedLaptops.map(laptop => {
                                const value = laptop.specifications?.[spec];
                                return `<td>${Array.isArray(value) ? value.join(', ') : value || 'Not specified'}</td>`;
                            }).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// Chat Functions
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    console.log('[DEBUG] sendMessage called');
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) {
        console.log('[DEBUG] Empty message, returning');
        return;
    }
    
    console.log('[DEBUG] Sending message:', message);
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    input.value = '';
    
    // Show typing indicator
    addTypingIndicator();
    
    try {
        console.log('[DEBUG] Making API call to /chat');
        const response = await apiCall('/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });
        
        console.log('[DEBUG] Chat API response:', response);
        
        if (response) {
            conversationId = response.conversation_id;
            removeTypingIndicator();
            addMessageToChat(response.response, 'assistant', response.sources);
        }
    } catch (error) {
        console.error('[DEBUG] Chat error:', error);
        removeTypingIndicator();
        addMessageToChat('Sorry, I encountered an error. Please try again. Error: ' + error.message, 'assistant');
    }
}

function addMessageToChat(message, sender, sources = null) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const icon = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    // Create sources HTML if sources are provided
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources mt-2">
                <small class="text-muted">
                    <i class="fas fa-info-circle"></i> <strong>Sources:</strong> ${sources.join(', ')}
                </small>
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${icon} ${message}
            ${sourcesHtml}
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <i class="fas fa-robot"></i> <span class="loading-spinner"></span> Typing...
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Recommendation Functions
async function getRecommendations() {
    const budgetMin = document.getElementById('budget-min').value;
    const budgetMax = document.getElementById('budget-max').value;
    const useCase = document.getElementById('use-case').value;
    const preferredBrand = document.getElementById('preferred-brand').value;
    
    const requestData = {};
    if (budgetMin) requestData.budget_min = parseFloat(budgetMin);
    if (budgetMax) requestData.budget_max = parseFloat(budgetMax);
    if (useCase) requestData.use_case = useCase;
    if (preferredBrand) requestData.preferred_brand = preferredBrand;
    
    try {
        const response = await apiCall('/recommend', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        if (response) {
            displayRecommendations(response);
        }
    } catch (error) {
        showError('Failed to get recommendations');
    }
}

function displayRecommendations(recommendations) {
    const message = `Based on your criteria, here are my recommendations:\n\n${recommendations.rationale}`;
    addMessageToChat(message, 'assistant');
    
    // Also update the explore tab with recommended laptops
    if (recommendations.recommendations && recommendations.recommendations.length > 0) {
        switchTab('explore');
        displayLaptops(recommendations.recommendations);
    }
}

function quickRecommend(type) {
    const recommendations = {
        business: 'I recommend looking for laptops with Intel i5 or i7 processors, 8-16GB RAM, and SSD storage for business use.',
        student: 'For students, consider budget-friendly options with good battery life and sufficient performance for coursework.',
        gaming: 'Gaming laptops should have dedicated graphics cards, fast processors, and adequate cooling systems.',
        ultrabook: 'Ultrabooks prioritize portability with lightweight design, long battery life, and solid performance.'
    };
    
    addMessageToChat(`Tell me about ${type} laptops`, 'user');
    addMessageToChat(recommendations[type], 'assistant');
    
    switchTab('chat');
}

// Chart Functions
function initializeCharts() {
    initializePriceChart();
    initializeRatingsChart();
}

function initializePriceChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Price',
                data: [],
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Laptop Price Trends'
                },
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: { display: true, text: 'Price ($)' }
                },
                x: { ticks: { maxRotation: 0, autoSkip: true } }
            }
        }
    });
}

function initializeRatingsChart() {
    console.log('[DEBUG] Initializing ratings chart...');
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('[DEBUG] Chart.js library not loaded!');
        return;
    }
    
    const canvas = document.getElementById('ratingsChart');
    
    if (!canvas) {
        console.error('[DEBUG] ratingsChart canvas element not found!');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    console.log('[DEBUG] Canvas context obtained, creating chart...');
    
    ratingsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['5 Stars', '4 Stars', '3 Stars', '2 Stars', '1 Star'],
            datasets: [{
                data: [0, 0, 0, 0, 0], // Will be populated by loadReviewsData()
                backgroundColor: [
                    '#198754',
                    '#20c997',
                    '#ffc107',
                    '#fd7e14',
                    '#dc3545'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Rating Distribution'
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    console.log('[DEBUG] Ratings chart initialized successfully');
}

async function loadPriceTrends(laptopId) {
    try {
        ensureTrendsDropdown();
        let selectedId = laptopId;
        const sellerEl = document.getElementById('trendsSeller');
        if (!selectedId) {
            const select = document.querySelector('#trendsSelect');
            if (select && select.value) {
                selectedId = parseInt(select.value);
            } else if (laptops && laptops.length > 0) {
                selectedId = laptops[0].id;
                if (select) select.value = String(selectedId);
            } else {
                return;
            }
        }
        const offers = await apiCall(`/laptops/${selectedId}/offers`);
        const labels = [];
        const data = [];
        let latestSeller = '';
        if (offers && offers.length > 0) {
            // sort ascending by timestamp
            offers.sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
            offers.forEach(o => {
                labels.push(new Date(o.timestamp).toLocaleDateString());
                data.push(o.price);
            });
            const latest = offers[offers.length - 1];
            latestSeller = latest && latest.seller ? latest.seller : '';
        }
        if (priceChart) {
            priceChart.data.labels = labels;
            priceChart.data.datasets[0].data = data;
            priceChart.update();
        }
        if (sellerEl) {
            sellerEl.textContent = latestSeller ? `Seller: ${latestSeller}` : '';
        }
    } catch (error) {
        console.error('[DEBUG] Error loading price trends:', error);
        if (priceChart) {
            priceChart.data.labels = [];
            priceChart.data.datasets[0].data = [];
            priceChart.update();
        }
        const sellerEl = document.getElementById('trendsSeller');
        if (sellerEl) sellerEl.textContent = '';
    }
}

// Populate laptop dropdown for reviews tab
function populateLaptopDropdown() {
    const dropdown = document.getElementById('laptopSelect');
    if (!dropdown) return;
    
    // Clear existing options except "All Laptops"
    dropdown.innerHTML = '<option value="all">All Laptops</option>';
    
    // Add laptop options
    if (laptops && laptops.length > 0) {
        laptops.forEach(laptop => {
            const option = document.createElement('option');
            option.value = laptop.id;
            option.textContent = `${laptop.brand} ${laptop.model_name}`;
            dropdown.appendChild(option);
        });
    }
}

// Load reviews for selected laptop
async function loadSelectedLaptopReviews() {
    const dropdown = document.getElementById('laptopSelect');
    const selectedLaptopId = dropdown ? dropdown.value : 'all';
    
    console.log('[DEBUG] Loading reviews for selected laptop:', selectedLaptopId);
    
    try {
        if (selectedLaptopId === 'all') {
            // Load all reviews
            await loadReviewsData();
        } else {
            // Load reviews for specific laptop
            await loadSingleLaptopReviews(parseInt(selectedLaptopId));
        }
    } catch (error) {
        console.error('[DEBUG] Error loading selected laptop reviews:', error);
        showError('Failed to load reviews for selected laptop');
    }
}

// Fetch and render simple insights for reviews
async function loadReviewInsights(laptopId) {
    try {
        const target = document.getElementById('reviews-insights');
        if (!laptopId || !target) return;
        const data = await apiCall(`/laptops/${laptopId}/reviews/insights`);
        if (!data) return;
        let trendsHtml = '';
        if (data.trends && data.trends.length > 0) {
            const last = data.trends.slice(-6);
            trendsHtml = `<div class="small text-muted">Last months: ${last.map(t => `${t.month} (${t.count})`).join(' · ')}</div>`;
        }
        let aspectsHtml = '';
        if (data.aspects && data.aspects.length > 0) {
            aspectsHtml = `<div class="mt-2">` +
                data.aspects.map(a => `<span class="badge bg-light text-dark me-1 mb-1">${a.name} · ${a.mentions} · ${a.avg_rating}</span>`).join(' ') +
                `</div>`;
        }
        target.innerHTML = `
            <div>
                ${trendsHtml}
                ${aspectsHtml || '<span class="text-muted small">No insights yet</span>'}
            </div>
        `;
    } catch (e) {
        console.error('[DEBUG] insights error', e);
    }
}

// Hook into single laptop loading
async function loadSingleLaptopReviews(laptopId) {
    console.log('[DEBUG] Loading reviews for laptop ID:', laptopId);
    
    try {
        const laptop = laptops.find(l => l.id === laptopId);
        if (!laptop) {
            console.error('[DEBUG] Laptop not found:', laptopId);
            return;
        }
        // Load insights (does not alter reviews list)
        loadReviewInsights(laptopId);
        
        // Load reviews for this specific laptop
        const reviews = await apiCall(`/laptops/${laptopId}/reviews`);
        console.log(`[DEBUG] Received ${reviews ? reviews.length : 0} reviews for laptop ${laptopId}`);
        
        let ratingCounts = [0, 0, 0, 0, 0];
        let allReviews = [];
        
        if (reviews && reviews.length > 0) {
            allReviews = reviews.map(review => ({
                ...review,
                laptop_brand: laptop.brand,
                laptop_model: laptop.model_name
            }));
            reviews.forEach(review => {
                if (review.rating && review.rating >= 1 && review.rating <= 5) {
                    ratingCounts[Math.floor(review.rating) - 1]++;
                }
            });
        }
        
        const chartTitle = document.getElementById('chart-title');
        const reviewsTitle = document.getElementById('reviews-title');
        if (chartTitle) chartTitle.textContent = `Rating Distribution - ${laptop.brand} ${laptop.model_name}`;
        if (reviewsTitle) reviewsTitle.textContent = `All Reviews - ${laptop.brand} ${laptop.model_name}`;
        
        allReviews.sort((a, b) => new Date(b.timestamp || b.date) - new Date(a.timestamp || a.date));
        const reviewsToShow = allReviews; // show all for selected laptop
        
        const reviewsContainer = document.getElementById('recent-reviews');
        
        if (reviewsToShow.length === 0) {
            reviewsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> No reviews available for ${laptop.brand} ${laptop.model_name}.
                </div>
            `;
        } else {
            reviewsContainer.innerHTML = reviewsToShow.map(review => {
                const rating = review.rating || 0;
                const author = review.author || 'Anonymous';
                const date = review.timestamp || review.date;
                const text = review.review_text || review.body || 'No review text';
                
                let formattedDate = 'Unknown date';
                if (date) {
                    try {
                        formattedDate = new Date(date).toLocaleDateString();
                    } catch (e) {
                        formattedDate = date.toString().substring(0, 10);
                    }
                }
                
                return `
                    <div class="review-item">
                        <div class="review-header">
                            <div>
                                <span class="review-rating">${'★'.repeat(Math.floor(rating))}${'☆'.repeat(5-Math.floor(rating))}</span>
                                <span class="review-author">${author}</span>
                            </div>
                            <span class="review-date">${formattedDate}</span>
                        </div>
                        <div class="review-text">${text}</div>
                    </div>
                `;
            }).join('');
        }
        
        if (ratingsChart) {
            const chartData = ratingCounts.reverse();
            ratingsChart.data.datasets[0].data = chartData;
            ratingsChart.update();
        }
        
    } catch (error) {
        console.error('[DEBUG] Error loading single laptop reviews:', error);
        const reviewsContainer = document.getElementById('recent-reviews');
        reviewsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Error loading reviews: ${error.message}
            </div>
        `;
    }
}

async function loadReviewsData() {
    console.log('[DEBUG] Loading reviews data from API...');
    
    try {
        // Load all laptops to get their reviews
        const laptopsData = await apiCall('/laptops');
        if (!laptopsData || laptopsData.length === 0) {
            console.log('[DEBUG] No laptops found for reviews');
            return;
        }
        
        // Collect all reviews from all laptops
        let allReviews = [];
        let ratingCounts = [0, 0, 0, 0, 0]; // 1-star, 2-star, 3-star, 4-star, 5-star
        
        for (const laptop of laptopsData) {
            try {
                console.log(`[DEBUG] Loading reviews for laptop ${laptop.id}: ${laptop.brand} ${laptop.model_name}`);
                const reviews = await apiCall(`/laptops/${laptop.id}/reviews`);
                console.log(`[DEBUG] Received ${reviews ? reviews.length : 0} reviews for laptop ${laptop.id}`);
                
                if (reviews && reviews.length > 0) {
                    // Add laptop info to each review
                    const reviewsWithLaptop = reviews.map(review => ({
                        ...review,
                        laptop_brand: laptop.brand,
                        laptop_model: laptop.model_name
                    }));
                    allReviews = allReviews.concat(reviewsWithLaptop);
                    
                    // Count ratings for chart
                    reviews.forEach(review => {
                        if (review.rating && review.rating >= 1 && review.rating <= 5) {
                            ratingCounts[Math.floor(review.rating) - 1]++;
                        }
                    });
                }
            } catch (error) {
                console.error(`[DEBUG] Error loading reviews for laptop ${laptop.id}:`, error);
            }
        }
        
        console.log('[DEBUG] Loaded', allReviews.length, 'total reviews');
        
        // Update chart title for "All Laptops"
        const chartTitle = document.getElementById('chart-title');
        const reviewsTitle = document.getElementById('reviews-title');
        if (chartTitle) chartTitle.textContent = 'Rating Distribution - All Laptops';
        if (reviewsTitle) reviewsTitle.textContent = 'All Reviews - All Laptops';
        
        // Sort by date (newest first) and take recent ones
        allReviews.sort((a, b) => new Date(b.timestamp || b.date) - new Date(a.timestamp || a.date));
        const reviewsToShow = allReviews; // Show all reviews by default
        
        // Display reviews
        const reviewsContainer = document.getElementById('recent-reviews');
        
        if (reviewsToShow.length === 0) {
            reviewsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> No reviews available yet.
                </div>
            `;
            
            // Show sample chart data when no reviews exist
            if (ratingsChart) {
                console.log('[DEBUG] No reviews found, showing sample chart data');
                ratingsChart.data.datasets[0].data = [2, 1, 1, 0, 0]; // Sample: 2 five-star, 1 four-star, 1 three-star
                ratingsChart.update();
            }
        } else {
            reviewsContainer.innerHTML = reviewsToShow.map(review => {
                const rating = review.rating || 0;
                const author = review.author || 'Anonymous';
                const date = review.timestamp || review.date;
                const text = review.review_text || review.body || 'No review text';
                const laptopInfo = review.laptop_brand && review.laptop_model ? 
                    `${review.laptop_brand} ${review.laptop_model}` : 'Unknown Laptop';
                
                // Format date
                let formattedDate = 'Unknown date';
                if (date) {
                    try {
                        formattedDate = new Date(date).toLocaleDateString();
                    } catch (e) {
                        formattedDate = date.toString().substring(0, 10);
                    }
                }
                
                return `
                    <div class="review-item">
                        <div class="review-header">
                            <div>
                                <span class="review-rating">${'★'.repeat(Math.floor(rating))}${'☆'.repeat(5-Math.floor(rating))}</span>
                                <span class="review-author">${author}</span>
                            </div>
                            <span class="review-date">${formattedDate}</span>
                        </div>
                        <div class="review-laptop"><small class="text-muted">${laptopInfo}</small></div>
                        <div class="review-text">${text}</div>
                    </div>
                `;
            }).join('');
        }
        
        // Update ratings chart with real data
        if (ratingsChart) {
            // Reverse array because chart expects [5-star, 4-star, 3-star, 2-star, 1-star]
            const chartData = ratingCounts.reverse();
            console.log('[DEBUG] Updating chart with rating counts:', ratingCounts, 'reversed to:', chartData);
            ratingsChart.data.datasets[0].data = chartData;
            ratingsChart.update();
            console.log('[DEBUG] Updated ratings chart with data:', chartData);
        } else {
            console.error('[DEBUG] ratingsChart is null - chart not initialized!');
        }
        
    } catch (error) {
        console.error('[DEBUG] Error loading reviews data:', error);
        const reviewsContainer = document.getElementById('recent-reviews');
        reviewsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Error loading reviews: ${error.message}
            </div>
        `;
    }
}

function ensureCompareSelector() {
    try {
        const compareTab = document.getElementById('compare-tab');
        if (!compareTab) return;
        let header = compareTab.querySelector('.compare-controls');
        if (!header) {
            header = document.createElement('div');
            header.className = 'compare-controls d-flex align-items-center mb-3';
            header.innerHTML = `
                <div class="me-2">
                    <label for="compareSelect" class="form-label mb-0 me-2">Select Laptop to Compare:</label>
                    <select id="compareSelect" class="form-select d-inline-block" style="width: 320px;"></select>
                </div>
                <button id="compareAddBtn" class="btn btn-outline-primary ms-2">
                    <i class="fas fa-plus"></i> Add to Comparison
                </button>
                <button id="compareClearBtn" class="btn btn-outline-secondary ms-2">
                    <i class="fas fa-trash"></i> Clear
                </button>
            `;
            compareTab.insertBefore(header, compareTab.firstChild);
        }
        // Populate options
        const select = header.querySelector('#compareSelect');
        if (select) {
            select.innerHTML = '';
            laptops.forEach(l => {
                const opt = document.createElement('option');
                opt.value = String(l.id);
                opt.textContent = `${l.brand} ${l.model_name}`;
                select.appendChild(opt);
            });
        }
        // Wire buttons
        const addBtn = header.querySelector('#compareAddBtn');
        if (addBtn && !addBtn._wired) {
            addBtn._wired = true;
            addBtn.addEventListener('click', () => {
                const sel = header.querySelector('#compareSelect');
                const id = sel ? parseInt(sel.value) : NaN;
                if (!isNaN(id)) {
                    addToCompare(id);
                }
            });
        }
        const clearBtn = header.querySelector('#compareClearBtn');
        if (clearBtn && !clearBtn._wired) {
            clearBtn._wired = true;
            clearBtn.addEventListener('click', () => {
                selectedLaptops = [];
                updateComparisonView();
            });
        }
    } catch (e) {
        console.error('[DEBUG] ensureCompareSelector error:', e);
    }
}

function ensureTrendsDropdown() {
    try {
        const trendsTab = document.getElementById('trends-tab');
        if (!trendsTab) return;
        let header = trendsTab.querySelector('.trends-controls');
        if (!header) {
            header = document.createElement('div');
            header.className = 'trends-controls d-flex align-items-center mb-3';
            header.innerHTML = `
                <div class="me-2">
                    <label for="trendsSelect" class="form-label mb-0 me-2">Select Laptop:</label>
                    <select id="trendsSelect" class="form-select d-inline-block" style="width: 320px;"></select>
                </div>
                <div id="trendsSeller" class="ms-3 text-muted small" style="min-width: 160px;"></div>
            `;
            trendsTab.insertBefore(header, trendsTab.firstChild);
        }
        // Populate options
        const select = header.querySelector('#trendsSelect');
        if (select) {
            select.innerHTML = '';
            laptops.forEach(l => {
                const opt = document.createElement('option');
                opt.value = String(l.id);
                opt.textContent = `${l.brand} ${l.model_name}`;
                select.appendChild(opt);
            });
            if (!select._wired) {
                select._wired = true;
                select.addEventListener('change', () => {
                    const id = parseInt(select.value);
                    loadPriceTrends(id);
                });
            }
        }
    } catch (e) {
        console.error('[DEBUG] ensureTrendsDropdown error:', e);
    }
}

// Utility Functions
function showLoading(show) {
    const loading = document.getElementById('loading');
    loading.style.display = show ? 'block' : 'none';
}

function showError(message) {
    // You could implement a toast notification system here
    console.error(message);
    alert(message); // Simple alert for now
}

function showSuccess(message) {
    // You could implement a toast notification system here
    console.log(message);
    // Simple success indication for now
}

// Export functions for global access
window.showLaptopDetails = showLaptopDetails;
window.addToCompare = addToCompare;
window.removeFromCompare = removeFromCompare;
window.applyFilters = applyFilters;
window.sendMessage = sendMessage;
window.handleChatKeyPress = handleChatKeyPress;
window.getRecommendations = getRecommendations;
window.quickRecommend = quickRecommend;
window.loadSelectedLaptopReviews = loadSelectedLaptopReviews;
