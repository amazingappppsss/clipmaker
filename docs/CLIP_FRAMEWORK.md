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


## 5. The Hook Playbook (what breakout Shorts actually open with)

We pulled the 24 biggest breakout podcast-clip Shorts on YouTube from the last 3 months (vidIQ
outliers) and read the openings of the top 7:

| Short | Views | Opening | Hook type |
|---|---|---|---|
| UFC rules (3.6K-sub channel) | 6.6M | "If you could change one rule in the UFC, what would it be?" | hypothetical |
| Iced Coffee Hour | 1.8M | "What's the worst you've ever called someone out for wearing a fake watch?" | question + famous name |
| PBD Podcast | 1.6M | Quotes a provocative take, then pushes back | quote → rebuttal |
| Caleb Hammer clip | 792K | "Watching Caleb Hammer shows is the most radicalizing thing." | bold claim |
| Rogan clip | 777K | "People think I'm evil because… $28 for lunch" | confession + number |
| P1 with Matt & Tommy | 493K | "I completely agree with Lewis Hamilton…" | famous name → debate |
| One Percent Heart | 291× breakout | "…makes me feel less scared and not alone" | emotional |

**What they all share:**

- **Zero warm-up.** Every one of them starts mid-conversation.
- The first sentence is a **question or a claim**.
- Most contain a **famous name** or a **specific number**.
- They're **short**: 13–97 s, and many are under 45 s. (See §7 for the larger sample, which set our final length rules.)
- They **split opinions**, which is what drives the comments.

The AI tags every clip with the opener it uses: `question`, `hypothetical`, `bold_claim`,
`shocking_number`, `quote_rebuttal`, `confession`, `famous_name`, `story_in_motion`,
`secret_reveal`, `warning`, `call_out`, `result_first`, `emotional` or `funny`. A clip with no
real hook is tagged `none` and scores low on `hook`.

## 6. Flash-forward hooks (the "spoiler" opener)

When a clip's most curiosity-filled line sits in the middle, we show it first (2–6 s), flash a
rewind, and then play the clip from its start. Viewers stay to see how the story gets there.

The rules:

- **Tease, never spoil.** The teaser must sit strictly inside the clip, never be its first
  line, and never be its final payoff line.
- **Keep it short.** A teaser is one whole sentence of 1.5–6 s.
- **Show it's a flash-forward.** The rewind transition is visible, so we never misrepresent
  the order of what was said.
- **Skip it when the opening is already the strongest hook.**

## 7. What human editors see that AI clippers miss

**The larger sample.** We pulled 84 viral clip Shorts (200K–11M views, last 3 months) across
podcast, interview and business/money niches with vidIQ. We also reviewed what clip editors and
agencies say AI tools get wrong.

**Length.** The median is 45 s, and the middle half run 27–70 s; only half are under 45 s.
→ Clip2Easy allows 12–75 s and aims for 20–45 s. Every second past 45 costs 0.6 points.

**What wins:**

1. **Reactions beat monologues.** The top clips are exchanges: a claim met by disbelief, a
   roast and the laugh, a pushback ("Rogan Was Stunned 😭", "Theo Von Didn't Believe Him 😂",
   "He called me a lineman 😭😂", 11M views). The other person's reaction is often the payoff.
   → New hook type `reaction`. Clips are automatically extended to include the other
   speaker's quick reaction (≤ 3.5 s), so we never cut before the laugh lands.
2. **Comedy and conflict dominate** over calm advice: banter, roasts, awkward moments, heated
   disagreement, celebrity drama and shocking money numbers. A calm explanation needs a
   shocking claim or a specific number to compete.
3. **Titles are spectator captions, not essays.** 3–7 words, a name plus a reaction, one
   CAPITALIZED word, and one emoji when it fits: "The WORST Advice Paris Jackson Ever
   Received", "How Much Debt Does Stradman Have?". Never "Why Architects Should Bear Risk".
4. **Smartest, not loudest.** AI tools pick the loudest moment, cut mid-sentence, end before
   the punchline resolves, and miss inside jokes and emotional context. Editors protect the
   setup and the resolution.
5. **The strongest moment goes first.** That's our flash-forward teaser (§6).

**The editing rules editors use (these become Milestone 3, so no manual editing is needed):**

- **Visual change every 3–8 s.** Cut between speakers, or "punch in" (a 110–120% zoom) at a
  cut to hide it.
- **Jump cuts:** remove filler, false starts and long pauses (4–8 cuts per minute is typical),
  but keep the speaker's natural cadence and the hourglass pause before a reveal.
- **Captions:** big, centred low, 1–2 highlighted words per line (numbers, names, the
  emotional word), and never just mirroring every syllable in one style.
- **Emphasis:** a slight zoom on key words, and a subtle sound on cuts.
- **Framing:** 9:16 crop that follows whoever is talking, and both faces during reactions.

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
