# script (Code)

**File:** storage/script.js  
**Language:** JavaScript  
**Lines:** 329  

**Description:** **: This script is a JavaScript file for a chat application that handles user interactions, theme toggling, file uploads, message sending, and API communications. It manages state for messages, current model, theme, and file handling. Functions include initializing themes and settings, processing messages with markdown, handling file selections, sending messages to an API, and updating the UI dynamically. It processes user inputs, handles streaming responses from an API, and includes error handling for UI elements and API calls.

```javascript
const API_BASE_URL = "https://ai.assisted.space/api";
console.log("API_BASE_URL:", API_BASE_URL);

const state = {
  currentModel: "camina:latest",
  md: window.markdownit(),
  messages: [],
  currentFile: null,
  isResponding: false,
  theme: localStorage.getItem('theme') || 'light'
};
console.log("Initial state:", state);

// Theme handling
function initializeTheme() {
  const themeToggle = document.getElementById('themeToggle');
  if (!themeToggle) {
    console.warn('Theme toggle element not found');
    return;
  }
  themeToggle.checked = state.theme === 'dark';
  document.body.setAttribute('data-theme', state.theme);
}

function toggleTheme() {
  state.theme = state.theme === 'light' ? 'dark' : 'light';
  localStorage.setItem('theme', state.theme);
  document.body.setAttribute('data-theme', state.theme);
}

// Settings panel
function initializeSettings() {
  const settingsButton = document.getElementById('settingsButton');
  const settingsPanel = document.getElementById('settings
```

