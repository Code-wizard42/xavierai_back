# Xavier AI Chatbot Widget - Modular Structure

This directory contains the modular implementation of the Xavier AI Chatbot Widget. The code has been reorganized into separate modules to improve maintainability, readability, and extensibility.

## Module Structure

The widget is divided into the following modules:

### 1. `config.js`
- Handles initialization and configuration of the chatbot widget
- Extracts configuration from script tag attributes
- Sets up necessary URLs and settings

### 2. `utils.js`
- Provides utility functions used across the chatbot widget
- Includes color manipulation, HTML escaping, and ID generation

### 3. `ui.js`
- Handles UI components of the chatbot widget
- Generates HTML structure
- Manages styling and visual elements
- Provides methods for adding messages and indicators

### 4. `api.js`
- Handles all API communication for the chatbot widget
- Includes methods for sending questions, submitting feedback, creating tickets, etc.

### 5. `events.js`
- Manages event listeners and interactions
- Handles user input, button clicks, and form submissions
- Contains the core business logic for the widget

## Main Entry Point

The main entry point for the widget is `widget-modern.js`, which:
- Initializes all modules
- Sets up the widget on the page
- Coordinates between modules

## Usage

To use the widget, include the following scripts in your HTML:

```html
<script src="js/modules/config.js"></script>
<script src="js/modules/utils.js"></script>
<script src="js/modules/ui.js"></script>
<script src="js/modules/api.js"></script>
<script src="js/modules/events.js"></script>
<script src="js/widget-modern.js" 
        data-api="https://your-api-url.com/" 
        data-id="your-chatbot-id"
        data-name="Support Agent"
        data-theme="#0066CC"
        data-enable-tickets="true"
        data-enable-leads="false">
</script>
```

## Configuration Options

The widget can be configured using the following data attributes on the script tag:

- `data-api`: API base URL (required)
- `data-id`: Chatbot ID (required)
- `data-name`: Name of the chatbot agent (default: "Support Agent")
- `data-avatar`: URL to the agent's avatar image (default: "./assets/agent.png")
- `data-theme`: Theme color in hex format (default: "#0066CC")
- `data-enable-tickets`: Enable/disable ticket creation (default: true)
- `data-enable-leads`: Enable/disable lead collection (default: false)
- `data-enable-smart-lead-detection`: Enable/disable smart lead detection (default: true)
- `data-lead-detection-threshold`: Threshold for lead detection (default: 0.4)
- `data-enable-avatar`: Enable/disable avatar display (default: true)
