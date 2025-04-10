# Security Audit: Discovered Credentials

⚠️ **WARNING**: This file contains potentially sensitive information discovered during code analysis.
Secure or remove these credentials and consider implementing a secure credential management solution.

## Overview

**Total credentials found:** 6

| Credential Type | Count |
|----------------|-------|
| API Key | 6 |

## Detailed Findings

### clean_o3.py

**API Key (Line 48):**

```
XAI_API_URL = "https://api.x.ai/v1"  # Replace with the actual endpoint URL
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"           # Replace with your actual API key

```

### clean_perp.py

**API Key (Line 134):**

```
        """
        self.api_key = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
        self.api_url = "https://api.x.ai/v1"
```

### src/storage/test_xai_api.py

**API Key (Line 39):**

```
        # Use hard-coded API key (no need for environment variables)
        xai_api_key = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
        
```

### src/cleanupx/utils/simplified_api.py

**API Key (Line 31):**

```
# API Configuration
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
XAI_MODEL_TEXT = "grok-3-mini-latest"
```

### src/cleanupx/utils/api_utils.py

**API Key (Line 72):**

```
if 'XAI_API_KEY' not in globals():
    XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
    
```

**API Key (Line 222):**

```
        # Use the hardcoded key from your working examples
        api_key = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
        
```

# Security Audit: Discovered Credentials

⚠️ **WARNING**: This file contains potentially sensitive information discovered during code analysis.
Secure or remove these credentials and consider implementing a secure credential management solution.

## Overview

**Total credentials found:** 114

| Credential Type | Count |
|----------------|-------|
| API Key | 20 |
| Token | 2 |
| URL with Credentials | 92 |

## Detailed Findings

### WORKING/flask-alt/perplexity-flask.py

**API Key (Line 141):**

```
# NOTE: In a production multi-user environment, you'd want to manage per-user conversation state.
API_KEY = "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"  # replace with your actual API key
chat_client = PerplexityChat(API_KEY)
```

### WORKING/flask-alt/coze-flask.py

**API Key (Line 32):**

```
COZE_SPACE_ID = "7345427862138912773"
HF_API_KEY = "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"

```

**Token (Line 28):**

```
# Constants
COZE_AUTH_TOKEN = 'pat_x43jhhVkypZ7CrKwnFwLGLdHOAegoEQqnhFO4kIqomnw6a3Zp4EaorAYfn6EMLz4'
COZE_BOT_ID = "7462296933429346310"  # Alt Text Generator bot ID
```

### WORKING/cli/perplexity.py

**API Key (Line 178):**

```
    # Initialize with API key
    api_key = "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"
    
```

### finished/search_results/search_20250127_151428_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_153012_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_153934_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_151428_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_153012_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_153934_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_155937_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_153722_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160701_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_151945_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160558_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_151242_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_144814_2.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube...
```

### finished/search_results/search_20250127_155937_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_161727_0.txt

**URL with Credentials (Line 32):**

```
Content:
, California, United States · Stealth ModeI am, first and foremost, a clinician. My specialty is working with kids who employ augmentative and alternative communication devices and/or present as ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 13](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_153722_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160701_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_151945_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160558_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_151242_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_144814_1.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: ) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub...
```

### finished/search_results/search_20250127_155317_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160518_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_151717_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_155405_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_144933_1.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: ) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub...
```

### finished/search_results/search_20250127_152638_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_154350_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_154051_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_155317_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160518_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_151717_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_155405_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_144933_2.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube...
```

### finished/search_results/search_20250127_152638_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_154350_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_154051_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160250_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_155726_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_154231_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160719_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_145355_2.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube...
```

### finished/search_results/search_20250127_145621_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160055_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_151044_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_144605_2.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: bara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub...
```

### finished/search_results/search_20250127_160250_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_155726_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_154231_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_145355_1.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: ) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub...
```

### finished/search_results/search_20250127_160719_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_145621_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160055_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_151044_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_144605_1.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteu...
```

### finished/search_results/search_20250127_151544_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_152841_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160844_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_153106_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_151544_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_152841_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160844_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_153106_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_155239_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_145822_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_153657_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_145549_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160434_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_155239_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_145822_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_153657_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_145549_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160434_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160636_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_145144_2.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7: Luke Steuber](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.c...
```

### finished/search_results/search_20250127_151404_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160636_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_145144_1.txt

**URL with Credentials (Line 23):**

```
   URL: https://medium.com
   Content: ) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub...
```

### finished/search_results/search_20250127_151404_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_150954_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_150008_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_161454_0.txt

**URL with Credentials (Line 32):**

```
Content:
, California, United States · Stealth ModeI am, first and foremost, a clinician. My specialty is working with kids who employ augmentative and alternative communication devices and/or present as ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 13](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_150833_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160804_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160325_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_150954_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_150008_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_150833_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### finished/search_results/search_20250127_160804_1.txt

**URL with Credentials (Line 32):**

```
Content:
) ### [Luke Steuber | Substack: one impossible thing](https://lukesteuber.substack.com/) Launching 35+ new assistants for accessibility, SLPs, businesses, and daily life! Oct 2, 2024 • Luke Steuber. [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 12](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteub
```

### finished/search_results/search_20250127_160325_2.txt

**URL with Credentials (Line 32):**

```
Content:
rbara, California, United States · Stealth ModeLucas "Luke" Steuber, a holder of Master's degrees in Speech and Language Pathology and… · Experience: Stealth Mode · Education: Pacific University ... [https://medium.com › @lukesteuber](https://medium.com/@lukesteuber)[![Image 7](blob:https://searx.be/439b786609e9c40013762a12d94d639e)](https://medium.com/@lukesteuber) ### [Luke Steuber](https://medium.com/@lukesteube
```

### storage/proxy_anthropic_chat.py

**API Key (Line 15):**

```

ANTHROPIC_API_KEY = "test-key-local-dev-2024"

```

### storage/model_info.html

**URL with Credentials (Line 7):**

```
  <title>Model Summaries • actually useful ai</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Open+Sans:wght@400;600&display=swap">
  <style>
```

### storage/old_main.html

**URL with Credentials (Line 57):**

```
    <!-- Fonts and Styles -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Open+Sans:wght@400;600&display=swap">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/markdown-it/13.0.1/markdown-it.min.js"></script>
```

### soon/tools_pending/_geocode_maps.py

**API Key (Line 89):**

```
if __name__ == "__main__":
    api_key = "66be6044be017202539979xpl8d5b6b"  # Replace with your actual Geocode Maps key
    geocode_client = GeocodeMapsClient(api_key)
```

### soon/tools_pending/_carbon_api.py

**API Key (Line 91):**

```
if __name__ == "__main__":
    api_key = "VNfO2257BW0K4zEkCnKKdg"  # Replace with your actual Carbon Marketplace key
    carbon_client = CarbonMarketplaceClient(api_key)
```

### soon/tools_pending/_football_api.py

**API Key (Line 91):**

```
if __name__ == "__main__":
    api_key = "3f1bdd93fe424ac78f52173ac3bd9ea7"  # Replace with your actual Football Data API key
    football_client = FootballDataClient(api_key)
```

### soon/tools_pending/_scrapestack_api.py

**API Key (Line 78):**

```
if __name__ == "__main__":
    api_key = "141991d2b4d9784c24f5ec7b2ecb261a"  # Replace with your actual Scrapestack key
    scrapestack_client = ScrapestackClient(api_key)
```

### soon/tools_pending/_tax_api.py

**API Key (Line 91):**

```
if __name__ == "__main__":
    api_key = "PiHucpwCUfpA87dOUSWhqV0MJXQLBo89"  # Replace with your actual Tax Data key
    tax_data_client = TaxDataClient(api_key)
```

### soon/tools_pending/_openstates_api.py

**API Key (Line 99):**

```
if __name__ == "__main__":
    api_key = "083f77a7-3f7a-49bf-ac44-d92047b7902a"  # Replace with your actual OpenStates key
    openstates_client = OpenStatesClient(api_key)
```

### soon/tools_pending/_phone_verify.py

**API Key (Line 85):**

```
if __name__ == "__main__":
    api_key = "PiHucpwCUfpA87dOUSWhqV0MJXQLBo89"  # Replace with your actual Number Verification key
    number_verification_client = NumberVerificationClient(api_key)
```

### soon/tools_pending/_guardian_api.py

**API Key (Line 94):**

```
if __name__ == "__main__":
    api_key = "d4be32d-c296-430c-b599-3d223efb7df7"  # Replace with your actual Guardian key
    guardian_client = GuardianNewsClient(api_key)
```

### soon/tools_pending/_windy_api.py

**API Key (Line 100):**

```
if __name__ == "__main__":
    api_key = "oEr5iOwUmtblbu9prTMVQBTilkIVlr2j"  # Replace with your actual Windy Webcams key
    webcams_client = WindyWebcamsClient(api_key)
```

### soon/tools_pending/_openweather_api.py

**API Key (Line 92):**

```
if __name__ == "__main__":
    api_key = "93eaf4ae2611e5c4576823656e0c82415633c077"  # Replace with your actual OpenWeather Air Quality key
    air_quality_client = OpenWeatherAirQualityClient(api_key)
```

### soon/tools_pending/flux.py

**API Key (Line 15):**

```
# Replace <my_bfl_api_key> with your own API key
BFL_API_KEY = "<my_bfl_api_key>"

```

### soon/snippets/coze_agent_list.py

**Token (Line 6):**

```
API_URL = "https://api.coze.com/v1/space/published_bots_list"
API_TOKEN = "pat_JF8Lre4IgXOABlmf383x7GyLF6cj6yn6E4ElRKtvYP3DXpYmB9gJpoMyw2qfwjX4"
SPACE_ID = "7345427862138912773"
```

### prompts/coze_analysis/prompts/impossiblepython_prompt.md

**API Key (Line 124):**

```
    city = "San Francisco"
    api_key = "your_api_key_here"  # Replace with your OpenWeatherMap API key
    weather_data = get_weather(city, api_key)
```

### moe/tools/property/location/walkscore_api.py

**API Key (Line 95):**

```
if __name__ == "__main__":
    api_key = "61b0834f61254d3dab14e9683a592c7b"  # Replace with your actual Walk Score key
    walkscore_client = WalkScoreClient(api_key)
```

### moe/tools/property/location/mapquest_api.py

**API Key (Line 90):**

```
if __name__ == "__main__":
    api_key = "857aMIxq4Ldp30Mi0MqABvsBjQijY5co"  # Replace with your actual MapQuest key
    mapquest_client = MapQuestClient(api_key)
```

### moe/tools/data/analysis/data_analyzer.py

**API Key (Line 88):**

```
if __name__ == "__main__":
    api_key = "52573597091145c2befcc184c54b49ff"  # Replace with your actual Tisane API key
    tisane_client = TisaneClient(api_key)
```

### moe/archive/old_tools/inbox/processed/pixabay_api.py

**API Key (Line 94):**

```
if __name__ == "__main__":
    api_key = "45497543-be9605f4a10e5812fff3aa61f"  # Replace with your actual Pixabay key
    pixabay_client = PixabayClient(api_key)
```

