/**
 * Xavier AI Chatbot Widget - Events Module
 * 
 * This module handles all event listeners and interactions for the chatbot widget.
 */

const XavierEvents = (function() {
    // State variables
    let state = {
        userId: null,
        conversationId: null,
        isTyping: false,
        typingIndicator: null,
        ticketFormData: {},
        isCreatingTicket: false,
        currentTicketField: null,
        messageCount: 0,
        leadSuggested: false,
        leadFormSubmitted: false,
        lastLeadCheck: 0,
        config: null,
        ticketSuggestionTracking: null
    };
    
    /**
     * Initialize event handlers
     * @param {Object} config - Widget configuration
     */
    function init(config) {
        state.config = config;
        state.userId = XavierUtils.generateUserId();
        
        // Set up input event listener
        const input = document.getElementById('chatbot-input');
        const sendButton = document.getElementById('chatbot-send');
        
        if (input && sendButton) {
            input.addEventListener('input', () => {
                sendButton.disabled = !input.value.trim();
            });
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && input.value.trim()) {
                    sendMessage();
                }
            });
            
            sendButton.addEventListener('click', () => {
                if (!sendButton.disabled) {
                    sendMessage();
                }
            });
        }
        
        // Toggle button
        const toggleButton = document.getElementById('chatbot-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', toggleChat);
        }
        
        // Close button
        const closeButton = document.querySelector('.chatbot-close-chat');
        if (closeButton) {
            closeButton.addEventListener('click', toggleChat);
        }
        
        // Menu button
        const menuButton = document.getElementById('chatbot-menu-button');
        const dropdownMenu = document.getElementById('chatbot-dropdown-menu');
        
        if (menuButton && dropdownMenu) {
            menuButton.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdownMenu.classList.toggle('show');
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', () => {
                if (dropdownMenu.classList.contains('show')) {
                    dropdownMenu.classList.remove('show');
                }
            });
        }
        
        // Ticket button
        const ticketButton = document.getElementById('chatbot-ticket-button');
        if (ticketButton && config.enableTickets) {
            ticketButton.addEventListener('click', openTicketForm);
        }
        
        // Feedback button
        const feedbackButton = document.getElementById('chatbot-feedback-button');
        if (feedbackButton) {
            feedbackButton.addEventListener('click', openFeedbackForm);
        }
        
        // Lead button
        const leadButton = document.getElementById('chatbot-lead-button');
        if (leadButton && config.enableLeads) {
            leadButton.addEventListener('click', openLeadForm);
        }
        
        // Sentiment buttons
        const positiveButton = document.querySelector('.chatbot-sentiment-positive');
        const negativeButton = document.querySelector('.chatbot-sentiment-negative');
        
        if (positiveButton && negativeButton) {
            positiveButton.addEventListener('click', () => submitSentiment('positive'));
            negativeButton.addEventListener('click', () => submitSentiment('negative'));
        }
        
        // Feedback form buttons
        const feedbackSubmit = document.querySelector('.chatbot-feedback-submit');
        const feedbackCancel = document.querySelector('.chatbot-feedback-cancel');
        
        if (feedbackSubmit && feedbackCancel) {
            feedbackSubmit.addEventListener('click', submitFeedback);
            feedbackCancel.addEventListener('click', closeFeedbackForm);
        }
        
        // Show notification dot after a delay
        setTimeout(() => {
            const notificationDot = document.querySelector('.chatbot-notification-dot');
            if (notificationDot) {
                notificationDot.style.display = 'block';
            }
        }, 5000);
    }
    
    /**
     * Toggle chat visibility
     */
    function toggleChat() {
        const content = document.getElementById('chatbot-content');
        const toggle = document.getElementById('chatbot-toggle');
        const notificationDot = document.querySelector('.chatbot-notification-dot');
        
        if (!content || !toggle) return;
        
        content.classList.toggle('chatbot-visible');
        toggle.style.display = content.classList.contains('chatbot-visible') ? 'none' : 'flex';
        
        if (content.classList.contains('chatbot-visible')) {
            const input = document.getElementById('chatbot-input');
            if (input) input.focus();
            
            // Hide notification dot when chat is opened
            if (notificationDot) {
                notificationDot.style.display = 'none';
            }
        }
    }
    
    /**
     * Send a message to the chatbot
     */
    async function sendMessage() {
        const input = document.getElementById('chatbot-input');
        const sendButton = document.getElementById('chatbot-send');
        
        if (!input || !sendButton) return;
        
        const question = input.value.trim();
        if (!question) return;
        
        // If we're in ticket creation mode, handle the ticket input instead
        if (state.isCreatingTicket && state.currentTicketField) {
            handleTicketInput(state.currentTicketField);
            return;
        }
        
        try {
            input.disabled = true;
            sendButton.disabled = true;
            
            // Display user message
            XavierUI.addMessage(question, 'user');
            input.value = '';
            
            // Show typing indicator
            state.isTyping = true;
            state.typingIndicator = XavierUI.showTypingIndicator();
            
            // Increment message count for lead detection
            state.messageCount++;
            
            // Send to API
            const data = await XavierAPI.sendQuestion(
                question, 
                state.config.askUrl, 
                state.userId, 
                state.conversationId
            );
            
            // Store the conversation ID for future use
            if (data.conversation_id) {
                state.conversationId = data.conversation_id;
            }
            
            // Hide typing indicator and show response
            state.isTyping = false;
            XavierUI.hideTypingIndicator(state.typingIndicator);
            XavierUI.addMessage(data.answer, 'bot');
            
            // Check for ticket or lead opportunities
            checkForTicketOpportunity(question, data.answer);
            
        } catch (error) {
            console.error('Chatbot error:', error);
            state.isTyping = false;
            XavierUI.hideTypingIndicator(state.typingIndicator);
            XavierUI.addMessage('Sorry, something went wrong. Please try again.', 'error');
        } finally {
            input.disabled = false;
            sendButton.disabled = false;
            input.focus();
        }
    }
    
    /**
     * Check if we should offer a ticket based on the conversation
     * @param {string} question - User's question
     * @param {string} answer - Bot's answer
     */
    function checkForTicketOpportunity(question, answer) {
        if (!state.config.enableTickets) return;
        
        const lowerCaseQuestion = question.toLowerCase();
        const lowerCaseAnswer = answer.toLowerCase();
        
        // Track ticket suggestion attempts to prevent spam
        if (!state.ticketSuggestionTracking) {
            state.ticketSuggestionTracking = {
                lastSuggestion: 0,
                suggestionCount: 0,
                conversationStartTime: Date.now(),
                questionsWithoutHelp: 0
            };
        }
        
        const now = Date.now();
        const timeSinceLastSuggestion = now - state.ticketSuggestionTracking.lastSuggestion;
        const timeSinceConversationStart = now - state.ticketSuggestionTracking.conversationStartTime;
        
        // Don't suggest tickets too frequently (minimum 2 minutes between suggestions)
        if (timeSinceLastSuggestion < 120000) {
            return;
        }
        
        // Don't suggest tickets if we've already suggested 2 times in this conversation
        if (state.ticketSuggestionTracking.suggestionCount >= 2) {
            return;
        }
        
        // Don't suggest tickets too early in the conversation (at least 30 seconds and 2 questions)
        if (timeSinceConversationStart < 30000 || state.messageCount < 2) {
            return;
        }
        
        // Direct ticket request detection - always honor explicit requests
        if (detectTicketIntent(lowerCaseQuestion)) {
            setTimeout(() => {
                askAboutTicketCreation("I understand you'd like to create a support ticket.");
                state.ticketSuggestionTracking.lastSuggestion = now;
                state.ticketSuggestionTracking.suggestionCount++;
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
            state.ticketSuggestionTracking.lastSuggestion = now;
            state.ticketSuggestionTracking.suggestionCount++;
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
                    state.ticketSuggestionTracking.questionsWithoutHelp++;
                    
                    // Only suggest ticket after 3 consecutive questions the bot couldn't help with
                    // AND if we're not in an enhanced fallback conversation
                    if (state.ticketSuggestionTracking.questionsWithoutHelp >= 3) {
                        setTimeout(() => {
                            askAboutTicketCreation("I'm having difficulty finding the right information for you despite multiple attempts. Would you like to create a support ticket so a human agent can provide specialized assistance?");
                            state.ticketSuggestionTracking.lastSuggestion = now;
                            state.ticketSuggestionTracking.suggestionCount++;
                            state.ticketSuggestionTracking.questionsWithoutHelp = 0; // Reset counter
                        }, 2000);
                    }
                    return;
                } else if (!botCantHelp || isEnhancedFallback) {
                    // Reset the counter if the bot provided helpful response or used enhanced fallback
                    state.ticketSuggestionTracking.questionsWithoutHelp = 0;
                }
        
        // More selective problem-specific language detection
        const hasUrgentProblem = detectUrgentProblem(lowerCaseQuestion, lowerCaseAnswer);
        if (hasUrgentProblem && state.messageCount >= 3) {
            setTimeout(() => {
                askAboutTicketCreation("It sounds like you're experiencing a significant issue. Would you like to create a support ticket to get direct help from our technical team?");
                state.ticketSuggestionTracking.lastSuggestion = now;
                state.ticketSuggestionTracking.suggestionCount++;
            }, 1000);
            return;
        }
        
        // Check for lead intent if we have enough messages and haven't suggested a lead form yet
        if (state.config.enableLeads && state.messageCount >= 2 && !state.leadSuggested) {
            checkForLeadIntent(question);
        }
    }
    
    /**
     * Detect if the user is explicitly asking for a ticket
     * @param {string} question - User's question in lowercase
     * @returns {boolean} - Whether ticket intent is detected
     */
    function detectTicketIntent(question) {
        const ticketPhrases = [
            'create a ticket',
            'open a ticket',
            'submit a ticket',
            'make a ticket',
            'start a ticket',
            'need a ticket',
            'support ticket',
            'talk to a human',
            'talk to a person',
            'talk to an agent',
            'speak to a human',
            'speak to a person',
            'speak to an agent',
            'talk to support',
            'speak to support',
            'contact support'
        ];
        
        return ticketPhrases.some(phrase => question.includes(phrase));
    }
    
    /**
     * Detect if the conversation indicates an urgent problem that truly needs a ticket
     * This is more selective than the old detectProblemLanguage function
     * @param {string} question - User's question in lowercase
     * @param {string} answer - Bot's answer in lowercase
     * @returns {boolean} - Whether urgent problem language is detected
     */
    function detectUrgentProblem(question, answer) {
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
    }
    
    /**
     * Ask the user if they want to create a ticket
     * @param {string} message - Message to display
     */
    function askAboutTicketCreation(message) {
        const html = `
            <p>${message}</p>
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button id="create-ticket-btn" style="flex: 1; background: var(--theme-color); color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                    Create ticket
                </button>
                <button id="no-ticket-btn" style="flex: 1; background: #f1f1f1; color: #333; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                    No, thanks
                </button>
            </div>
        `;
        
        XavierUI.addMessage(html, 'bot', true);
        
        // Add event listeners
        const createBtn = document.getElementById('create-ticket-btn');
        const noBtn = document.getElementById('no-ticket-btn');
        
        if (createBtn && noBtn) {
            createBtn.addEventListener('click', openTicketForm);
            noBtn.addEventListener('click', () => {
                XavierUI.addMessage("No problem. Let me know if you need anything else!", 'bot');
            });
        }
    }
    
    /**
     * Check for lead intent in the conversation
     * @param {string} message - User's message
     */
    async function checkForLeadIntent(message) {
        if (!state.config.enableLeads || !state.config.enableSmartLeadDetection) return;
        
        // Don't check too frequently
        const now = Date.now();
        if (now - state.lastLeadCheck < 30000) return; // 30 seconds cooldown
        
        state.lastLeadCheck = now;
        
        try {
            const data = await XavierAPI.detectLeadIntent(
                message,
                state.config.detectLeadIntentUrl,
                state.userId,
                state.conversationId
            );
            
            if (data.score && data.score >= state.config.leadDetectionThreshold) {
                suggestLeadForm();
            }
        } catch (error) {
            console.error('Lead detection error:', error);
        }
    }
    
    /**
     * Suggest the lead form to the user
     */
    function suggestLeadForm() {
        if (state.leadSuggested || state.leadFormSubmitted) return;
        
        state.leadSuggested = true;
        
        const html = `
            <p>Would you like to leave your contact information so we can follow up with you?</p>
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button id="open-lead-form-btn" style="flex: 1; background: var(--theme-color); color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                    Yes, please
                </button>
                <button id="no-lead-form-btn" style="flex: 1; background: #f1f1f1; color: #333; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                    No, thanks
                </button>
            </div>
        `;
        
        XavierUI.addMessage(html, 'bot', true);
        
        // Add event listeners
        const yesBtn = document.getElementById('open-lead-form-btn');
        const noBtn = document.getElementById('no-lead-form-btn');
        
        if (yesBtn && noBtn) {
            yesBtn.addEventListener('click', openLeadForm);
            noBtn.addEventListener('click', () => {
                XavierUI.addMessage("No problem. Let me know if you need anything else!", 'bot');
            });
        }
    }
    
    /**
     * Open the ticket form
     */
    function openTicketForm() {
        state.ticketFormData = {};
        state.isCreatingTicket = true;
        state.currentTicketField = 'subject';
        
        // Extract conversation context for smart pre-filling
        extractConversationContext();
        
        const ticketForm = document.getElementById('chatbot-ticket-form');
        if (ticketForm) {
            ticketForm.classList.add('chatbot-visible');
        }
        
        // Focus on the subject field
        const subjectField = document.getElementById('ticket-subject');
        if (subjectField) {
            subjectField.focus();
        }
    }
    
    /**
     * Extract context from the conversation to pre-fill ticket fields
     */
    function extractConversationContext() {
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
        
        // Create a formatted conversation context for the description
        // Add a header and timestamp
        const timestamp = new Date().toLocaleString();
        let contextHeader = `--- Conversation History (${timestamp}) ---\n\n`;
        
        // Format the conversation in a readable way
        state.ticketFormData.conversationContext = contextHeader + recentMessages
            .map(msg => `${msg.type === 'user' ? '👤 Customer' : '🤖 Chatbot'}: ${msg.content}`)
            .join('\n\n');
    }
    
    /**
     * Handle ticket form input
     * @param {string} field - Field being edited
     */
    function handleTicketInput(field) {
        const input = document.getElementById('chatbot-input');
        if (!input) return;
        
        const value = input.value.trim();
        if (!value) return;
        
        state.ticketFormData[field] = value;
        input.value = '';
        
        // Display the entered value
        XavierUI.addMessage(`${getFieldLabel(field)}: ${value}`, 'user');
        
        // Move to the next field
        switch (field) {
            case 'subject':
                state.currentTicketField = 'description';
                XavierUI.addMessage("Great! Now please provide a detailed description of the issue:", 'bot');
                break;
                
            case 'description':
                state.currentTicketField = 'account';
                XavierUI.addMessage("Thanks! Finally, please provide your contact details (email or phone):", 'bot');
                break;
                
            case 'account':
                state.currentTicketField = null;
                state.isCreatingTicket = false;
                state.ticketFormData.priority = 'medium';
                displayTicketSummary();
                break;
        }
    }
    
    /**
     * Get the label for a ticket field
     * @param {string} field - Field name
     * @returns {string} - Field label
     */
    function getFieldLabel(field) {
        switch (field) {
            case 'subject': return 'Subject';
            case 'description': return 'Description';
            case 'account': return 'Contact Details';
            case 'priority': return 'Priority';
            default: return field.charAt(0).toUpperCase() + field.slice(1);
        }
    }
    
    /**
     * Display ticket summary and confirmation
     */
    function displayTicketSummary() {
        const html = `
            <div class="ticket-summary">
                <h4>Ticket Summary</h4>
                <p><strong>Subject:</strong> ${XavierUtils.escapeHtml(state.ticketFormData.subject)}</p>
                <p><strong>Description:</strong> ${XavierUtils.escapeHtml(state.ticketFormData.description)}</p>
                <p><strong>Contact:</strong> ${XavierUtils.escapeHtml(state.ticketFormData.account)}</p>
                <p><strong>Priority:</strong> ${state.ticketFormData.priority}</p>
                <div style="display: flex; gap: 8px; margin-top: 12px;">
                    <button id="submit-ticket-btn" style="flex: 1; background: var(--theme-color); color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                        Submit Ticket
                    </button>
                    <button id="cancel-ticket-btn" style="flex: 1; background: #f1f1f1; color: #333; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer;">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        
        XavierUI.addMessage(html, 'bot', true);
        
        // Add event listeners
        const submitBtn = document.getElementById('submit-ticket-btn');
        const cancelBtn = document.getElementById('cancel-ticket-btn');
        
        if (submitBtn && cancelBtn) {
            submitBtn.addEventListener('click', submitTicket);
            cancelBtn.addEventListener('click', () => {
                XavierUI.addMessage("Ticket creation cancelled.", 'bot');
            });
        }
    }
    
    /**
     * Submit the ticket to the API
     */
    async function submitTicket() {
        try {
            XavierUI.addMessage("Submitting your ticket...", 'bot');
            
            const ticketData = {
                subject: state.ticketFormData.subject,
                description: state.ticketFormData.description + '\n\n' + state.ticketFormData.conversationContext,
                priority: state.ticketFormData.priority,
                contact: state.ticketFormData.account,
                conversation_id: state.conversationId
            };
            
            const data = await XavierAPI.createTicket(
                ticketData,
                state.config.ticketUrl,
                state.userId
            );
            
            if (data.ticket_id) {
                XavierUI.addMessage(`Your ticket has been created successfully! Ticket ID: ${data.ticket_id}. Our team will contact you soon.`, 'bot');
            } else {
                XavierUI.addMessage("Your ticket has been created successfully! Our team will contact you soon.", 'bot');
            }
            
        } catch (error) {
            console.error('Ticket submission error:', error);
            XavierUI.addMessage("Sorry, there was a problem creating your ticket. Please try again later.", 'error');
        }
    }
    
    /**
     * Open the lead form
     */
    function openLeadForm() {
        const leadForm = document.getElementById('chatbot-lead-form');
        if (leadForm) {
            leadForm.classList.add('chatbot-visible');
        }
        
        // Focus on the name field
        const nameField = document.getElementById('lead-name');
        if (nameField) {
            nameField.focus();
        }
        
        // Add event listeners to the form buttons
        const submitBtn = leadForm.querySelector('.chatbot-ticket-submit');
        const cancelBtn = leadForm.querySelector('.chatbot-ticket-cancel');
        
        if (submitBtn && cancelBtn) {
            submitBtn.addEventListener('click', submitLeadForm);
            cancelBtn.addEventListener('click', () => {
                leadForm.classList.remove('chatbot-visible');
            });
        }
    }
    
    /**
     * Submit the lead form
     */
    async function submitLeadForm() {
        const nameField = document.getElementById('lead-name');
        const emailField = document.getElementById('lead-email');
        const phoneField = document.getElementById('lead-phone');
        const messageField = document.getElementById('lead-message');
        const leadForm = document.getElementById('chatbot-lead-form');
        
        if (!nameField || !emailField || !leadForm) return;
        
        const name = nameField.value.trim();
        const email = emailField.value.trim();
        
        if (!name || !email) {
            alert('Please fill in all required fields.');
            return;
        }
        
        try {
            const leadData = {
                name: name,
                email: email,
                phone: phoneField ? phoneField.value.trim() : '',
                message: messageField ? messageField.value.trim() : '',
                conversation_id: state.conversationId
            };
            
            await XavierAPI.submitLead(
                leadData,
                state.config.submitLeadUrl,
                state.userId
            );
            
            leadForm.classList.remove('chatbot-visible');
            state.leadFormSubmitted = true;
            
            XavierUI.addMessage("Thank you for your interest! We've received your information and will be in touch soon.", 'bot');
            
        } catch (error) {
            console.error('Lead submission error:', error);
            alert('Sorry, there was a problem submitting your information. Please try again later.');
        }
    }
    
    /**
     * Open the feedback form
     */
    function openFeedbackForm() {
        const feedbackModal = document.getElementById('chatbot-feedback');
        if (feedbackModal) {
            feedbackModal.classList.add('chatbot-visible');
            
            // Focus on the textarea
            const textarea = document.getElementById('chatbot-feedback-text');
            if (textarea) {
                textarea.focus();
            }
        }
    }
    
    /**
     * Close the feedback form
     */
    function closeFeedbackForm() {
        const feedbackModal = document.getElementById('chatbot-feedback');
        if (feedbackModal) {
            feedbackModal.classList.remove('chatbot-visible');
            
            // Clear the textarea
            const textarea = document.getElementById('chatbot-feedback-text');
            if (textarea) {
                textarea.value = '';
            }
        }
    }
    
    /**
     * Submit feedback
     */
    async function submitFeedback() {
        const textarea = document.getElementById('chatbot-feedback-text');
        if (!textarea) return;
        
        const feedback = textarea.value.trim();
        if (!feedback) {
            alert('Please enter your feedback before submitting.');
            return;
        }
        
        try {
            await XavierAPI.submitFeedback(
                feedback,
                state.config.feedbackUrl,
                state.userId
            );
            
            closeFeedbackForm();
            XavierUI.addMessage("Thank you for your feedback! We appreciate your input.", 'bot');
            
        } catch (error) {
            console.error('Feedback submission error:', error);
            alert('Sorry, we couldn\'t submit your feedback. Please try again later.');
        }
    }
    
    /**
     * Submit sentiment feedback
     * @param {string} sentiment - 'positive' or 'negative'
     */
    async function submitSentiment(sentiment) {
        try {
            const sentimentButtons = document.querySelectorAll('.chatbot-sentiment-button');
            
            // Disable buttons
            sentimentButtons.forEach(button => {
                button.classList.add('disabled');
            });
            
            await XavierAPI.submitSentiment(
                sentiment,
                state.config.sentimentUrl,
                state.userId,
                state.conversationId
            );
            
            // Show temporary thank you message and re-enable after delay
            setTimeout(() => {
                sentimentButtons.forEach(button => {
                    button.classList.remove('disabled');
                });
            }, 3000);
            
        } catch (error) {
            console.error('Sentiment submission error:', error);
            // Re-enable buttons on error
            const sentimentButtons = document.querySelectorAll('.chatbot-sentiment-button');
            sentimentButtons.forEach(button => {
                button.classList.remove('disabled');
            });
        }
    }
    
    return {
        init: init,
        toggleChat: toggleChat,
        sendMessage: sendMessage,
        openTicketForm: openTicketForm,
        openLeadForm: openLeadForm,
        openFeedbackForm: openFeedbackForm
    };
})();

// Export to global scope if in browser environment
if (typeof window !== 'undefined') {
    window.XavierEvents = XavierEvents;
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = XavierEvents;
}
