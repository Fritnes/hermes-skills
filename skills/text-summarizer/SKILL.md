---
name: text-summarizer
description: Summarizes text the user provides into a short, structured summary. Use when the user asks to summarize, shorten, TL;DR, or give key points of a text, article, or notes.
---

# Text Summarizer

## Instructions

1. Read the text the user provides. If none is provided, ask them to paste it.
2. Respond in this format:

```
**TL;DR:** <one sentence>

**Key points:**
- <point 1>
- <point 2>
- <point 3>

**Action items:** <list, or "None">
```

3. Keep the whole summary under 120 words unless the user asks for more.
4. Do not add information that is not in the original text.
