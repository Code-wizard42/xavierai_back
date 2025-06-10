/**
 * Xavier AI Chatbot Widget - Utilities Module
 * 
 * This module provides utility functions used across the chatbot widget.
 */

const XavierUtils = (function() {
    /**
     * Convert hex color to RGB
     * @param {string} hex - Hex color code
     * @returns {Object|null} - RGB color object or null if invalid
     */
    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }
    
    /**
     * Adjust color brightness
     * @param {string} hex - Hex color code
     * @param {number} amount - Amount to adjust brightness
     * @returns {string} - Adjusted hex color
     */
    function adjustColor(hex, amount) {
        let r = parseInt(hex.substring(1, 3), 16);
        let g = parseInt(hex.substring(3, 5), 16);
        let b = parseInt(hex.substring(5, 7), 16);
        
        r = Math.max(0, Math.min(255, r + amount));
        g = Math.max(0, Math.min(255, g + amount));
        b = Math.max(0, Math.min(255, b + amount));
        
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }
    
    /**
     * Escape HTML to prevent XSS
     * @param {string} unsafe - Unsafe string that might contain HTML
     * @returns {string} - Escaped safe string
     */
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    /**
     * Generate a random user ID
     * @returns {string} - Random user ID
     */
    function generateUserId() {
        return 'user_' + Math.random().toString(36).substring(2, 11);
    }
    
    return {
        hexToRgb: hexToRgb,
        adjustColor: adjustColor,
        escapeHtml: escapeHtml,
        generateUserId: generateUserId
    };
})();

// Export to global scope if in browser environment
if (typeof window !== 'undefined') {
    window.XavierUtils = XavierUtils;
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = XavierUtils;
}
