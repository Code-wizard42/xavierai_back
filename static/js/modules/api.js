/**
 * Xavier AI Chatbot Widget - API Module
 * 
 * This module handles all API communication for the chatbot widget.
 */

const XavierAPI = (function() {
    /**
     * Send a question to the chatbot API
     * @param {string} question - User's question
     * @param {string} askUrl - API URL for asking questions
     * @param {string} userId - User ID for tracking conversations
     * @param {string} conversationId - Current conversation ID if available
     * @returns {Promise<Object>} - API response
     */
    async function sendQuestion(question, askUrl, userId, conversationId) {
        const response = await fetch(askUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-ID': userId
            },
            body: JSON.stringify({
                question,
                conversation_id: conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        return await response.json();
    }
    
    /**
     * Submit feedback to the API
     * @param {string} feedback - User feedback
     * @param {string} feedbackUrl - API URL for submitting feedback
     * @param {string} userId - User ID
     * @returns {Promise<Object>} - API response
     */
    async function submitFeedback(feedback, feedbackUrl, userId) {
        const response = await fetch(feedbackUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-ID': userId
            },
            body: JSON.stringify({ feedback })
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit feedback');
        }
        
        return await response.json();
    }
    
    /**
     * Submit sentiment feedback
     * @param {string} sentiment - 'positive' or 'negative'
     * @param {string} sentimentUrl - API URL for submitting sentiment
     * @param {string} userId - User ID
     * @param {string} conversationId - Current conversation ID
     * @returns {Promise<Object>} - API response
     */
    async function submitSentiment(sentiment, sentimentUrl, userId, conversationId) {
        const response = await fetch(sentimentUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-ID': userId
            },
            body: JSON.stringify({
                sentiment: sentiment,
                conversation_id: conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit sentiment');
        }
        
        return await response.json();
    }
    
    /**
     * Create a support ticket
     * @param {Object} ticketData - Ticket data
     * @param {string} ticketUrl - API URL for creating tickets
     * @param {string} userId - User ID
     * @returns {Promise<Object>} - API response
     */
    async function createTicket(ticketData, ticketUrl, userId) {
        const response = await fetch(ticketUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-ID': userId
            },
            body: JSON.stringify(ticketData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to create ticket');
        }
        
        return await response.json();
    }
    
    /**
     * Submit lead information
     * @param {Object} leadData - Lead data
     * @param {string} submitLeadUrl - API URL for submitting leads
     * @param {string} userId - User ID
     * @returns {Promise<Object>} - API response
     */
    async function submitLead(leadData, submitLeadUrl, userId) {
        const response = await fetch(submitLeadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-ID': userId
            },
            body: JSON.stringify(leadData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit lead');
        }
        
        return await response.json();
    }
    
    /**
     * Detect lead intent from conversation
     * @param {string} message - User message
     * @param {string} detectLeadIntentUrl - API URL for detecting lead intent
     * @param {string} userId - User ID
     * @param {string} conversationId - Current conversation ID
     * @returns {Promise<Object>} - API response with lead intent score
     */
    async function detectLeadIntent(message, detectLeadIntentUrl, userId, conversationId) {
        const response = await fetch(detectLeadIntentUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-ID': userId
            },
            body: JSON.stringify({
                message,
                conversation_id: conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to detect lead intent');
        }
        
        return await response.json();
    }
    
    return {
        sendQuestion: sendQuestion,
        submitFeedback: submitFeedback,
        submitSentiment: submitSentiment,
        createTicket: createTicket,
        submitLead: submitLead,
        detectLeadIntent: detectLeadIntent
    };
})();

// Export to global scope if in browser environment
if (typeof window !== 'undefined') {
    window.XavierAPI = XavierAPI;
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = XavierAPI;
}
