# Writing Style Setup Skill

## Purpose
Captures and applies a consistent brand voice across all agent-generated copy. Stop every bot writing differently.

## Style Profile Structure

```yaml
brand_voice:
  name: "Professional Technical"
  personality: ["expert", "clear", "helpful", "concise"]
  tone_range: ["formal → conversational"]
  default_tone: "professional but approachable"
  
vocabulary:
  prefer: ["use", "create", "build", "implement"]
  avoid: ["leverage", "utilize", "synergy", "paradigm"]
  jargon_level: "moderate"
  
sentence_structure:
  avg_length: "15-20 words"
  max_length: "30 words"
  style: "active voice preferred"
  
formatting:
  use_headers: true
  use_lists: true
  use_bold: "for key terms only"
  use_code_blocks: "for technical content"
```

## Voice Dimensions

### 1. Formality Scale
```
1: Casual (hey, check this out)
2: Friendly (here's what you need to know)
3: Professional (this feature enables...)
4: Formal (the system facilitates...)
5: Academic (it is incumbent upon the user to...)
```

### 2. Technical Depth
```
1: Plain English (no jargon)
2: Light Technical (common terms explained)
3: Technical (industry standard)
4: Expert (assumes deep knowledge)
5: Academic (research-level terminology)
```

### 3. Enthusiasm Level
```
1: Reserved (factual, minimal emotion)
2: Measured (positive but restrained)
3: Warm (genuinely helpful tone)
4: Enthusiastic (excited about possibilities)
5: Promotional (marketing energy)
```

## Style Application

### Before (Generic)
```
The API endpoint can be used to retrieve data from the system. 
You will need to authenticate using a valid token.
```

### After (Styled - Professional Technical)
```
The API endpoint retrieves your project data. 
Authenticate with a valid token to access it.
```

## Consistency Enforcement

### Check Score
```python
def style_score(text, style_profile):
    score = 100
    # Check vocabulary
    for word in style_profile['avoid']:
        if word in text.lower():
            score -= 10
    # Check sentence length
    sentences = text.split('.')
    avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
    if avg_len > style_profile['max_sentence_length']:
        score -= 15
    return score
```

### Auto-Fix
```python
def apply_style(text, style_profile):
    # Replace banned words
    for word in style_profile['avoid']:
        text = text.replace(word, style_profile['prefer'][0])
    # Shorten long sentences
    # Adjust formality level
    return text
```

## Quality Checklist
- [ ] Style profile defined
- [ ] Vocabulary preferences set
- [ ] Tone range established
- [ ] Consistency scoring implemented
- [ ] Auto-fix for violations