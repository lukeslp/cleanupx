# html_templates (Code)

**File:** soon/snippets/html_templates.js  
**Language:** JavaScript  
**Lines:** 143  

**Description:** **: This code defines a JavaScript module that exports an object called Templates containing several functions to generate HTML strings for various UI components like upload area, result container, control buttons, support buttons, and settings tray. It also exports an object called TemplateUtils with utility functions to create, inject, and append these HTML elements to the DOM. The purpose is to provide reusable, accessible HTML templates for a web application, likely related to image uploading and processing.  

```javascript
/**
 * HTML Templates
 * Reusable HTML components with accessibility support
 */

export const Templates = {
    // File Upload Area
    uploadArea: () => `
        <div id="uploadArea" 
             class="upload-area" 
             aria-labelledby="upload-heading"
             role="button"
             tabindex="0"
             aria-pressed="false">
            <i class="fas fa-cloud-upload-alt upload-icon" aria-hidden="true"></i>
            <h2 id="upload-heading" class="upload-text">
                Drop, paste, or click to upload!
            </h2>
            <div class="upload-subtext">
                JPG, JPEG, PNG, GIF, WEBP, and more. Try any format, it might work!<br /><br />
                Max size: 20MB
            </div>
            <input type="file"
                   id="fileInput"
                   accept="image/*,video/*,.heic,.heif,image/heic,image/heif,video/quicktime,video/webm,video/mp4,video/x-msvideo,video/x-flv,video/x-ms-wmv,video/x-matroska,video/3gpp,v
```

