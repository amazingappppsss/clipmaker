# The plan: stop competing with OpusClip, beat it where it's weakest

Written 2026-11-16, after an honest look at where Clip2Easy actually stands.

## The situation, without flattery

OpusClip has a team, funding and years of iteration. We have one person and an AI. A feature
race against them is a race we lose — they ship B-roll, brand kits, 25 languages, scheduling
and team seats, and we ship none of those.

But their reviews name four consistent weaknesses:

1. **Auto-reframe drifts or locks onto the wrong person on multi-speaker video.**
2. **The AI misses context, jokes and emotional beats** — it finds the setup and loses the payoff.
3. **The virality score is unproven and opaque.** No published study ties it to real views.
4. **Billing and support are their reputational problem**, not their technology.

Numbers 1 and 2 are exactly what we built for. That is not a coincidence — the framework came
from reading what editors say AI tools get wrong.

## The wedge

**Clip2Easy is the clipper for conversations with more than one person.**

Solo talking-head video is where OpusClip is strong and where our advantage is nil. Two-person
podcasts, interviews and panels are where their reframing drifts and where the payoff is
usually somebody *else's* reaction — the thing we extend the clip to catch.

Niching down is not shrinking. It is the only way a one-person product beats a funded one:
be undeniably better at one thing for one audience.

Everything below is ordered by that.

---

## Phase 0 — Prove the thesis, or kill it (this week, costs nothing)

**The whole product rests on a claim we have never tested: that we pick better moments.**

`docs/CLIP_FRAMEWORK.md` says it plainly — the 11 signal weights "are starting heuristics" to
be tuned against real data. They never were. Our validation is one clip that felt good.

Before building anything else:

- Pick 3 real two-person episodes (45–90 min).
- Run each through Clip2Easy **and** OpusClip.
- Put the clips side by side and score each pair blind on: did it start on a hook, did it keep
  the payoff, did it frame the right person, did it cut before the laugh?

**Done when:** we can say, with evidence, whether we are better, the same, or worse.

**Why this is first:** if we are worse, the roadmap below is decoration on a bad product and
the real work is the selection prompt instead. If we are better, we have the one line of
marketing copy that actually sells — and it is true.

---

## Phase 1 — Make it correctable (nothing can be charged for without this)

Our single biggest gap is not a missing feature. It is that **a wrong decision cannot be
fixed.** OpusClip's reframe drifts too, but it lets you drag the frame back. We ship whatever
the AI decided, and one bad cut makes a clip useless with no recourse.

1. **Trim handles.** Drag the start and end of a clip, re-render just that clip.
2. **Reframe nudge.** Three positions per shot — left speaker, right speaker, both — overriding
   what diarisation chose. This is also our honest answer when our own tracking is wrong.
3. **Caption text fix.** Click a word, correct it. Names and jargon are always wrong, in every
   tool, and a wrong name in big lime letters is the one error viewers notice.

**Done when:** a user can take a clip the AI got wrong and make it postable without leaving
the app.

---

## Phase 2 — Fix what we already know is broken

These are failures seen with our own eyes this session, not speculation.

1. **The box.** 953 MB RAM, 0.45 GB disk, 2 CPUs. It has OOM-killed renders, filled its disk
   and starved playback. Either pay for Railway Hobby or move to the Oracle stack already
   written in `deploy/oracle/`. Everything else is unreliable until this is settled.
2. **"It looks artificial."** The diarisation-driven framing and the slower cuts shipped, but
   were never confirmed on a real video. Phase 0 confirms or reopens this.
3. **Clips per video.** We cap at 3–12. The ask was "every video should produce many clips."
   An exhaustive mode that returns everything above the bar, ranked, with the top picks marked.
4. **Speed.** 2–3.5 minutes, against a 60-second goal. The remaining win is folding the
   UNDERSTANDING stage into the parallel candidate calls (~34s).

---

## Phase 3 — The differentiators worth building

Only after Phase 0–2. Each of these is chosen because it widens the wedge, not because
OpusClip has it.

1. **Show the rejections in the product**, not just on the landing page. Their score is
   criticised as opaque; ours can be the one that shows its work. "Here are the 40 moments we
   threw away and why" is a feature nobody else offers.
2. **Caption styles.** We have exactly one look. Three or four, plus a colour, is enough — we
   do not need brand kits.
3. **Learn from downloads.** Which clips a creator actually downloads and posts is free
   training signal for the weights that are currently guesses. This is how the score stops
   being heuristic.

---

## Phase 4 — Business, once the product earns it

- **Email domain.** The waitlist can only mail the owner's own address until a domain is
  verified. Everything else about email is built and live.
- **Billing.** Paddle or Lemon Squeezy. Their billing is the thing people complain about most
  — being simple and honest here is a real advantage, cheaply won.
- **Google login** or a proper sender before any public launch.

---

## What this plan deliberately does not do

- **No B-roll.** Reviews report OpusClip inserting beach footage into a revenue discussion.
  Doing it badly is worse than not doing it.
- **No 25 languages.** English-first until the wedge is proven.
- **No scheduling, no teams, no brand kits.** These are features of a company with a team.

## The one-line version

Prove we pick better moments on two-person video. Make our mistakes fixable. Fix the box.
Then widen the lead, and only then build a business on top.
