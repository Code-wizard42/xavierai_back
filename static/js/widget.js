(function() {
    // Get the script tag
    const scriptTag = document.currentScript;
    let apiBase = scriptTag.getAttribute('data-api');
    const chatbotId = scriptTag.getAttribute('data-id');

    // Ensure API base ends with a slash
    if (apiBase && !apiBase.endsWith('/')) {
        apiBase += '/';
    }

    // Log the API base for debugging
    console.log('API Base:', apiBase);
    console.log('Chatbot ID:', chatbotId);

    // Validate required attributes
    if (!apiBase) {
        console.error('Missing data-api attribute in script tag');
    }

    if (!chatbotId) {
        console.error('Missing data-id attribute in script tag');
    }

    // Build API URLs from base
    const urls = {
        ask: `${apiBase}chatbot/${chatbotId}/ask`,
        feedback: `${apiBase}chatbot/${chatbotId}/feedback`,
        sentiment: `${apiBase}analytics/sentiment/${chatbotId}`,
        ticket: `${apiBase}ticket/create/${chatbotId}`,
        submitLead: `${apiBase}api/leads/submit`,
        detectLeadIntent: `${apiBase}api/leads/detect-intent`
    };

    // Update the config object to include the new settings
    const config = {
        chatbotId: chatbotId,
        name: scriptTag.getAttribute('data-name') || 'Support Agent',
        askUrl: urls.ask,
        feedbackUrl: urls.feedback,
        ticketUrl: urls.ticket,
        avatar: scriptTag.getAttribute('data-avatar') || './assets/agent.png',
        themeColor: scriptTag.getAttribute('data-theme') || '#0066CC',
        sentimentUrl: urls.sentiment,
        submitLeadUrl: urls.submitLead,
        detectLeadIntentUrl: urls.detectLeadIntent,
        enableTickets: scriptTag.getAttribute('data-enable-tickets') !== 'false', // Default to true
        enableLeads: scriptTag.getAttribute('data-enable-leads') === 'true', // Default to false
        enableSmartLeadDetection: scriptTag.getAttribute('data-enable-smart-lead-detection') !== 'false', // Default to true
        leadDetectionThreshold: parseFloat(scriptTag.getAttribute('data-lead-detection-threshold') || '0.4'), // Default threshold
        enableAvatar: scriptTag.getAttribute('data-enable-avatar') !== 'false', // Default to true
        enableSentiment: scriptTag.getAttribute('data-enable-sentiment') !== 'false', // Default to true
        widgetRadius: parseInt(scriptTag.getAttribute('data-radius') || '45') // Default to 45px
    };

    // Load external CSS file for modern design
    function loadChatbotStyles() {
        console.log('Loading modern chatbot styles');

        // Create a link element for the external CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `${apiBase}static/css/chatbot-widget-redesign.css`;
        document.head.appendChild(link);

        // Also create a style element for CSS variables
        const style = document.createElement('style');

        // Add just the CSS variables
        style.textContent = `/* Chatbot Widget Variables */
:root {
    --theme-color: ${config.themeColor};
    --theme-color-dark: ${adjustColor(config.themeColor, -20)};
    --widget-radius: ${config.widgetRadius}px;
}`;

        // Add the style element to the document head
        document.head.appendChild(style);

        // Extract RGB values from hex color for pulse animation
        const hexToRgb = (hex) => {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? {
                r: parseInt(result[1], 16),
                g: parseInt(result[2], 16),
                b: parseInt(result[3], 16)
            } : null;
        };

        const rgb = hexToRgb(config.themeColor);
        if (rgb) {
            document.documentElement.style.setProperty('--theme-color-rgb', `${rgb.r}, ${rgb.g}, ${rgb.b}`);
        }

        console.log('CSS styles applied successfully');
    }

    // No fallback needed since CSS is loaded externally

    // Helper function to adjust color brightness
    function adjustColor(hex, amount) {
        let r = parseInt(hex.substring(1, 3), 16);
        let g = parseInt(hex.substring(3, 5), 16);
        let b = parseInt(hex.substring(5, 7), 16);

        r = Math.max(0, Math.min(255, r + amount));
        g = Math.max(0, Math.min(255, g + amount));
        b = Math.max(0, Math.min(255, b + amount));

        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    // Define the initializeWidget function
    function initializeWidget() {
        // Load the modern chatbot widget CSS
        const linkElement = document.createElement('link');
        linkElement.rel = 'stylesheet';
        linkElement.href = config.cssUrl || '/static/css/chatbot-widget-redesign.css';
        document.head.appendChild(linkElement);

        // Set theme color as CSS variable
        document.documentElement.style.setProperty('--theme-color', config.themeColor);

        // Set theme color dark variant for gradient effect
        const themeColorDark = adjustColor(config.themeColor, -30);
        document.documentElement.style.setProperty('--theme-color-dark', themeColorDark);

        // Set theme color RGB for animations
        const hexToRgb = (hex) => {
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return `${r}, ${g}, ${b}`;
        };
        document.documentElement.style.setProperty('--theme-color-rgb', hexToRgb(config.themeColor));

        console.log('CSS styles applied successfully');
    }

    // No fallback needed since CSS is embedded directly

    // Define the initializeWidget function
    function initializeWidget() {
        // Load the CSS
        loadChatbotStyles();

        // Create widget HTML
        const widget = document.createElement('div');
        widget.innerHTML = `
            <div id="chatbot-widget" class="chatbot-container">
                <button id="chatbot-toggle" class="chatbot-toggle" aria-label="Toggle chat">
                    <span class="chatbot-notification-dot"></span>
                    <div class="chatbot-toggle-icon">
                        <!-- Circular Message Bubble icon -->
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" />
                            <circle cx="12" cy="12" r="8" fill="white" opacity="0.2" />
                            <path d="M8 10h8M8 14h6" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                        </svg>
                    </div>
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

                        ${config.enableSentiment ? `
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
                        ` : ''}

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
        document.body.appendChild(widget);

        // Initialize widget functionality
        window.chatbotWidget = {
            userId: 'user_' + Math.random().toString(36).substring(2, 11),
            isTyping: false,
            ticketFormData: {},
            isCreatingTicket: false,
            currentTicketField: null,
            conversationId: null,
            messageCount: 0,
            leadSuggested: false,
            leadFormSubmitted: false, // Track if a lead form has been submitted
            lastLeadCheck: 0,
            ticketSuggestionTracking: null,

            // Show notification dot after a delay
            showNotificationDot() {
                setTimeout(() => {
                    const notificationDot = document.querySelector('.chatbot-notification-dot');
                    if (notificationDot) {
                        notificationDot.style.display = 'block';
                    }
                }, 5000); // Show after 5 seconds
            },

            // Helper function to adjust color brightness (kept for potential future use)
            adjustColor(color, amount) {
                const hex = color.replace('#', '');
                const r = Math.max(0, Math.min(255, parseInt(hex.substr(0, 2), 16) + amount));
                const g = Math.max(0, Math.min(255, parseInt(hex.substr(2, 2), 16) + amount));
                const b = Math.max(0, Math.min(255, parseInt(hex.substr(4, 2), 16) + amount));
                return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
            },

            // Escape HTML to prevent XSS
            escapeHtml(unsafe) {
                return unsafe
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            },

            // Format structured responses with proper HTML
            formatStructuredResponse(text) {
                if (!text) return '';
                
                let formatted = text;
                
                // STEP 1: Convert markdown headers to HTML
                formatted = formatted.replace(/^## (.+)$/gm, '<h3 class="structured-header">$1</h3>');
                formatted = formatted.replace(/^### (.+)$/gm, '<h4 class="structured-subheader">$1</h4>');
                
                // STEP 2: Handle bullet points with bold text (• **Text**: description)
                formatted = formatted.replace(/• \*\*([^*]+?)\*\*:\s*([^•\n]*)/g, '<li class="bullet-item"><strong>$1:</strong> $2</li>');
                
                // STEP 3: Handle simple bullet points (• Text)
                formatted = formatted.replace(/• ([^•\n]+)/g, '<li class="bullet-item">$1</li>');
                
                // STEP 4: Convert remaining bold text (**text**)
                formatted = formatted.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
                
                // STEP 5: REMOVE ALL REMAINING ASTERISKS
                formatted = formatted.replace(/\*/g, '');
                
                // STEP 6: Wrap consecutive list items in ul tags
                formatted = formatted.replace(/(<li class="bullet-item">[^<]*<\/li>\s*)+/gs, '<ul class="bullet-list">$&</ul>');
                
                // STEP 7: Convert line breaks
                formatted = formatted.replace(/\n/g, '<br>');
                
                // STEP 8: Clean up multiple spaces and breaks
                formatted = formatted.replace(/\s+/g, ' ');
                formatted = formatted.replace(/(<br\s*\/?>){2,}/g, '<br>');
                
                // STEP 9: Clean up spacing around HTML elements
                formatted = formatted.replace(/<br>\s*(<h[3-4]|<ul)/g, '$1');
                formatted = formatted.replace(/(<\/h[3-4]>|<\/ul>)\s*<br>/g, '$1');
                
                return formatted.trim();
            },

            // Toggle the chatbot visibility
            toggle() {
                const content = document.getElementById('chatbot-content');
                const toggle = document.getElementById('chatbot-toggle');
                const notificationDot = document.querySelector('.chatbot-notification-dot');

                content.classList.toggle('chatbot-visible');
                toggle.style.display = content.classList.contains('chatbot-visible') ? 'none' : 'flex';

                if (content.classList.contains('chatbot-visible')) {
                    document.getElementById('chatbot-input').focus();
                    // Hide notification dot when chat is opened
                    if (notificationDot) {
                        notificationDot.style.display = 'none';
                    }
                }
            },

            // Show typing indicator
            showTyping() {
                if (this.isTyping) return;

                this.isTyping = true;
                const messages = document.getElementById('chatbot-messages');
                messages.insertAdjacentHTML('beforeend', `
                    <div id="typing-indicator" class="chatbot-typing">
                        <div class="chatbot-typing-dots">
                            <div class="chatbot-typing-dot"></div>
                            <div class="chatbot-typing-dot"></div>
                            <div class="chatbot-typing-dot"></div>
                        </div>
                    </div>
                `);
                messages.scrollTop = messages.scrollHeight;
            },

            // Hide typing indicator
            hideTyping() {
                if (!this.isTyping) return;

                this.isTyping = false;
                const typingIndicator = document.getElementById('typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            },

            // Send a message
            async send() {
                const input = document.getElementById('chatbot-input');
                const messages = document.getElementById('chatbot-messages');
                const sendButton = document.getElementById('chatbot-send');
                const question = input.value.trim();

                if (!question) return;

                // If we're in ticket creation mode, handle the ticket input instead
                if (this.isCreatingTicket && this.currentTicketField) {
                    console.log("Handling ticket input for field:", this.currentTicketField);
                    this.handleTicketInput(this.currentTicketField);
                    return;
                }

                try {
                    input.disabled = true;
                    sendButton.disabled = true;

                    // Display user message
                    messages.innerHTML += `<div class="chatbot-message user">${this.escapeHtml(question)}</div>`;
                    input.value = '';
                    messages.scrollTop = messages.scrollHeight;

                    this.showTyping();

                    // Increment message count for lead detection
                    this.messageCount++;

                    const response = await fetch(config.askUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-ID': this.userId
                        },
                        body: JSON.stringify({
                            question,
                            conversation_id: this.conversationId
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }

                    const data = await response.json();

                    // Store the conversation ID for future use
                    if (data.conversation_id) {
                        this.conversationId = data.conversation_id;
                    }

                    this.hideTyping();
                    
                    // Backend sends markdown format, convert to HTML and remove all asterisks
                    let formattedAnswer = this.formatStructuredResponse(data.answer);
                    
                    // AGGRESSIVELY remove ALL asterisks 
                    formattedAnswer = formattedAnswer.replace(/\*/g, '');
                    
                    console.log('Original answer:', data.answer);
                    console.log('Final answer:', formattedAnswer);
                    messages.innerHTML += `<div class="chatbot-message bot">${formattedAnswer}</div>`;
                    messages.scrollTop = messages.scrollHeight;

                    // Check if the answer indicates the chatbot couldn't resolve the issue
                    const lowerCaseAnswer = data.answer.toLowerCase();
                    const lowerCaseQuestion = question.toLowerCase();

                    // Smart ticket suggestion with improved throttling
                    if (config.enableTickets) {
                        this.checkForTicketOpportunity(question, data.answer);
                    } else {
                        // Check for lead intent if we have enough messages and haven't suggested a lead form yet
                        if (this.messageCount >= 2 && !this.leadSuggested) {
                            this.checkForLeadIntent();
                        }
                    }
                } catch (error) {
                    console.error('Chatbot error:', error);
                    this.hideTyping();
                    messages.innerHTML += `
                        <div class="chatbot-message error">
                            Sorry, something went wrong. Please try again.
                        </div>
                    `;
                } finally {
                    input.disabled = false;
                    sendButton.disabled = false;
                    input.focus();
                    messages.scrollTop = messages.scrollHeight;
                }
            },

            // Submit sentiment feedback
            async submitSentiment(sentiment) {
                try {
                    const sentimentButtons = document.querySelectorAll('.chatbot-sentiment-button');

                    // Disable buttons
                    sentimentButtons.forEach(button => {
                        button.classList.add('disabled');
                    });

                    const response = await fetch(config.sentimentUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-ID': this.userId
                        },
                        body: JSON.stringify({
                            sentiment: sentiment,
                            conversation_id: this.currentConversationId
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to submit sentiment');
                    }

                    // Show temporary thank you message and re-enable after delay
                    setTimeout(() => {
                        sentimentButtons.forEach(button => {
                            button.classList.remove('disabled');
                        });
                    }, 3000);

                } catch (error) {
                    console.error('Sentiment submission error:', error);
                    // Re-enable buttons on error
                    sentimentButtons.forEach(button => {
                        button.classList.remove('disabled');
                    });
                }
            },

            // Open feedback modal
            openFeedback() {
                document.getElementById('chatbot-feedback').classList.add('chatbot-visible');
            },

            // Close feedback modal
            closeFeedback() {
                document.getElementById('chatbot-feedback').classList.remove('chatbot-visible');
                document.getElementById('chatbot-feedback-text').value = '';
            },

            // Submit feedback
            async submitFeedback() {
                const textarea = document.getElementById('chatbot-feedback-text');
                const feedback = textarea.value.trim();

                if (!feedback) {
                    alert('Please enter your feedback before submitting.');
                    return;
                }

                try {
                    await fetch(config.feedbackUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-ID': this.userId
                        },
                        body: JSON.stringify({ feedback })
                    });

                    alert('Thank you for your feedback!');
                    this.closeFeedback();
                } catch (error) {
                    console.error('Feedback error:', error);
                    alert('Sorry, we couldn\'t submit your feedback. Please try again.');
                }
            },

            // Open ticket form
            openTicketForm() {
                this.ticketFormData = {};
                this.isCreatingTicket = true;
                this.currentTicketField = 'subject';

                // Extract conversation context for smart pre-filling
                this.extractConversationContext();

                const input = document.getElementById('chatbot-input');
                if (!input) {
                    console.error('Input element not found');
                    return;
                }

                input.placeholder = "Type your response...";
                const sendButton = document.getElementById('chatbot-send');
                if (sendButton) {
                    sendButton.disabled = false;
                }

                // Show progress indicator for the ticket creation process
                this.displayMessage(`
                    <div class="ticket-creation-progress">
                        <div class="progress-step active">Subject</div>
                        <div class="progress-step">Description</div>
                        <div class="progress-step">Contact</div>
                        <div class="progress-step">Review</div>
                    </div>
                    <p>Let's create a ticket to help resolve your issue. First, please enter a subject for your ticket:</p>
                `, "bot", true);

                // If we have a suggested subject from context, offer it
                if (this.ticketFormData.suggestedSubject) {
                    setTimeout(() => {
                        this.displayMessage(`
                            <p>Based on our conversation, I suggest this subject:</p>
                            <div class="suggested-value">
                                "${this.ticketFormData.suggestedSubject}"
                            </div>
                            <div style="display: flex; gap: 10px; margin-top: 12px;">
                                <button class="use-suggestion-btn" style="background: var(--theme-color, #0066CC); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                    Use this subject
                                </button>
                                <button class="custom-input-btn" style="background: #f5f5f5; color: #555; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                    Enter my own
                                </button>
                            </div>
                        `, "bot", true);

                        // Add event listeners for the suggestion buttons
                        // Use the most recently added buttons by getting all buttons and taking the last ones
                        const allUseBtns = document.querySelectorAll('.use-suggestion-btn');
                        const allCustomBtns = document.querySelectorAll('.custom-input-btn');

                        // Get the most recently added buttons (last in the DOM)
                        const useBtn = allUseBtns[allUseBtns.length - 1];
                        const customBtn = allCustomBtns[allCustomBtns.length - 1];

                        console.log("Setting up subject suggestion buttons:", useBtn, customBtn);

                        if (useBtn && customBtn) {
                            // Remove any existing event listeners
                            const newUseBtn = useBtn.cloneNode(true);
                            const newCustomBtn = customBtn.cloneNode(true);

                            useBtn.parentNode.replaceChild(newUseBtn, useBtn);
                            customBtn.parentNode.replaceChild(newCustomBtn, customBtn);

                            // Add new event listeners
                            newUseBtn.addEventListener('click', () => {
                                console.log("Use subject button clicked");
                                this.handleSuggestedValue('subject', this.ticketFormData.suggestedSubject);
                            });

                            newCustomBtn.addEventListener('click', () => {
                                console.log("Custom subject button clicked");
                                // Set up for manual input
                                input.focus();
                                input.value = ''; // Clear any existing value

                                // Update the send button to handle this specific field
                                const sendBtn = document.getElementById('chatbot-send');
                                if (sendBtn) {
                                    // Create a one-time click handler for the send button
                                    const handleSendClick = () => {
                                        this.handleTicketInput('subject');
                                        // Remove this event listener after use
                                        sendBtn.removeEventListener('click', handleSendClick);
                                    };

                                    // Remove any existing click handlers and add our new one
                                    sendBtn.replaceWith(sendBtn.cloneNode(true));
                                    const newSendBtn = document.getElementById('chatbot-send');
                                    newSendBtn.addEventListener('click', handleSendClick);
                                    newSendBtn.disabled = false;
                                }

                                // Display a message to guide the user
                                this.displayMessage("Please type your subject and press Enter or click the send button.", "bot");
                            });
                        }
                    }, 500);
                }

                // Clear any existing event listeners
                const newInput = input.cloneNode(true);
                input.parentNode.replaceChild(newInput, input);

                // Re-add the input event listener
                newInput.addEventListener('input', () => {
                    const sendBtn = document.getElementById('chatbot-send');
                    if (sendBtn) {
                        sendBtn.disabled = !newInput.value.trim();
                    }
                });

                // Focus the input
                newInput.focus();
            },

            // Extract context from the conversation to pre-fill ticket fields
            extractConversationContext() {
                // Get all messages from the chat
                const messageElements = document.querySelectorAll('.chatbot-message');
                if (!messageElements || messageElements.length === 0) return;

                // Extract the last 10 exchanges (or fewer if not available)
                const recentMessages = [];
                const maxMessages = Math.min(10, messageElements.length);

                for (let i = messageElements.length - 1; i >= messageElements.length - maxMessages; i--) {
                    if (i < 0) break;
                    const element = messageElements[i];
                    const isUser = element.classList.contains('user');
                    const content = element.textContent.trim();

                    // Skip empty messages and ticket creation buttons/UI elements
                    if (content &&
                        !content.includes('Create ticket') &&
                        !content.includes('No, thanks') &&
                        !content.includes('Submit Ticket') &&
                        !content.includes('Cancel')) {

                        recentMessages.unshift({
                            type: isUser ? 'user' : 'bot',
                            content: content
                        });
                    }
                }

                // Identify user information from the conversation
                this.extractUserInfo(recentMessages);

                // Generate a suggested subject based on the conversation
                this.generateSuggestedSubject(recentMessages);

                // Create a formatted conversation context for the description
                // Add a header and timestamp
                const timestamp = new Date().toLocaleString();
                let contextHeader = `--- Conversation History (${timestamp}) ---\n\n`;

                // Format the conversation in a readable way
                this.ticketFormData.conversationContext = contextHeader + recentMessages
                    .map(msg => `${msg.type === 'user' ? '👤 Customer' : '🤖 Chatbot'}: ${msg.content}`)
                    .join('\n\n');
            },

            // Extract user information from conversation if available
            extractUserInfo(messages) {
                if (!messages || messages.length === 0) return;

                // Look for name patterns in user messages
                const namePatterns = [
                    /my name is ([a-zA-Z\s]+)/i,
                    /i am ([a-zA-Z\s]+)/i,
                    /this is ([a-zA-Z\s]+)/i,
                    /([a-zA-Z\s]+) here/i
                ];

                // Look for email patterns
                const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/;

                // Look for company/organization patterns
                const companyPatterns = [
                    /work for ([a-zA-Z0-9\s&]+)/i,
                    /with ([a-zA-Z0-9\s&]+)/i,
                    /at ([a-zA-Z0-9\s&]+)/i,
                    /from ([a-zA-Z0-9\s&]+)/i,
                    /([a-zA-Z0-9\s&]+) company/i
                ];

                // Check each user message
                for (const message of messages) {
                    if (message.type !== 'user') continue;

                    const content = message.content;

                    // Check for name
                    for (const pattern of namePatterns) {
                        const match = content.match(pattern);
                        if (match && match[1]) {
                            // Clean up the name (remove titles, etc.)
                            let name = match[1].trim();
                            name = name.replace(/^(mr|mrs|ms|dr|prof)\.?\s+/i, '');

                            // Store the name if it seems valid (not too long, not just one letter)
                            if (name.length > 1 && name.length < 40) {
                                this.ticketFormData.userName = name;
                            }
                        }
                    }

                    // Check for email
                    const emailMatch = content.match(emailPattern);
                    if (emailMatch) {
                        this.ticketFormData.userEmail = emailMatch[0];
                    }

                    // Check for company
                    for (const pattern of companyPatterns) {
                        const match = content.match(pattern);
                        if (match && match[1]) {
                            let company = match[1].trim();

                            // Store if it seems valid
                            if (company.length > 1 && company.length < 50) {
                                this.ticketFormData.userCompany = company;
                            }
                        }
                    }
                }
            },

            // Generate a suggested subject based on conversation context
            generateSuggestedSubject(messages) {
                if (!messages || messages.length === 0) return;

                // Extract all user messages
                const userMessages = messages.filter(msg => msg.type === 'user');
                if (userMessages.length === 0) return;

                // Ignore messages that are just about creating a ticket
                const ticketRequestPhrases = [
                    'create a ticket',
                    'support ticket',
                    'create ticket',
                    'open ticket',
                    'submit ticket',
                    'make a ticket',
                    'i need a ticket'
                ];

                // Get the most substantive user messages
                const substantiveMessages = userMessages.filter(msg => {
                    const content = msg.content.toLowerCase();
                    // Skip messages that are just about creating a ticket
                    return !ticketRequestPhrases.some(phrase => content.includes(phrase));
                });

                if (substantiveMessages.length === 0) {
                    // If no substantive messages, use a generic subject
                    this.ticketFormData.suggestedSubject = "Support Request";
                    return;
                }

                // Try to identify the main topic from the conversation
                const allText = substantiveMessages.map(msg => msg.content.toLowerCase()).join(' ');

                // Look for specific topics or issues in the conversation
                const topics = {
                    'Account Setup': ['setup', 'account', 'sign up', 'register', 'create account'],
                    'Integration Help': ['integrate', 'integration', 'connect', 'api', 'website', 'install'],
                    'Billing Question': ['billing', 'payment', 'charge', 'price', 'cost', 'subscription'],
                    'Technical Issue': ['error', 'problem', 'not working', 'bug', 'issue', 'broken'],
                    'Feature Request': ['feature', 'add', 'missing', 'would like', 'should have'],
                    'Product Information': ['how does', 'what is', 'information', 'details', 'learn more']
                };

                // Check if any topics match the conversation
                for (const [topic, keywords] of Object.entries(topics)) {
                    if (keywords.some(keyword => allText.includes(keyword))) {
                        this.ticketFormData.suggestedSubject = topic;
                        return;
                    }
                }

                // If no specific topic is found, create a subject from the most recent substantive message
                const recentMessage = substantiveMessages[substantiveMessages.length - 1].content;

                // Create a concise subject line
                const words = recentMessage.split(' ');
                if (words.length > 5) {
                    // For longer messages, take the first 5-7 words
                    this.ticketFormData.suggestedSubject = words.slice(0, Math.min(7, words.length)).join(' ');

                    // Add ellipsis if truncated
                    if (words.length > 7) {
                        this.ticketFormData.suggestedSubject += '...';
                    }
                } else {
                    // For short messages, use the whole message
                    this.ticketFormData.suggestedSubject = recentMessage;
                }

                // Ensure the subject isn't too long
                const maxLength = 60;
                if (this.ticketFormData.suggestedSubject.length > maxLength) {
                    this.ticketFormData.suggestedSubject =
                        this.ticketFormData.suggestedSubject.substring(0, maxLength) + '...';
                }
            },

            // Handle when user selects a suggested value
            handleSuggestedValue(field, value) {
                this.ticketFormData[field] = value;

                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'chatbot-message bot';
                fieldDiv.innerHTML = `
                    <div class="chatbot-form-field completed">
                        <label>${this.getFieldLabel(field)}</label>
                        <div style="display: flex; align-items: center;">
                            <span>${this.escapeHtml(value)}</span>
                            <span class="chatbot-check-mark">✓</span>
                        </div>
                    </div>
                `;

                const messages = document.getElementById('chatbot-messages');
                messages.appendChild(fieldDiv);
                messages.scrollTop = messages.scrollHeight;

                // Move to the next field
                switch (field) {
                    case 'subject':
                        this.currentTicketField = 'description';
                        this.displayNextTicketStep('description');
                        break;

                    case 'description':
                        this.currentTicketField = 'account';
                        this.displayNextTicketStep('account');
                        break;

                    case 'account':
                        this.currentTicketField = null;
                        this.isCreatingTicket = false;
                        this.ticketFormData.priority = 'medium';
                        this.displayTicketSummary();
                        break;
                }
            },

            // Display the next step in the ticket creation process with progress indicator
            displayNextTicketStep(field) {
                // Update progress indicator
                const progressSteps = document.querySelectorAll('.progress-step');
                if (progressSteps.length > 0) {
                    // Remove active class from all steps
                    progressSteps.forEach(step => step.classList.remove('active'));

                    // Add active class to current step
                    let stepIndex = 0;
                    switch (field) {
                        case 'subject': stepIndex = 0; break;
                        case 'description': stepIndex = 1; break;
                        case 'account': stepIndex = 2; break;
                        default: stepIndex = 3; break;
                    }

                    if (progressSteps[stepIndex]) {
                        progressSteps[stepIndex].classList.add('active');
                    }
                }

                // Display appropriate message for the current field
                switch (field) {
                    case 'description':
                        this.displayMessage("Great! Now please provide a detailed description of the issue:", "bot");

                        // If we have conversation context, offer it as a suggestion
                        if (this.ticketFormData.conversationContext) {
                            setTimeout(() => {
                                const suggestedDescription = "I'm having the issue described in our conversation:\n\n" +
                                    this.ticketFormData.conversationContext;

                                this.displayMessage(`
                                    <p>I can include our conversation as part of the description:</p>
                                    <div class="suggested-value" style="max-height: 100px; overflow-y: auto; font-size: 12px; background: #f5f5f5; padding: 8px; border-radius: 4px; margin: 8px 0;">
                                        ${this.escapeHtml(suggestedDescription).replace(/\n/g, '<br>')}
                                    </div>
                                    <div style="display: flex; gap: 10px; margin-top: 12px;">
                                        <button class="use-suggestion-btn" style="background: var(--theme-color, #0066CC); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                            Use this description
                                        </button>
                                        <button class="custom-input-btn" style="background: #f5f5f5; color: #555; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                            Enter my own
                                        </button>
                                    </div>
                                `, "bot", true);

                                // Add event listeners for the suggestion buttons
                                // Use the most recently added buttons by getting all buttons and taking the last ones
                                const allUseBtns = document.querySelectorAll('.use-suggestion-btn');
                                const allCustomBtns = document.querySelectorAll('.custom-input-btn');

                                // Get the most recently added buttons (last in the DOM)
                                const useBtn = allUseBtns[allUseBtns.length - 1];
                                const customBtn = allCustomBtns[allCustomBtns.length - 1];

                                console.log("Setting up description suggestion buttons:", useBtn, customBtn);

                                if (useBtn && customBtn) {
                                    // Remove any existing event listeners
                                    const newUseBtn = useBtn.cloneNode(true);
                                    const newCustomBtn = customBtn.cloneNode(true);

                                    useBtn.parentNode.replaceChild(newUseBtn, useBtn);
                                    customBtn.parentNode.replaceChild(newCustomBtn, customBtn);

                                    // Add new event listeners
                                    newUseBtn.addEventListener('click', () => {
                                        console.log("Use description button clicked");
                                        this.handleSuggestedValue('description', suggestedDescription);
                                    });

                                    newCustomBtn.addEventListener('click', () => {
                                        console.log("Custom description button clicked");
                                        // Set up for manual input
                                        const input = document.getElementById('chatbot-input');
                                        input.focus();
                                        input.value = ''; // Clear any existing value

                                        // Update the send button to handle this specific field
                                        const sendBtn = document.getElementById('chatbot-send');
                                        if (sendBtn) {
                                            // Create a one-time click handler for the send button
                                            const handleSendClick = () => {
                                                this.handleTicketInput('description');
                                                // Remove this event listener after use
                                                sendBtn.removeEventListener('click', handleSendClick);
                                            };

                                            // Remove any existing click handlers and add our new one
                                            sendBtn.replaceWith(sendBtn.cloneNode(true));
                                            const newSendBtn = document.getElementById('chatbot-send');
                                            newSendBtn.addEventListener('click', handleSendClick);
                                            newSendBtn.disabled = false;
                                        }

                                        // Display a message to guide the user
                                        this.displayMessage("Please type your description and press Enter or click the send button.", "bot");
                                    });
                                }
                            }, 500);
                        }
                        break;

                    case 'account':
                        this.displayMessage("Finally, please provide your contact details (email or phone):", "bot");

                        // If we have extracted user info, offer it as a suggestion
                        if (this.ticketFormData.userName || this.ticketFormData.userEmail) {
                            setTimeout(() => {
                                let contactInfo = '';

                                if (this.ticketFormData.userName) {
                                    contactInfo += this.ticketFormData.userName;
                                }

                                if (this.ticketFormData.userEmail) {
                                    if (contactInfo) contactInfo += ' - ';
                                    contactInfo += this.ticketFormData.userEmail;
                                }

                                if (this.ticketFormData.userCompany) {
                                    if (contactInfo) contactInfo += ' - ';
                                    contactInfo += this.ticketFormData.userCompany;
                                }

                                if (contactInfo) {
                                    this.displayMessage(`
                                        <p>I found your contact information in our conversation:</p>
                                        <div class="suggested-value">
                                            "${this.escapeHtml(contactInfo)}"
                                        </div>
                                        <div style="display: flex; gap: 10px; margin-top: 12px;">
                                            <button class="use-suggestion-btn" style="background: var(--theme-color, #0066CC); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                                Use this information
                                            </button>
                                            <button class="custom-input-btn" style="background: #f5f5f5; color: #555; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                                Enter my own
                                            </button>
                                        </div>
                                    `, "bot", true);

                                    // Add event listeners for the suggestion buttons
                                    // Use the most recently added buttons by getting all buttons and taking the last ones
                                    const allUseBtns = document.querySelectorAll('.use-suggestion-btn');
                                    const allCustomBtns = document.querySelectorAll('.custom-input-btn');

                                    // Get the most recently added buttons (last in the DOM)
                                    const useBtn = allUseBtns[allUseBtns.length - 1];
                                    const customBtn = allCustomBtns[allCustomBtns.length - 1];

                                    console.log("Setting up contact details suggestion buttons:", useBtn, customBtn);

                                    if (useBtn && customBtn) {
                                        // Remove any existing event listeners
                                        const newUseBtn = useBtn.cloneNode(true);
                                        const newCustomBtn = customBtn.cloneNode(true);

                                        useBtn.parentNode.replaceChild(newUseBtn, useBtn);
                                        customBtn.parentNode.replaceChild(newCustomBtn, customBtn);

                                        // Add new event listeners
                                        newUseBtn.addEventListener('click', () => {
                                            console.log("Use contact details button clicked");
                                            this.handleSuggestedValue('account', contactInfo);
                                        });

                                        newCustomBtn.addEventListener('click', () => {
                                            console.log("Custom contact details button clicked");
                                            // Set up for manual input
                                            const input = document.getElementById('chatbot-input');
                                            input.focus();
                                            input.value = ''; // Clear any existing value

                                            // Update the send button to handle this specific field
                                            const sendBtn = document.getElementById('chatbot-send');
                                            if (sendBtn) {
                                                // Create a one-time click handler for the send button
                                                const handleSendClick = () => {
                                                    this.handleTicketInput('account');
                                                    // Remove this event listener after use
                                                    sendBtn.removeEventListener('click', handleSendClick);
                                                };

                                                // Remove any existing click handlers and add our new one
                                                sendBtn.replaceWith(sendBtn.cloneNode(true));
                                                const newSendBtn = document.getElementById('chatbot-send');
                                                newSendBtn.addEventListener('click', handleSendClick);
                                                newSendBtn.disabled = false;
                                            }

                                            // Display a message to guide the user
                                            this.displayMessage("Please type your contact details and press Enter or click the send button.", "bot");
                                        });
                                    }
                                }
                            }, 500);
                        }
                        break;
                }
            },

            // Handle ticket input
            handleTicketInput(field) {
                console.log("Handling ticket input for field:", field);
                const input = document.getElementById('chatbot-input');
                const value = input.value.trim();

                if (!value) {
                    this.displayMessage("This field cannot be empty. Please try again.", "error");
                    return;
                }

                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'chatbot-message bot';
                fieldDiv.innerHTML = `
                    <div class="chatbot-form-field completed">
                        <label>${this.getFieldLabel(field)}</label>
                        <div style="display: flex; align-items: center;">
                            <span>${this.escapeHtml(value)}</span>
                            <span class="chatbot-check-mark">✓</span>
                        </div>
                    </div>
                `;

                const messages = document.getElementById('chatbot-messages');
                messages.appendChild(fieldDiv);
                messages.scrollTop = messages.scrollHeight;

                input.value = '';
                this.ticketFormData[field] = value;

                // Reset the send button to its default state
                const sendButton = document.getElementById('chatbot-send');
                if (sendButton) {
                    sendButton.replaceWith(sendButton.cloneNode(true));
                    const newSendButton = document.getElementById('chatbot-send');
                    newSendButton.addEventListener('click', () => window.chatbotWidget.send());
                    newSendButton.disabled = true;
                }

                switch (field) {
                    case 'subject':
                        this.currentTicketField = 'description';
                        this.displayNextTicketStep('description');
                        break;

                    case 'description':
                        this.currentTicketField = 'account';
                        this.displayNextTicketStep('account');
                        break;

                    case 'account':
                        this.currentTicketField = null;
                        this.isCreatingTicket = false;
                        this.ticketFormData.priority = 'medium';

                        // Update progress indicator for review step
                        const progressSteps = document.querySelectorAll('.progress-step');
                        if (progressSteps.length > 0) {
                            progressSteps.forEach(step => step.classList.remove('active'));
                            if (progressSteps[3]) {
                                progressSteps[3].classList.add('active');
                            }
                        }

                        this.displayTicketSummary();
                        break;
                }

                // Focus the input after processing
                input.focus();
            },

            // Get field label
            getFieldLabel(field) {
                const labels = {
                    subject: 'Subject',
                    description: 'Description',
                    priority: 'Priority Level',
                    account: 'Account Details'
                };
                return labels[field] || field;
            },

            // Display ticket summary
            displayTicketSummary() {
                this.displayMessage("Perfect! Here's a summary of your ticket:", "bot");

                // Create a summary of the ticket information
                const summaryDiv = document.createElement('div');
                summaryDiv.className = 'chatbot-message bot';
                summaryDiv.innerHTML = `
                    <div class="ticket-summary">
                        <div class="ticket-summary-field">
                            <strong>Subject:</strong> ${this.escapeHtml(this.ticketFormData.subject)}
                        </div>
                        <div class="ticket-summary-field">
                            <strong>Description:</strong>
                            <div class="ticket-description-preview">
                                ${this.escapeHtml(this.ticketFormData.description).substring(0, 150)}${this.ticketFormData.description.length > 150 ? '...' : ''}
                            </div>
                        </div>
                        <div class="ticket-summary-field">
                            <strong>Contact:</strong> ${this.escapeHtml(this.ticketFormData.account)}
                        </div>
                        <div class="ticket-summary-field">
                            <strong>Priority:</strong> Medium
                        </div>
                    </div>
                `;

                const messages = document.getElementById('chatbot-messages');
                messages.appendChild(summaryDiv);

                // Add action buttons
                const buttonDiv = document.createElement('div');
                buttonDiv.className = 'chatbot-message bot';
                buttonDiv.style.display = 'flex';
                buttonDiv.style.gap = '10px';
                buttonDiv.innerHTML = `
                    <button class="chatbot-ticket-submit" style="display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 14px; padding: 8px 14px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                        <i class="fas fa-paper-plane" style="font-size: 12px;"></i>
                        <span>Submit Ticket</span>
                    </button>
                    <button class="chatbot-ticket-cancel" style="font-size: 14px; padding: 8px 14px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                        Cancel
                    </button>
                `;

                // Add event listeners
                const submitButton = buttonDiv.querySelector('.chatbot-ticket-submit');
                const cancelButton = buttonDiv.querySelector('.chatbot-ticket-cancel');

                submitButton.addEventListener('click', () => this.submitTicketForm());
                cancelButton.addEventListener('click', () => this.cancelTicketForm());

                messages.appendChild(buttonDiv);
                messages.scrollTop = messages.scrollHeight;
            },

            // Submit ticket form
            async submitTicketForm() {
                // Show loading state and store a reference to the loading message element
                const loadingMessageElement = document.createElement('div');
                loadingMessageElement.className = 'chatbot-message bot';
                loadingMessageElement.innerHTML = `
                    <div class="ticket-submission-loading">
                        <div class="loading-spinner"></div>
                        <p>Submitting your ticket...</p>
                    </div>
                `;

                const messages = document.getElementById('chatbot-messages');
                messages.appendChild(loadingMessageElement);
                messages.scrollTop = messages.scrollHeight;

                try {
                    const response = await fetch(config.ticketUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-ID': this.userId
                        },
                        body: JSON.stringify({
                            subject: this.ticketFormData.subject,
                            description: this.ticketFormData.description,
                            priority: 'medium',
                            account_details: this.ticketFormData.account
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to create ticket');
                    }

                    const data = await response.json();

                    // Remove the loading message
                    if (loadingMessageElement && loadingMessageElement.parentNode) {
                        loadingMessageElement.parentNode.removeChild(loadingMessageElement);
                    }

                    // Success message with ticket ID and next steps
                    this.displayMessage(`
                        <div class="ticket-success">
                            <div class="ticket-success-icon">
                                <i class="fas fa-check-circle" style="color: #10B981; font-size: 24px;"></i>
                            </div>
                            <div class="ticket-success-message">
                                <p><strong>Ticket #${data.ticket_id} created successfully!</strong></p>
                                <p>Our support team will review your ticket and get back to you as soon as possible.</p>
                                <p class="ticket-response-time">Typical response time: 24-48 hours</p>
                            </div>
                        </div>
                    `, "bot", true);

                    // Add follow-up message after a short delay
                    setTimeout(() => {
                        this.displayMessage("Is there anything else I can help you with today?", "bot");
                    }, 1500);

                    this.resetTicketForm();
                } catch (error) {
                    console.error('Ticket creation error:', error);

                    // Remove the loading message even if there's an error
                    if (loadingMessageElement && loadingMessageElement.parentNode) {
                        loadingMessageElement.parentNode.removeChild(loadingMessageElement);
                    }

                    this.displayMessage(`
                        <div class="ticket-error">
                            <div class="ticket-error-icon">
                                <i class="fas fa-exclamation-circle" style="color: #EF4444; font-size: 24px;"></i>
                            </div>
                            <div class="ticket-error-message">
                                <p><strong>Sorry, we couldn't create your ticket.</strong></p>
                                <p>Please try again or contact support directly at support@example.com</p>
                            </div>
                        </div>
                    `, "bot", true);
                }
            },

            // Cancel ticket form
            cancelTicketForm() {
                this.displayMessage("Ticket creation cancelled.", "bot");
                this.resetTicketForm();
            },

            // Reset ticket form
            resetTicketForm() {
                const input = document.getElementById('chatbot-input');
                input.placeholder = "Type your message...";
                this.ticketFormData = {};
                this.isCreatingTicket = false;
                this.currentTicketField = null;
                input.value = '';

                // Clear any existing event listeners
                const newInput = input.cloneNode(true);
                input.parentNode.replaceChild(newInput, input);

                // Re-add the input event listener
                newInput.addEventListener('input', () => {
                    const sendBtn = document.getElementById('chatbot-send');
                    if (sendBtn) {
                        sendBtn.disabled = !newInput.value.trim();
                    }
                });

                // Re-add the keypress event listener for Enter
                newInput.addEventListener('keypress', (event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        window.chatbotWidget.send();
                    }
                });

                // Reset the send button to its default state
                const sendButton = document.getElementById('chatbot-send');
                if (sendButton) {
                    sendButton.replaceWith(sendButton.cloneNode(true));
                    const newSendButton = document.getElementById('chatbot-send');
                    newSendButton.addEventListener('click', () => window.chatbotWidget.send());
                    newSendButton.disabled = true;
                }

                // Focus the input
                newInput.focus();

                console.log("Ticket form reset completed");
            },

            // Open lead form with smart pre-filling
            openLeadForm() {
                const leadForm = document.getElementById('chatbot-lead-form');
                leadForm.classList.add('chatbot-visible');

                // Pre-fill message field if we have detected product interest
                if (this.leadProductInterest) {
                    const messageField = document.getElementById('lead-message');
                    if (messageField) {
                        messageField.value = `I'm interested in learning more about your ${this.leadProductInterest}.`;
                    }
                }

                // Add a subtle animation to highlight the form
                leadForm.style.animation = 'formSlideIn 0.4s ease-out forwards';

                // Focus on the first empty required field
                setTimeout(() => {
                    const nameField = document.getElementById('lead-name');
                    if (nameField && !nameField.value) {
                        nameField.focus();
                    } else {
                        const emailField = document.getElementById('lead-email');
                        if (emailField && !emailField.value) {
                            emailField.focus();
                        }
                    }
                }, 300);
            },

            // Close lead form
            closeLeadForm() {
                const leadForm = document.getElementById('chatbot-lead-form');
                leadForm.classList.remove('chatbot-visible');

                // Reset form fields
                document.getElementById('lead-name').value = '';
                document.getElementById('lead-email').value = '';
                document.getElementById('lead-phone').value = '';
                document.getElementById('lead-message').value = '';

                // Clear any stored product interest
                this.leadProductInterest = null;

                // Note: We don't reset leadFormSubmitted here because we want to keep track
                // of whether a form was successfully submitted during this session
            },

            // Submit lead form with improved feedback
            async submitLeadForm() {
                const name = document.getElementById('lead-name').value.trim();
                const email = document.getElementById('lead-email').value.trim();
                const phone = document.getElementById('lead-phone').value.trim();
                const message = document.getElementById('lead-message').value.trim();

                // Validate required fields with inline feedback
                if (!name || !email) {
                    // Highlight missing fields
                    if (!name) {
                        const nameField = document.getElementById('lead-name');
                        nameField.style.border = '1px solid #EF4444';
                        nameField.style.boxShadow = '0 0 0 2px rgba(239, 68, 68, 0.2)';
                        nameField.focus();
                    }

                    if (!email) {
                        const emailField = document.getElementById('lead-email');
                        emailField.style.border = '1px solid #EF4444';
                        emailField.style.boxShadow = '0 0 0 2px rgba(239, 68, 68, 0.2)';
                        if (name) emailField.focus();
                    }

                    // Add validation message
                    const validationMsg = document.createElement('div');
                    validationMsg.className = 'lead-validation-error';
                    validationMsg.innerHTML = 'Please fill in all required fields (Name and Email)';
                    validationMsg.style.color = '#EF4444';
                    validationMsg.style.fontSize = '13px';
                    validationMsg.style.marginTop = '8px';

                    const actionsDiv = document.querySelector('.chatbot-ticket-actions');
                    if (actionsDiv) {
                        actionsDiv.parentNode.insertBefore(validationMsg, actionsDiv);

                        // Remove the message after 3 seconds
                        setTimeout(() => {
                            validationMsg.remove();

                            // Reset field styling
                            if (!name) document.getElementById('lead-name').style.border = '';
                            if (!email) document.getElementById('lead-email').style.border = '';
                            if (!name) document.getElementById('lead-name').style.boxShadow = '';
                            if (!email) document.getElementById('lead-email').style.boxShadow = '';
                        }, 3000);
                    }

                    return;
                }

                // Validate email format with inline feedback
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(email)) {
                    const emailField = document.getElementById('lead-email');
                    emailField.style.border = '1px solid #EF4444';
                    emailField.style.boxShadow = '0 0 0 2px rgba(239, 68, 68, 0.2)';
                    emailField.focus();

                    // Add validation message
                    const validationMsg = document.createElement('div');
                    validationMsg.className = 'lead-validation-error';
                    validationMsg.innerHTML = 'Please enter a valid email address';
                    validationMsg.style.color = '#EF4444';
                    validationMsg.style.fontSize = '13px';
                    validationMsg.style.marginTop = '8px';

                    const actionsDiv = document.querySelector('.chatbot-ticket-actions');
                    if (actionsDiv) {
                        actionsDiv.parentNode.insertBefore(validationMsg, actionsDiv);

                        // Remove the message after 3 seconds
                        setTimeout(() => {
                            validationMsg.remove();
                            emailField.style.border = '';
                            emailField.style.boxShadow = '';
                        }, 3000);
                    }

                    return;
                }

                // Show loading state
                const submitButton = document.querySelector('.chatbot-lead-form .chatbot-ticket-submit');
                const cancelButton = document.querySelector('.chatbot-lead-form .chatbot-ticket-cancel');

                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<div class="loading-spinner" style="width: 16px; height: 16px;"></div><span>Submitting...</span>';
                }

                if (cancelButton) {
                    cancelButton.disabled = true;
                }

                try {
                    const response = await fetch(config.submitLeadUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            name: name,
                            email: email,
                            phone: phone || null,
                            message: message || null,
                            chatbot_id: config.chatbotId,
                            product_interest: this.leadProductInterest || null
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to submit lead');
                    }

                    this.closeLeadForm();

                    // Mark the lead form as submitted
                    this.leadFormSubmitted = true;

                    // Display success message with personalized follow-up
                    this.displayMessage(`
                        <div class="lead-success">
                            <div class="lead-success-icon">
                                <i class="fas fa-check-circle" style="color: #10B981; font-size: 24px;"></i>
                            </div>
                            <div class="lead-success-message">
                                <p><strong>Thank you, ${name.split(' ')[0]}!</strong></p>
                                <p>We've received your information and will contact you soon${this.leadProductInterest ? ` with details about our ${this.leadProductInterest}` : ''}.</p>
                                <p class="lead-response-time">You should hear from us within 1-2 business days.</p>
                            </div>
                        </div>
                    `, 'bot', true);

                    // Add follow-up message after a short delay
                    setTimeout(() => {
                        this.displayMessage("Is there anything else I can help you with today?", "bot");
                    }, 1500);

                } catch (error) {
                    console.error('Lead submission error:', error);

                    // Reset button state
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = '<i class="fas fa-paper-plane"></i><span>Submit</span>';
                    }

                    if (cancelButton) {
                        cancelButton.disabled = false;
                    }

                    // Display error message in the form
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'lead-submission-error';
                    errorMsg.innerHTML = 'Sorry, we couldn\'t submit your information. Please try again.';
                    errorMsg.style.color = '#EF4444';
                    errorMsg.style.fontSize = '13px';
                    errorMsg.style.marginTop = '8px';
                    errorMsg.style.marginBottom = '8px';

                    const actionsDiv = document.querySelector('.chatbot-ticket-actions');
                    if (actionsDiv) {
                        actionsDiv.parentNode.insertBefore(errorMsg, actionsDiv);

                        // Remove the message after 5 seconds
                        setTimeout(() => {
                            errorMsg.remove();
                        }, 5000);
                    }
                }
            },

            // Check if we should analyze the conversation for lead intent
            async checkForLeadIntent() {
                // Skip if leads are disabled, lead detection is disabled, already suggested in this session,
                // or a lead form has already been submitted
                if (!config.enableLeads || !config.enableSmartLeadDetection || this.leadSuggested || this.leadFormSubmitted) {
                    return;
                }

                // Make sure the lead button is visible if leads are enabled
                const leadButton = document.getElementById('chatbot-lead-button');
                if (leadButton && config.enableLeads) {
                    leadButton.style.display = 'flex';
                }

                // Skip if we don't have enough messages yet (reduced to 2 for testing)
                if (this.messageCount < 2) {
                    return;
                }

                // Skip if we checked recently (avoid checking too frequently)
                const now = Date.now();
                if (now - this.lastLeadCheck < 60000) { // Check at most once per minute
                    return;
                }

                this.lastLeadCheck = now;

                // Skip if we don't have a conversation ID
                if (!this.conversationId) {
                    return;
                }

                try {
                    const response = await fetch(config.detectLeadIntentUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-ID': this.userId
                        },
                        body: JSON.stringify({
                            conversation_id: this.conversationId,
                            chatbot_id: config.chatbotId
                        })
                    });

                    if (!response.ok) {
                        console.error('Lead intent detection failed:', response.status);
                        return;
                    }

                    const data = await response.json();
                    console.log('Lead intent detection result:', data);

                    // If the threshold is met, suggest lead form
                    if (data.suggest_lead && data.threshold_met) {
                        // Wait a moment before suggesting
                        setTimeout(() => {
                            this.suggestLeadForm();
                        }, 1000);
                    }
                } catch (error) {
                    console.error('Error detecting lead intent:', error);
                }
            },

            // Suggest the lead form to the user with context-aware messaging
            suggestLeadForm() {
                // Skip if leads are disabled
                if (!config.enableLeads) {
                    return;
                }

                // Skip if a lead form has already been submitted in this session
                if (this.leadFormSubmitted) {
                    console.log('Lead form already submitted in this session, skipping suggestion');
                    return;
                }

                // Mark as suggested so we don't suggest again in this session
                this.leadSuggested = true;

                // Get conversation context to personalize the lead suggestion
                const messageElements = document.querySelectorAll('.chatbot-message');
                let recentUserMessages = [];

                // Extract recent user messages for context
                if (messageElements && messageElements.length > 0) {
                    for (let i = messageElements.length - 1; i >= Math.max(0, messageElements.length - 6); i--) {
                        const element = messageElements[i];
                        if (element.classList.contains('user')) {
                            recentUserMessages.push(element.textContent.trim());
                        }
                    }
                }

                // Determine the type of lead suggestion based on conversation context
                let leadMessage = "Would you like to provide your contact information so we can send you more details about our products and services?";
                let leadButtonText = "I'm interested";

                // Check for specific interests in the conversation
                const productInterest = this.detectProductInterest(recentUserMessages.join(' ').toLowerCase());
                if (productInterest) {
                    leadMessage = `Would you like to receive more information about our ${productInterest}? We can send details directly to your inbox.`;
                    leadButtonText = `Yes, send ${productInterest} info`;
                }

                const messages = document.getElementById('chatbot-messages');

                // Create a message with buttons
                const messageDiv = document.createElement('div');
                messageDiv.className = 'chatbot-message bot lead-suggestion';
                messageDiv.innerHTML = `
                    <p>${leadMessage}</p>
                    <div style="display: flex; gap: 10px; margin-top: 12px;">
                        <button class="lead-yes-btn" style="background: var(--theme-color, #0066CC); color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: all 0.2s ease; display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-user-plus" style="font-size: 12px;"></i>
                            <span>${leadButtonText}</span>
                        </button>
                        <button class="lead-no-btn" style="background: #f5f5f5; color: #555; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: all 0.2s ease;">No, thanks</button>
                    </div>
                `;

                // Add event listeners to the buttons
                const yesButton = messageDiv.querySelector('.lead-yes-btn');
                const noButton = messageDiv.querySelector('.lead-no-btn');

                yesButton.addEventListener('click', () => {
                    // Remove the buttons to prevent multiple clicks
                    yesButton.remove();
                    noButton.remove();

                    // Store the product interest for pre-filling the lead form
                    if (productInterest) {
                        this.leadProductInterest = productInterest;
                    }

                    // Open the lead form
                    this.openLeadForm();
                });

                noButton.addEventListener('click', () => {
                    // Remove the buttons to prevent multiple clicks
                    yesButton.remove();
                    noButton.remove();

                    // Mark as declined to prevent showing success message
                    this.leadSuggested = true;

                    // Acknowledge the user's choice
                    this.displayMessage("No problem! Let me know if you have any other questions.", "bot");

                    // Set a flag to not suggest again for a while
                    this.lastLeadDecline = Date.now();
                });

                // Add the message to the chat
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            },

            // Detect specific product interest from conversation
            detectProductInterest(text) {
                // Define product categories to look for
                const productCategories = {
                    'pricing plans': ['pricing', 'price', 'plan', 'subscription', 'cost', 'package'],
                    'features': ['feature', 'functionality', 'capabilities', 'can it do', 'does it have'],
                    'integrations': ['integrate', 'integration', 'connect', 'api', 'webhook'],
                    'demo': ['demo', 'demonstration', 'show me', 'example', 'trial'],
                    'documentation': ['documentation', 'docs', 'guide', 'tutorial', 'how to']
                };

                // Check each category
                for (const [category, keywords] of Object.entries(productCategories)) {
                    if (keywords.some(keyword => text.includes(keyword))) {
                        return category;
                    }
                }

                return null;
            },

            // Detect direct ticket intent from user message
            detectTicketIntent(message) {
                const ticketPhrases = [
                    'create ticket', 'open ticket', 'submit ticket', 'raise ticket', 'new ticket',
                    'support ticket', 'help ticket', 'make a ticket', 'start a ticket',
                    'generate ticket', 'file a ticket', 'get a ticket', 'issue a ticket',
                    'talk to a human', 'talk to a person', 'talk to an agent', 'speak to someone',
                    'contact support', 'need help with', 'having trouble with', 'having a problem with',
                    'not working', 'doesn\'t work', 'isn\'t working', 'broken', 'issue with'
                ];

                return ticketPhrases.some(phrase => message.includes(phrase));
            },

            // Check if we should offer a ticket based on the conversation with intelligent throttling
            checkForTicketOpportunity(question, answer) {
                if (!config.enableTickets) return;
                
                const lowerCaseQuestion = question.toLowerCase();
                const lowerCaseAnswer = answer.toLowerCase();
                
                // Track ticket suggestion attempts to prevent spam
                if (!this.ticketSuggestionTracking) {
                    this.ticketSuggestionTracking = {
                        lastSuggestion: 0,
                        suggestionCount: 0,
                        conversationStartTime: Date.now(),
                        questionsWithoutHelp: 0
                    };
                }
                
                const now = Date.now();
                const timeSinceLastSuggestion = now - this.ticketSuggestionTracking.lastSuggestion;
                const timeSinceConversationStart = now - this.ticketSuggestionTracking.conversationStartTime;
                
                // Don't suggest tickets too frequently (minimum 2 minutes between suggestions)
                if (timeSinceLastSuggestion < 120000) {
                    return;
                }
                
                // Don't suggest tickets if we've already suggested 2 times in this conversation
                if (this.ticketSuggestionTracking.suggestionCount >= 2) {
                    return;
                }
                
                // Don't suggest tickets too early in the conversation (at least 30 seconds and 2 questions)
                if (timeSinceConversationStart < 30000 || this.messageCount < 2) {
                    return;
                }
                
                // Direct ticket request detection - always honor explicit requests
                if (this.detectTicketIntent(lowerCaseQuestion)) {
                    setTimeout(() => {
                        this.askAboutTicketCreation("I understand you'd like to create a support ticket.");
                        this.ticketSuggestionTracking.lastSuggestion = now;
                        this.ticketSuggestionTracking.suggestionCount++;
                    }, 1000);
                    return;
                }
                
                // Check if the bot response already includes a ticket suggestion
                const botAlreadySuggestsTicket = 
                    lowerCaseAnswer.includes("would you like to create a support ticket") ||
                    lowerCaseAnswer.includes("would you like to create a ticket") ||
                    lowerCaseAnswer.includes("create a support ticket") ||
                    lowerCaseAnswer.includes("support ticket");
                
                // If the bot already suggested a ticket, don't add another suggestion
                if (botAlreadySuggestsTicket) {
                    this.ticketSuggestionTracking.lastSuggestion = now;
                    this.ticketSuggestionTracking.suggestionCount++;
                    return;
                }
                
                // Enhanced "can't help" detection with smarter patterns
                const botCantHelp = 
                    lowerCaseAnswer.includes("i don't have enough information") ||
                    lowerCaseAnswer.includes("i don't have any information") ||
                    lowerCaseAnswer.includes("i couldn't extract any useful information") ||
                    lowerCaseAnswer.includes("i'm sorry, i don't know") ||
                    lowerCaseAnswer.includes("i don't have the answer") ||
                    lowerCaseAnswer.includes("i don't have specific information") ||
                    (lowerCaseAnswer.includes("sorry") &&
                     (lowerCaseAnswer.includes("can't help") ||
                      lowerCaseAnswer.includes("cannot help") ||
                      lowerCaseAnswer.includes("don't know")));
                
                // Check for enhanced fallback responses (these should NOT trigger ticket suggestions)
                const isEnhancedFallback = 
                    lowerCaseAnswer.includes("i found some related information") ||
                    lowerCaseAnswer.includes("here are some related topics") ||
                    lowerCaseAnswer.includes("could you rephrase your question") ||
                    lowerCaseAnswer.includes("let me suggest trying a different approach") ||
                    lowerCaseAnswer.includes("to better assist you") ||
                    lowerCaseAnswer.includes("what specific problem are you trying to solve");
                
                // Only count as "can't help" if it's not an enhanced fallback response
                if (botCantHelp && !isEnhancedFallback) {
                    this.ticketSuggestionTracking.questionsWithoutHelp++;
                    
                    // Only suggest ticket after 3 consecutive questions the bot couldn't help with
                    // AND if we're not in an enhanced fallback conversation
                    if (this.ticketSuggestionTracking.questionsWithoutHelp >= 3) {
                        setTimeout(() => {
                            this.askAboutTicketCreation("I'm having difficulty finding the right information for you despite multiple attempts. Would you like to create a support ticket so a human agent can provide specialized assistance?");
                            this.ticketSuggestionTracking.lastSuggestion = now;
                            this.ticketSuggestionTracking.suggestionCount++;
                            this.ticketSuggestionTracking.questionsWithoutHelp = 0; // Reset counter
                        }, 2000);
                    }
                    return;
                } else if (!botCantHelp || isEnhancedFallback) {
                    // Reset the counter if the bot provided helpful response or used enhanced fallback
                    this.ticketSuggestionTracking.questionsWithoutHelp = 0;
                }
                
                // More selective problem-specific language detection
                const hasUrgentProblem = this.detectUrgentProblem(lowerCaseQuestion, lowerCaseAnswer);
                if (hasUrgentProblem && this.messageCount >= 3) {
                    setTimeout(() => {
                        this.askAboutTicketCreation("It sounds like you're experiencing a significant issue. Would you like to create a support ticket to get direct help from our technical team?");
                        this.ticketSuggestionTracking.lastSuggestion = now;
                        this.ticketSuggestionTracking.suggestionCount++;
                    }, 1000);
                    return;
                }
                
                // Check for lead intent if we have enough messages and haven't suggested a lead form yet
                if (this.messageCount >= 2 && !this.leadSuggested) {
                    this.checkForLeadIntent();
                }
            },

            // Detect if the conversation indicates an urgent problem that truly needs a ticket
            detectUrgentProblem(question, answer) {
                const urgentProblemPhrases = [
                    'completely broken',
                    'totally broken',
                    'not working at all',
                    'completely down',
                    'system is down',
                    'critical error',
                    'urgent issue',
                    'emergency',
                    'can\'t access',
                    'cannot access',
                    'locked out',
                    'data loss',
                    'lost data',
                    'crashed',
                    'keeps crashing',
                    'won\'t start',
                    'will not start',
                    'completely failed'
                ];
                
                const moderateProblemPhrases = [
                    'not working',
                    'doesn\'t work',
                    'isn\'t working',
                    'broken',
                    'error message',
                    'getting an error'
                ];
                
                // Check for urgent problems first
                const hasUrgentProblem = urgentProblemPhrases.some(phrase => 
                    question.includes(phrase) || answer.includes(phrase));
                
                if (hasUrgentProblem) {
                    return true;
                }
                
                // For moderate problems, require additional context indicating frustration or repeated issues
                const hasModerateProblem = moderateProblemPhrases.some(phrase => 
                    question.includes(phrase) || answer.includes(phrase));
                
                if (hasModerateProblem) {
                    const frustrationIndicators = [
                        'still',
                        'keeps',
                        'always',
                        'every time',
                        'again',
                        'frustrated',
                        'annoying',
                        'multiple times',
                        'tried everything',
                        'nothing works'
                    ];
                    
                    return frustrationIndicators.some(indicator => 
                        question.includes(indicator) || answer.includes(indicator));
                }
                
                return false;
            },

            // Detect problem language in the conversation
            detectProblemLanguage(question, answer) {
                // Problem indicators in user question
                const problemPhrases = [
                    'problem', 'issue', 'error', 'trouble', 'not working', 'doesn\'t work',
                    'broken', 'failed', 'failure', 'bug', 'glitch', 'wrong', 'incorrect',
                    'help me with', 'can\'t figure out', 'doesn\'t make sense', 'confused about',
                    'stuck', 'can\'t access', 'unable to', 'difficulty', 'having trouble'
                ];

                // Frustration indicators
                const frustrationPhrases = [
                    'frustrated', 'annoyed', 'annoying', 'upset', 'angry', 'ridiculous',
                    'terrible', 'horrible', 'awful', 'worst', 'bad experience', 'disappointing',
                    'disappointed', 'waste of time', 'useless', 'not helpful'
                ];

                // Check for problem phrases in the question
                const hasProblemPhrase = problemPhrases.some(phrase => question.includes(phrase));

                // Check for frustration phrases in the question
                const hasFrustrationPhrase = frustrationPhrases.some(phrase => question.includes(phrase));

                // Check if the answer indicates the chatbot couldn't help
                const unhelpfulAnswer =
                    answer.includes("i'm not sure") ||
                    answer.includes("i don't know") ||
                    answer.includes("i'm sorry") ||
                    answer.includes("i apologize") ||
                    answer.includes("i can't help");

                // Return true if there's a problem phrase or frustration combined with an unhelpful answer
                return hasProblemPhrase || (hasFrustrationPhrase && unhelpfulAnswer);
            },

            // Ask the user if they want to create a ticket
            askAboutTicketCreation(message = "Would you like to create a support ticket so a human agent can help you with this?") {
                // Skip if tickets are disabled
                if (!config.enableTickets) {
                    this.displayMessage("I'm sorry I couldn't help with that. Is there anything else you'd like to know?", "bot");
                    return;
                }

                // Make sure the ticket button is visible if tickets are enabled
                const ticketButton = document.getElementById('chatbot-ticket-button');
                if (ticketButton && config.enableTickets) {
                    ticketButton.style.display = 'flex';
                }

                const messages = document.getElementById('chatbot-messages');

                // Create a message with buttons
                const messageDiv = document.createElement('div');
                messageDiv.className = 'chatbot-message bot';
                messageDiv.innerHTML = `
                    <p>${message}</p>
                    <div style="display: flex; gap: 10px; margin-top: 12px;">
                        <button class="ticket-yes-btn" style="background: var(--theme-color, #0066CC); color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: all 0.2s ease; display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-ticket-alt" style="font-size: 12px;"></i>
                            <span>Create ticket</span>
                        </button>
                        <button class="ticket-no-btn" style="background: #f5f5f5; color: #555; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: all 0.2s ease;">No, thanks</button>
                    </div>
                `;

                // Add event listeners to the buttons
                const yesButton = messageDiv.querySelector('.ticket-yes-btn');
                const noButton = messageDiv.querySelector('.ticket-no-btn');

                yesButton.addEventListener('click', () => {
                    // Remove the buttons to prevent multiple clicks
                    yesButton.remove();
                    noButton.remove();

                    // Start the ticket creation process
                    this.openTicketForm();
                });

                noButton.addEventListener('click', () => {
                    // Remove the buttons to prevent multiple clicks
                    yesButton.remove();
                    noButton.remove();

                    // Acknowledge the user's choice
                    this.displayMessage("Okay, let me know if you need anything else!", "bot");
                });

                // Add the message to the chat
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            },

            // Submit sentiment feedback (positive or negative)
            async submitSentiment(sentiment) {
                try {
                    // Get sentiment buttons
                    const positiveButton = document.querySelector('.chatbot-sentiment-button.chatbot-sentiment-positive');
                    const negativeButton = document.querySelector('.chatbot-sentiment-button.chatbot-sentiment-negative');

                    // Disable both buttons
                    positiveButton.classList.add('disabled');
                    negativeButton.classList.add('disabled');

                    // Add visual feedback for the selected button
                    const selectedButton = sentiment ? positiveButton : negativeButton;
                    selectedButton.classList.add('selected');

                    // Show a subtle notification
                    const header = document.querySelector('.chatbot-header');
                    const notification = document.createElement('div');
                    notification.className = 'chatbot-sentiment-notification';
                    notification.textContent = sentiment ? 'Thanks for the positive feedback!' : 'Thanks for your feedback!';
                    notification.style.position = 'absolute';
                    notification.style.top = '60px';
                    notification.style.left = '0';
                    notification.style.right = '0';
                    notification.style.backgroundColor = sentiment ? 'rgba(16, 185, 129, 0.1)' : 'rgba(59, 130, 246, 0.1)';
                    notification.style.color = sentiment ? '#065f46' : '#1e40af';
                    notification.style.padding = '8px';
                    notification.style.textAlign = 'center';
                    notification.style.fontSize = '14px';
                    notification.style.fontWeight = '500';
                    notification.style.borderRadius = '4px';
                    notification.style.margin = '0 10px';
                    notification.style.opacity = '0';
                    notification.style.transform = 'translateY(-10px)';
                    notification.style.transition = 'opacity 0.3s, transform 0.3s';

                    header.insertAdjacentElement('afterend', notification);

                    // Animate notification in
                    setTimeout(() => {
                        notification.style.opacity = '1';
                        notification.style.transform = 'translateY(0)';
                    }, 10);

                    // Send sentiment to backend
                    const response = await fetch(config.sentimentUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-ID': this.userId
                        },
                        body: JSON.stringify({
                            sentiment: sentiment,
                            conversation_id: this.conversationId // Use the correct property
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to submit sentiment');
                    }

                    // Remove notification and reset buttons after delay
                    setTimeout(() => {
                        // Fade out notification
                        notification.style.opacity = '0';
                        notification.style.transform = 'translateY(-10px)';

                        // Remove notification after animation
                        setTimeout(() => {
                            if (notification.parentNode) {
                                notification.parentNode.removeChild(notification);
                            }
                        }, 300);

                        // Reset buttons
                        positiveButton.classList.remove('disabled', 'selected');
                        negativeButton.classList.remove('disabled', 'selected');
                    }, 3000);

                } catch (error) {
                    console.error('Sentiment submission error:', error);

                    // Reset buttons on error
                    document.querySelectorAll('.chatbot-sentiment-button').forEach(button => {
                        button.classList.remove('disabled', 'selected');
                    });
                }
            },

            // Display a message in the chat
            displayMessage(message, type, isHtml = false) {
                const messages = document.getElementById('chatbot-messages');
                const div = document.createElement('div');
                div.className = `chatbot-message ${type}`;

                // Check if the message contains HTML or if isHtml flag is set
                if (isHtml || (typeof message === 'string' && (message.includes('<') && message.includes('>')))) {
                    div.innerHTML = message;
                } else {
                    div.textContent = message;
                }

                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
        };

        // Add event listeners
        document.getElementById('chatbot-toggle').addEventListener('click', () => window.chatbotWidget.toggle());
        document.getElementById('chatbot-send').addEventListener('click', () => window.chatbotWidget.send());
        document.querySelector('.chatbot-close-chat').addEventListener('click', () => window.chatbotWidget.toggle());

        // Dropdown menu functionality
        document.getElementById('chatbot-menu-button').addEventListener('click', () => {
            document.getElementById('chatbot-dropdown-menu').classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.chatbot-header-dropdown') &&
                document.getElementById('chatbot-dropdown-menu').classList.contains('show')) {
                document.getElementById('chatbot-dropdown-menu').classList.remove('show');
            }
        });

        // Menu item event listeners
        const ticketButton = document.getElementById('chatbot-ticket-button');
        if (ticketButton) {
            // Show/hide ticket button based on configuration
            ticketButton.style.display = config.enableTickets ? 'flex' : 'none';

            ticketButton.addEventListener('click', () => {
                document.getElementById('chatbot-dropdown-menu').classList.remove('show');
                window.chatbotWidget.openTicketForm();
            });
        }

        document.getElementById('chatbot-feedback-button').addEventListener('click', () => {
            document.getElementById('chatbot-dropdown-menu').classList.remove('show');
            window.chatbotWidget.openFeedback();
        });

        const leadButton = document.getElementById('chatbot-lead-button');
        if (leadButton) {
            // Show/hide lead button based on configuration
            leadButton.style.display = config.enableLeads ? 'flex' : 'none';

            leadButton.addEventListener('click', () => {
                document.getElementById('chatbot-dropdown-menu').classList.remove('show');
                window.chatbotWidget.openLeadForm();
            });
        }

        // Sentiment buttons - only add listeners if sentiment is enabled
        if (config.enableSentiment) {
            document.querySelector('.chatbot-sentiment-button.chatbot-sentiment-positive').addEventListener('click', () => window.chatbotWidget.submitSentiment(true));
            document.querySelector('.chatbot-sentiment-button.chatbot-sentiment-negative').addEventListener('click', () => window.chatbotWidget.submitSentiment(false));
        }

        // Feedback form buttons
        document.querySelector('.chatbot-feedback-submit').addEventListener('click', () => window.chatbotWidget.submitFeedback());
        document.querySelector('.chatbot-feedback-cancel').addEventListener('click', () => window.chatbotWidget.closeFeedback());

        // Lead form buttons
        document.querySelector('.chatbot-lead-form .chatbot-ticket-submit').addEventListener('click', () => window.chatbotWidget.submitLeadForm());
        document.querySelector('.chatbot-lead-form .chatbot-ticket-cancel').addEventListener('click', () => window.chatbotWidget.closeLeadForm());

        // Input event listeners
        const input = document.getElementById('chatbot-input');
        const sendButton = document.getElementById('chatbot-send');

        input.addEventListener('input', () => {
            sendButton.disabled = !input.value.trim();
        });

        input.addEventListener('keypress', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                window.chatbotWidget.send();
            }
        });
    }

    // Initialize the widget when the DOM is fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initializeWidget();
            // Show notification dot after initialization
            setTimeout(() => window.chatbotWidget.showNotificationDot(), 1000);
        });
    } else {
        initializeWidget();
        // Show notification dot after initialization
        setTimeout(() => window.chatbotWidget.showNotificationDot(), 1000);
    }
})();
