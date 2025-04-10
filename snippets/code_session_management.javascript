# session_management (Code)

**File:** soon/snippets/session_management.js  
**Language:** JavaScript  
**Lines:** 99  

**Description:** **: This module manages various aspects of a web application, including session handling (saving and loading user sessions with messages, current assistant, and timestamps), chat history operations (saving, loading, clearing, and initializing history), file handling (opening HTML files and setting up external links), and state management (creating and initializing the application's initial state with configurations like API URLs and bot IDs). It uses browser APIs like localStorage for persistence and ensures data integrity, such as checking session age.  

```javascript
/**
 * Session and History Management
 * Extracted from from_main.js
 */

// Session Management
export const SessionManager = {
    SESSION_STORAGE_KEY: "chat_session",
    CHAT_HISTORY_KEY: "chatHistory",

    saveSession(messages, currentAssistant) {
        const sessionData = {
            messages,
            currentAssistant,
            timestamp: Date.now()
        };
        localStorage.setItem(this.SESSION_STORAGE_KEY, JSON.stringify(sessionData));
    },

    loadSession() {
        const savedSession = localStorage.getItem(this.SESSION_STORAGE_KEY);
        if (savedSession) {
            const { messages, currentAssistant, timestamp } = JSON.parse(savedSession);
            // Only restore if session is less than 24 hours old
            if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
                return { messages, currentAssistant };
            }
        }
        return null;
    }
};

// Chat History Management
export const ChatHistoryManager = {
    CHAT_HIS
```

