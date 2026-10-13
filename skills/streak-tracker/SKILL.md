---
name: streak-tracker
description: Track daily completion streaks for any activity, with optional weekly freeze days that protect a streak after missed days. Use when the user asks to start, update, check, reset, or configure a streak, including a quiz, study, exercise, reading, or other habit streak.
---

# Streak Tracker

Track whether the user completed a named activity each day. A streak is about showing up, not quality or outcome. Be factual and encouraging; never guilt-trip.

## Setup and storage

If no tracker exists, ask in one short message:
1. What activity should the streak track?
2. Where should the progress file live? Suggest a suitable folder and use the user's chosen path.
3. How many weekly freeze days should it have: 0, 1, or 2? A freeze automatically covers one missed day.

Save progress in `streak-tracker.md` in the chosen folder. Create parent folders as needed. Tell the user the full file path. Keep using that file for this activity unless the user changes the path or tracked activity. Never keep progress only in conversation memory.

Use this format:

```text
activity: <named activity>
freezes_per_week: <0|1|2>
current: <N>
best: <N>
last_day: YYYY-MM-DD | never
freezes_left: <N>
freeze_week: <YYYY-Www>
```

Initialize `current` and `best` to 0, `last_day` to `never`, and `freezes_left` to the configured allowance. Set `freeze_week` to the current ISO week. Use the user's local date. A day counts when the user says they completed the activity; merely planning, being reminded, or receiving a quiz does not count. For a quiz streak, answering the quiz counts regardless of whether the answer is correct.

## Record a completion

When the user reports completing the tracked activity, update at most once per local day:
- If `last_day` is today, leave the counts unchanged.
- If `last_day` is `never`, set `current` to 1.
- Otherwise calculate `missed` as the calendar days between `last_day` and today, minus 1. If `missed` is 0, increment `current` by 1.
- At the start of a new ISO week, refill `freezes_left` to `freezes_per_week` and update `freeze_week`.
- If days were missed and `freezes_left >= missed`, spend that many freezes and increment `current` by 1. Missed days do not add to the streak. Say how many freezes were used and how many remain this week.
- If days were missed and there are not enough freezes, reset `current` to 1. Do not spend freezes.
- Set `best` to the greater of its existing value and `current`, and set `last_day` to today.

Report the current streak and best when useful. If it just restarted after a previous run of at least 3 days, say so kindly. Mention freeze use plainly; do not mention freezes when `freezes_per_week` is 0.

## Other requests

- **Check:** Read the file and report the current streak, best, and remaining freezes.
- **Reset:** Set `current` to 0 and `last_day` to `never`; keep the best and freeze settings unless asked otherwise.
- **Change freezes:** Set `freezes_per_week` to 0, 1, or 2. Refill the weekly allowance to the new setting and set `freeze_week` to the current ISO week.
- **Change activity or location:** Confirm the new setting and preserve the existing tracker data unless the user asks to reset it.

If the file is missing or malformed, ask only for the information needed to repair it. Do not silently invent past activity or streak values.