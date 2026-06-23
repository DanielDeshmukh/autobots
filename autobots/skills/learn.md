# Learn Skill

## Purpose
Structured teaching workflows — progressive disclosure, concept scaffolding, comprehension checks. For bots that onboard or train users.

## Teaching Patterns

### 1. Progressive Disclosure
Start simple, add complexity as understanding grows:

```
Level 1: Core concept (what it is)
Level 2: Basic usage (how to use it)
Level 3: Advanced patterns (when to use it)
Level 4: Edge cases (what can go wrong)
```

### 2. Concept Scaffolding
Build new knowledge on existing foundations:

```
Prerequisite → New Concept → Application → Mastery
     ↓              ↓             ↓            ↓
  "You know X"  "Now add Y"  "Use XY for Z"  "You've learned!"
```

### 3. Comprehension Checks
Verify understanding before advancing:

```
Check 1: Recall — "What is X?"
Check 2: Application — "How would you use X to solve Y?"
Check 3: Analysis — "Why does X work better than Z for this case?"
```

## Teaching Templates

### Concept Explanation
```
## [Concept Name]

**What it is:** One sentence definition

**Why it matters:** Practical benefit

**How it works:** Step-by-step breakdown

**Example:**
[Code or walkthrough]

**Your turn:** [Practice exercise]
```

### Tutorial Structure
```
## Tutorial: [Topic]

### Prerequisites
- What you need to know first

### Steps
1. [Step 1 with explanation]
2. [Step 2 with explanation]
3. ...

### Checkpoint
- [Comprehension question]

### Next Steps
- Where to go from here
```

### Troubleshooting Guide
```
## Problem: [Symptom]

### Possible Causes
1. [Cause 1] — Most likely
2. [Cause 2] — Less common
3. [Cause 3] — Rare

### Solutions
For each cause:
- [Solution with steps]

### Prevention
- [How to avoid this in the future]
```

## Adaptive Teaching

### Skill Level Detection
```python
def assess_skill(user_input):
    if any(term in user_input.lower() for term in ['beginner', 'new to', 'first time']):
        return 'beginner'
    elif any(term in user_input.lower() for term in ['advanced', 'expert', 'optimize']):
        return 'advanced'
    return 'intermediate'
```

### Pacing Adjustment
- **Beginner:** More explanations, simpler examples, more checkpoints
- **Intermediate:** Balanced explanation/practice, real-world examples
- **Advanced:** Concise, edge cases, optimization focus

## Quality Checklist
- [ ] Start with clear learning objective
- [ ] Build on existing knowledge
- [ ] Include hands-on practice
- [ ] Provide comprehension checks
- [ ] Offer next steps for continued learning