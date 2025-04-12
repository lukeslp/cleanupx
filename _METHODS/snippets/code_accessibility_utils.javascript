# accessibility_utils (Code)

**File:** soon/snippets/accessibility_utils.js  
**Language:** JavaScript  
**Lines:** 219  

**Description:** **: This code defines a JavaScript module named AccessibilityUtils that serves as a collection of utility functions aimed at improving web accessibility. It handles various aspects such as display mode management (e.g., toggling between light and dark modes using localStorage), font management (e.g., switching fonts and adjusting sizes), text-to-speech capabilities (e.g., speaking text and adjusting speech rates), switch control for keyboard navigation, eye gaze support for dwell-based interactions, and setup for ARIA attributes to ensure better compatibility with screen readers and keyboard users. The overall purpose is to create a more inclusive user experience by dynamically managing accessibility features and persisting user preferences.  

```javascript
/**
 * Accessibility Utilities
 * Consolidated from multiple files
 */

export const AccessibilityUtils = {
    // Display Mode Management
    initializeDisplayMode() {
        const savedMode = localStorage.getItem("displayMode") || "light-mode";
        document.body.classList.remove("light-mode", "dark-mode");
        document.body.classList.add(savedMode);
    },

    toggleDayNightMode() {
        const currentMode = localStorage.getItem("displayMode") || "light-mode";
        const newMode = currentMode === "dark-mode" ? "light-mode" : "dark-mode";
        document.body.classList.remove("light-mode", "dark-mode");
        document.body.classList.add(newMode);
        localStorage.setItem("displayMode", newMode);

        // Update loading gif if present
        const loadingGif = document.querySelector(".loading-gif");
        if (loadingGif) {
            loadingGif.src = loadingGif.src.replace(
                `triangle_construct_${currentMode.split('-')[0]}.gif`,
             
```

