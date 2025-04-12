# api_utilities (Code)

**File:** soon/snippets/api_utilities.js  
**Language:** JavaScript  
**Lines:** 99  

**Description:** **: This module exports several utilities for an application. It includes API_CONFIG, which dynamically determines the base URL for API calls based on whether the app is running on localhost or a production environment. It also features MessageRotator, an object that handles a rotating list of messages for user interface elements, with methods to cycle through messages at intervals. Additionally, ImageCounter is an object that fetches an image count from an API endpoint and updates a message in the rotator to display the current count, handling asynchronous operations and error logging.

```javascript
/**
 * API and Message Utilities
 * Extracted from old_alt_scripts.js
 */

// API Configuration
export const API_CONFIG = {
    getBaseUrl() {
        return window.location.hostname === "localhost"
            ? "http://localhost:5002"
            : "https://ai.assisted.space";
    }
};

// Message Rotation System
export const MessageRotator = {
    messages: [
        "Loading count...",
        "Back from the dead!",
        "Multiple languages!",
        "Try the text to speech!",
        "No image training!",
        "Adjust length!",
        "See the ? button!",
        "This isn't a chatbot!",
        "Stores absolutely nothing!",
        "Try Enhance!",
        "Support this project below!",
        "Try the interpreters!",
        "Free to use!",
        "I don't make images!",
        "Source code below!",
        "Streaming text to speech!",
        "Privacy first!",
        "Analyze art styles!",
        "Switch controls!",
        "Interpret context!",
        "Read emotio
```

