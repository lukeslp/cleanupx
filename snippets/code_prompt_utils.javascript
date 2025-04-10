# prompt_utils (Code)

**File:** soon/snippets/prompt_utils.js  
**Language:** JavaScript  
**Lines:** 130  

**Description:** **: This JavaScript module consolidates various utilities and templates for handling prompts. It includes objects for generating alt text for images (with base prompts, specialized interpretations, and modification commands), academic writing prompts (for citations, literature reviews, and research writing), prompt management functions (to combine prompts, add constraints, create structured prompts, add examples, and apply formatting), and response format templates (in JSON, Markdown, and structured text formats). The purpose is to provide reusable, structured prompts and tools to enhance content generation, ensuring accessibility, detail, and organization in applications like image descriptions or academic tasks.  

```javascript
/**
 * Prompt Utilities and Templates
 * Consolidated from multiple files
 */

// Alt Text Generation Prompts
export const AltTextPrompts = {
    // Base prompt for standard alt text generation
    base: `You're an Alt Text Specialist, dedicated to creating precise and accessible alt text for digital images, especially memes. Your primary goal is to ensure visually impaired individuals can engage with imagery by providing concise, accurate, and ethically-minded descriptions.

        Skill 1: Create Alt Text

        - **Depict essential visuals and visible text accurately.**
        - **Avoid adding social-emotional context or narrative interpretations unless specifically requested.**
        - **Refrain from speculating on artists' intentions.**
        - **Avoid prepending with "Alt text:" for direct usability.**
        - **Maintain clarity and consistency for all descriptions, including direct image links.**
        - **Character limit:** All descriptions must be under 1000 charac
```

