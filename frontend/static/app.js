// Laptop Intelligence Engine - Frontend JavaScript

// Global variables
let laptops = [];
let selectedLaptops = [];
let conversationId = null;
let priceChart = null;
let ratingsChart = null;

// API base URL
const API_BASE = '/api/v1';

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
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabId}-tab`).classList.add('active');
    
    // Load tab-specific data
    loadTabData(tabId);
}

function loadTabData(tabId) {
    switch(tabId) {
        case 'trends':
            loadPriceTrends();
            break;
        case 'reviews':
            loadReviewsData();
            break;
        case 'compare':
            updateComparisonView();
            break;
    }
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
    showLoading(true);
    
    try {
        const data = await apiCall('/laptops');
        if (data) {
            laptops = data;
            displayLaptops(laptops);
        }
    } catch (error) {
        showError('Failed to load laptops');
    } finally {
        showLoading(false);
    }
}

function displayLaptops(laptopsData, viewMode = 'grid') {
    const container = document.getElementById('laptops-container');
    
    if (!laptopsData || laptopsData.length === 0) {
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
                            <th>Actions</th>
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
                <div class="card-footer">
                    <button class="btn btn-primary btn-sm w-100" onclick="event.stopPropagation(); addToCompare(${laptop.id})">
                        <i class="fas fa-balance-scale"></i> Compare
                    </button>
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
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="event.stopPropagation(); addToCompare(${laptop.id})">
                    <i class="fas fa-balance-scale"></i>
                </button>
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
    
    // Set up the "Add to Compare" button
    const addToCompareBtn = document.getElementById('addToCompareBtn');
    addToCompareBtn.onclick = () => {
        addToCompare(laptop.id);
        bootstrap.Modal.getInstance(modal).hide();
    };
    
    // Show the modal
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
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    input.value = '';
    
    // Show typing indicator
    addTypingIndicator();
    
    try {
        const response = await apiCall('/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });
        
        if (response) {
            conversationId = response.conversation_id;
            removeTypingIndicator();
            addMessageToChat(response.response, 'assistant');
        }
    } catch (error) {
        removeTypingIndicator();
        addMessageToChat('Sorry, I encountered an error. Please try again.', 'assistant');
    }
}

function addMessageToChat(message, sender) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const icon = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${icon} ${message}
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
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Average Price',
                data: [950, 920, 900, 880, 860, 850],
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
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Price ($)'
                    }
                }
            }
        }
    });
}

function initializeRatingsChart() {
    const ctx = document.getElementById('ratingsChart').getContext('2d');
    
    ratingsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['5 Stars', '4 Stars', '3 Stars', '2 Stars', '1 Star'],
            datasets: [{
                data: [45, 30, 15, 7, 3],
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
}

async function loadPriceTrends() {
    // In a real implementation, this would fetch actual price trend data
    // For now, we'll update with sample data
    if (priceChart) {
        priceChart.data.datasets[0].data = [950, 920, 900, 880, 860, 850];
        priceChart.update();
    }
}

async function loadReviewsData() {
    // Load recent reviews
    const reviewsContainer = document.getElementById('recent-reviews');
    
    // Sample reviews data
    const sampleReviews = [
        {
            rating: 5,
            author: 'John D.',
            date: '2024-01-15',
            text: 'Excellent laptop for business use. Fast, reliable, and great build quality.'
        },
        {
            rating: 4,
            author: 'Sarah M.',
            date: '2024-01-10',
            text: 'Good performance and battery life. The display could be brighter.'
        },
        {
            rating: 5,
            author: 'Mike R.',
            date: '2024-01-08',
            text: 'Perfect for development work. Handles multiple applications smoothly.'
        }
    ];
    
    reviewsContainer.innerHTML = sampleReviews.map(review => `
        <div class="review-item">
            <div class="review-header">
                <div>
                    <span class="review-rating">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</span>
                    <span class="review-author">${review.author}</span>
                </div>
                <span class="review-date">${new Date(review.date).toLocaleDateString()}</span>
            </div>
            <div class="review-text">${review.text}</div>
        </div>
    `).join('');
    
    // Update ratings chart
    if (ratingsChart) {
        ratingsChart.data.datasets[0].data = [45, 30, 15, 7, 3];
        ratingsChart.update();
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
