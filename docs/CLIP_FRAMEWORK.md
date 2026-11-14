# The Clip2Easy Framework: STOP · STAY · SHARE + the Story Layer

This is the rulebook Clip2Easy's AI editor follows to pick, cut and package every clip. It is
the source of truth for `backend/src/clipmaker/pipeline/prompts.py` (what the AI is told) and
`pipeline/selection.py` (how its ratings become decisions). Change the rules here first.

It is our own synthesis, written in our own words, drawn from:

- **YouTube's three laws for creators**: "If they don't click, they don't watch." "Respect
  their time." "Make them want more."
- **Short-form creator practice** (the transcripts in our research notes): the 3-second hook,
  demographic call-outs, curiosity gaps, "you're the character" stakes, step-by-step reveals,
  comment-sparking takes, and the swipe-rate and retention targets that predict virality.
- **Claude C. Hopkins, *Scientific Advertising*** (1923): headlines that pick out the right
  person, curiosity as the strongest incentive, specific claims beating superlatives, telling
  the full story once you have attention, positive over negative, sincerity over cleverness,
  and test everything.
- **Matthew Dicks, *Storyworthy***: a story is something that *changed* someone; the
  five-second moment; begin where the ending needs you to; BUT/THEREFORE; stakes devices
  (elephants, backpacks, breadcrumbs, hourglasses, crystal balls); vulnerability; cinema of
  the mind; and endings that are earned.
- **John Truby, *The Anatomy of Story***: desire, weakness, opponent and self-revelation as
  the spine of a story.
- **Jonah Berger, *Contagious***: people share what makes them look good, what triggers
  high-arousal emotion, and what is genuinely useful.
- **Chip & Dan Heath, *Made to Stick***: simple, unexpected, concrete, credible, emotional,
  story.

---

## 1. STOP: win the first 3 seconds

*If they don't stop, they never watch.* The first sentence is the headline (Hopkins).

- It works on its own: a bold or contrarian claim, a specific number, a question the viewer
  wants answered, a surprising contrast, or a call-out ("If you're 25 and…").
- It hails the right viewer: people who care should feel "this is for me".
- No warm-up: never open on "so", "um", "great question" or "as I said".
- Open a curiosity loop that the clip closes later, not in the first line.

**Signals:** `hook`, `curiosity_gap`.

## 2. STAY: respect their time

*Every sentence must earn the next one.*

- Deliver what the opening promised, quickly.
- **Stakes:** it's about the viewer (money, career, health, status), or there's real tension.
- **Specific beats general:** numbers, names and real examples hold attention, while "work
  hard" loses it (Hopkins ch. 7, Made to Stick).
- **Momentum:** the idea unfolds step by step; there's no dead weight.
- **Emotion:** laughter, awe, anger, surprise, vulnerability and inspiration. Never miss the
  funny or emotional moments, which is OpusClip's most common complaint.

**Signals:** `stakes`, `specificity`, `momentum`, `emotion`.

## 3. SHARE: make them want more

- **Payoff:** end on the reveal, the punchline or the insight. Never end on a setup.
- **Share trigger:** would someone send it to a friend, repost it to look smart or funny, or
  argue about it (Contagious)?
- **Bright side:** what's possible beats doom, because positive outpulls negative (Hopkins
  ch. 18).
- **Standalone:** it makes complete sense to a stranger.

**Signals:** `payoff`, `share_trigger`, `standalone`.

## 4. The Story Layer (Storyworthy + Truby)

*Search for meaningful moments, not interesting sentences.*

- **Change is the story.** An event without change is an anecdote. Ordinary events with real
  internal change beat dramatic events without it.
- **The five-second moment** is the instant of realization or turn. The AI must quote it
  exactly.
- **Before → after:** the AI names the speaker's starting and ending states. The distance
  between them is the power.
- **Begin where the ending needs it:** start close to the conflict, but never cut the setup
  that makes the payoff land.
- **BUT / THEREFORE, never "and then":** consequence creates momentum.
- **Stakes devices already in the talk** are gold: the problem stated early, what the speaker
  had riding on it, foreshadowing, and expectation vs. reality.
- **Vulnerability and cinema of the mind:** admissions and concrete scenes beat polish and
  abstractions.
- **Not every clip is a story.** A sharp insight or a joke can win on STOP · STAY · SHARE
  alone, so transformation is weighted, not required.

**Signals:** `transformation`, `causality`. **Extra outputs:** `five_second_moment`,
`before_state`, `after_state`, `missing_context`.

---

## Scoring

The model rates 11 signals from 0 to 10, strictly: a typical moment scores 4–6. The final
score (0–100) is a weighted sum, configurable through `SCORE_WEIGHTS_JSON`:

| Signal | Weight | | Signal | Weight |
|---|---|---|---|---|
| hook | 0.15 | | transformation | 0.10 |
| curiosity_gap | 0.08 | | causality | 0.06 |
| stakes | 0.08 | | payoff | 0.12 |
| specificity | 0.07 | | share_trigger | 0.06 |
| momentum | 0.06 | | standalone | 0.12 |
| emotion | 0.10 | | | |

These weights are starting heuristics. Hopkins' first law is *test, don't guess*, so they will
be tuned against real retention data once creators publish (Milestone 6).

**Hard gates.** A clip that fails any of these never ships, whatever its score:

- `standalone` < 4: "needs outside context to make sense"
- `payoff` < 4: "ends without a payoff"
- `hook` < 3: "opening won't stop the scroll"

**How many clips.** "Auto" allows about one clip per 90 seconds of video, from 3 to 12. That's
a ceiling, not a quota: we show every moment that clears the quality bar (55), and top up to
3 with moments within 15 points of it, clearly marked. We'd rather show 3 bangers than 10
maybes.

## Packaging (titles, hooks, captions)

These rules come from Hopkins' chapter on headlines:

- Hail the right viewer and promise a specific benefit or answer.
- Specific beats superlative: "He paid $2,000 to wax a surfboard" beats "Crazy story!"
- Curiosity without lies: the clip must deliver what the title promises.
- Three alternative titles from three angles: curiosity, a specific claim, and an audience
  call-out.
- End captions with a genuine question when it fits, to invite comments.

## Editing rules for Milestone 3 (rendering)

- **Hook first.** When a clip's strongest line sits mid-clip, consider a cold open: that line
  first, then the clip. Never change what was said or meant.
- **Trim dead air, but keep the hourglass.** Remove "um", false starts and long silences, but
  keep a deliberate pause right before a reveal (Storyworthy's hourglass).
- **Captions** emphasise the specific words (numbers, names, the five-second moment).

## Integrity (non-negotiable)

- Never invent words, claims, names, numbers, emotions, events or outcomes.
- Never cut a moment so it misrepresents the speaker.
- Controversy is not a story, and intensity is not quality.
- Every score comes with a plain-words "why it works" grounded in the transcript.
