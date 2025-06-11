/**
 * Xavier AI Chatbot Widget - Configuration Module
 * 
 * This module handles the initialization and configuration of the chatbot widget.
 * It extracts configuration from the script tag and sets up the necessary URLs and settings.
 */

const XavierConfig = (function() {
    /**
     * Initialize configuration from script tag attributes
     * @param {HTMLScriptElement} scriptTag - The script tag with data attributes
     * @returns {Object} - Configuration object
     */
    function init(scriptTag) {
        let apiBase = scriptTag.getAttribute('data-api');
        const chatbotId = scriptTag.getAttribute('data-id');
        
        // Ensure API base ends with a slash
        if (apiBase && !apiBase.endsWith('/')) {
            apiBase += '/';
        }
        
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
            sentiment: `${apiBase}/analytics/sentiment/${chatbotId}`,
            ticket: `${apiBase}ticket/create/${chatbotId}`,
            submitLead: `${apiBase}api/leads/submit`,
            detectLeadIntent: `${apiBase}api/leads/detect-intent`
        };
        
        // Create the config object
        return {
            chatbotId: chatbotId,
            apiBase: apiBase,
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
            enableAvatar: scriptTag.getAttribute('data-enable-avatar') !== 'false' // Default to true
        };
    }
    
    return {
        init: init
    };
})();

// Export to global scope if in browser environment
if (typeof window !== 'undefined') {
    window.XavierConfig = XavierConfig;
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = XavierConfig;
}
