/**
 * Xavier AI Chatbot Widget - UI Module
 *
 * This module handles the UI components of the chatbot widget,
 * including HTML generation and style application.
 */

const XavierUI = (function() {
    /**
     * Load CSS styles for the widget
     * @param {Object} config - Widget configuration
     */
    function loadStyles(config) {
        console.log('Loading chatbot styles');

        // Create a link element for the external CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `${config.apiBase}static/css/chatbot-widget-redesign.css`;
        document.head.appendChild(link);

        // Create a style element for CSS variables
        const style = document.createElement('style');

        // Add CSS variables
        style.textContent = `/* Chatbot Widget Variables */
        :root {
            --theme-color: ${config.themeColor};
            --theme-color-dark: ${XavierUtils.adjustColor(config.themeColor, -20)};
        }`;

        // Add the style element to the document head
        document.head.appendChild(style);

        // Extract RGB values from hex color for pulse animation
        const rgb = XavierUtils.hexToRgb(config.themeColor);
        if (rgb) {
            document.documentElement.style.setProperty('--theme-color-rgb', `${rgb.r}, ${rgb.g}, ${rgb.b}`);
        }

        console.log('CSS styles applied successfully');
    }

    /**
     * Create the widget HTML structure
     * @param {Object} config - Widget configuration
     * @returns {HTMLElement} - Widget container element
     */
    function createWidgetHTML(config) {
        const widget = document.createElement('div');
        widget.innerHTML = `
            <div id="chatbot-widget" class="chatbot-container">
                <button id="chatbot-toggle" class="chatbot-toggle" aria-label="Toggle chat">
                    <span class="chatbot-notification-dot"></span>
                    <div class="chatbot-toggle-icon">
                        <!-- Headphones icon -->
                        <svg viewBox="0 0 24 24" width="36" height="36" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 1c-4.97 0-9 4.03-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h3c1.66 0 3-1.34 3-3v-7c0-4.97-4.03-9-9-9z"/>
                        </svg>
                    </div>
                    <!-- Chat bubble is created using CSS ::before and ::after pseudo-elements -->
                </button>

                <div id="chatbot-content" class="chatbot-content">
                    <div class="chatbot-header">
                        <div class="chatbot-header-info">
                            ${config.enableAvatar ? `<img src="${config.avatar}" class="chatbot-avatar" alt="${config.name}">` : ''}
                            <div class="chatbot-header-text">
                                <div style="font-weight: 600">${config.name}</div>
                                <div style="font-size: 14px;">
                                    <span class="chatbot-status-dot"></span>Online
                                </div>
                            </div>
                        </div>

                        <div class="chatbot-header-sentiment">
                            <button class="chatbot-sentiment-button chatbot-sentiment-positive"
                                    title="Helpful"
                                    aria-label="Mark as helpful">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                                </svg>
                            </button>
                            <button class="chatbot-sentiment-button chatbot-sentiment-negative"
                                    title="Not Helpful"
                                    aria-label="Mark as not helpful">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14h-4.764a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.737 3h4.017c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                                </svg>
                            </button>
                        </div>

                        <div class="chatbot-header-dropdown">
                            <button class="chatbot-header-actions-button" aria-label="Menu" id="chatbot-menu-button">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <circle cx="12" cy="12" r="2"></circle>
                                    <circle cx="12" cy="5" r="2"></circle>
                                    <circle cx="12" cy="19" r="2"></circle>
                                </svg>
                            </button>
                            <div class="chatbot-dropdown-menu" id="chatbot-dropdown-menu">
                                ${config.enableTickets ? `
                                <button class="chatbot-dropdown-item" id="chatbot-ticket-button">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                        <polyline points="14 2 14 8 20 8"></polyline>
                                        <line x1="16" y1="13" x2="8" y2="13"></line>
                                        <line x1="16" y1="17" x2="8" y2="17"></line>
                                        <polyline points="10 9 9 9 8 9"></polyline>
                                    </svg>
                                    <span>Create Support Ticket</span>
                                </button>
                                ` : ''}
                                <button class="chatbot-dropdown-item" id="chatbot-feedback-button">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                        <line x1="9" y1="10" x2="15" y2="10"></line>
                                        <line x1="9" y1="14" x2="15" y2="14"></line>
                                    </svg>
                                    <span>Provide Feedback</span>
                                </button>
                                ${config.enableLeads ? `
                                <button class="chatbot-dropdown-item" id="chatbot-lead-button">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                        <circle cx="9" cy="7" r="4"></circle>
                                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                                    </svg>
                                    <span>Request Information</span>
                                </button>
                                ` : ''}
                            </div>
                        </div>

                        <button class="chatbot-close-chat" aria-label="Close chat">×</button>
                    </div>

                    <div id="chatbot-messages" class="chatbot-messages">
                        <div class="chatbot-message bot">
                            Hi there! 👋 How can I help you today?
                        </div>
                    </div>

                    <div class="chatbot-input-container">
                        <div class="chatbot-input-wrapper">
                            <input type="text"
                                   id="chatbot-input"
                                   class="chatbot-input"
                                   placeholder="Type your message..."
                                   autocomplete="off">
                            <button id="chatbot-send" class="chatbot-send" disabled aria-label="Send message">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M22 2L11 13M22 2L15 22L11 13M11 13L2 9L22 2"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div class="powered-by">Powered by Xavier AI</div>

                    <!-- Lead Collection Form -->
                    <div id="chatbot-lead-form" class="chatbot-lead-form">
                        <h3>Interested in learning more?</h3>
                        <p class="lead-form-subtitle">Fill out this form and we'll get back to you soon.</p>
                        <div class="chatbot-form-group">
                            <label for="lead-name">Name *</label>
                            <input type="text" id="lead-name" required>
                        </div>
                        <div class="chatbot-form-group">
                            <label for="lead-email">Email *</label>
                            <input type="email" id="lead-email" required>
                        </div>
                        <div class="chatbot-form-group">
                            <label for="lead-phone">Phone</label>
                            <input type="tel" id="lead-phone">
                        </div>
                        <div class="chatbot-form-group">
                            <label for="lead-message">Message</label>
                            <textarea id="lead-message"></textarea>
                        </div>
                        <div class="chatbot-ticket-actions">
                            <button class="chatbot-ticket-submit">
                                <i class="fas fa-paper-plane"></i>
                                <span>Submit</span>
                            </button>
                            <button class="chatbot-ticket-cancel">Cancel</button>
                        </div>
                    </div>

                    <!-- Ticket Form -->
                    <div id="chatbot-ticket-form" class="chatbot-ticket-form">
                        <h3>Create Support Ticket</h3>
                        <p class="ticket-form-subtitle">It might take some time to get a response</p>
                        <div class="chatbot-form-group">
                            <label for="ticket-subject">Subject</label>
                            <input type="text" id="ticket-subject" required>
                        </div>
                        <div class="chatbot-form-group">
                            <label for="ticket-description">Description</label>
                            <textarea id="ticket-description" required></textarea>
                        </div>
                        <div class="chatbot-form-group">
                            <label for="ticket-priority">Priority</label>
                            <select id="ticket-priority">
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                            </select>
                        </div>
                        <div class="chatbot-form-group">
                            <label for="ticket-account">Contact Details</label>
                            <input type="text" id="ticket-account" required>
                        </div>
                        <div class="chatbot-ticket-actions">
                            <button class="chatbot-ticket-submit">
                                <i class="fas fa-paper-plane"></i>
                                <span>Submit Ticket</span>
                            </button>
                            <button class="chatbot-ticket-cancel">Cancel</button>
                        </div>
                    </div>
                </div>

                <!-- Feedback Modal -->
                <div id="chatbot-feedback" class="chatbot-feedback-modal">
                    <div class="chatbot-feedback-content">
                        <h3>Provide Feedback</h3>
                        <textarea id="chatbot-feedback-text"
                                 placeholder="Your feedback helps us improve..."></textarea>
                        <button class="chatbot-feedback-submit">
                            <i class="fas fa-paper-plane"></i>
                            <span>Submit</span>
                        </button>
                        <button class="chatbot-feedback-cancel">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        return widget;
    }

    /**
     * Show typing indicator in the chat
     */
    function showTypingIndicator() {
        const messages = document.getElementById('chatbot-messages');
        if (!messages) return;

        const typingIndicator = document.createElement('div');
        typingIndicator.id = 'typing-indicator';
        typingIndicator.className = 'chatbot-typing';
        typingIndicator.innerHTML = `
            <div class="chatbot-typing-dots">
                <div class="chatbot-typing-dot"></div>
                <div class="chatbot-typing-dot"></div>
                <div class="chatbot-typing-dot"></div>
            </div>
        `;

        messages.appendChild(typingIndicator);
        messages.scrollTop = messages.scrollHeight;

        return typingIndicator;
    }

    /**
     * Hide typing indicator
     * @param {HTMLElement} indicator - The typing indicator element
     */
    function hideTypingIndicator(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }

    /**
     * Add a message to the chat
     * @param {string} text - Message text
     * @param {string} sender - Message sender ('user' or 'bot')
     * @param {boolean} isHtml - Whether the message contains HTML
     */
    function addMessage(text, sender, isHtml = false) {
        const messages = document.getElementById('chatbot-messages');
        if (!messages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${sender}`;

        if (isHtml) {
            messageDiv.innerHTML = text;
        } else {
            messageDiv.textContent = text;
        }

        messages.appendChild(messageDiv);
        messages.scrollTop = messages.scrollHeight;

        return messageDiv;
    }

    return {
        loadStyles: loadStyles,
        createWidgetHTML: createWidgetHTML,
        showTypingIndicator: showTypingIndicator,
        hideTypingIndicator: hideTypingIndicator,
        addMessage: addMessage
    };
})();

// Export to global scope if in browser environment
if (typeof window !== 'undefined') {
    window.XavierUI = XavierUI;
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = XavierUI;
}
