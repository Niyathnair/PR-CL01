# crowdLens

**A proactive simulation environment for marketers.**

Test campaign copy against a simulated population of audience personas *before* publishing — and find out not just whether people will be offended, but what they think you said.

## The idea

Offense is not a property of text. It is a relationship between text and an audience. So the primitive isn't a classifier — it's a population of simulated readers, each with distinct values, sensitivities, and readings of context.

Most backlash isn't caused by people being offended by what you said. It's caused by people being offended by **what they think you said**. Those are different failures with different fixes:

- **Misunderstood** → the copy is ambiguous → *clarify it*
- **Controversial** → the copy is understood and rejected → *decide whether you accept that cost*

A tool that reports only "risk: 62" can't distinguish them, and therefore can't tell you what to do. crowdLens models interpretation first and reaction second.

## What it produces

Eight questions, twenty-four analysis views:

| | Question |
|---|---|
| 🧠 | What did they understand? |
| ❤️ | How did they feel? |
| ⚠️ | Why might they react badly? |
| 🎯 | Who is affected? |
| 🔍 | What exactly caused it? |
| 📊 | How does it compare to similar campaigns? |
| ✏️ | How can we fix it? |
| 🔄 | Did the fix actually work? |

## Plan

**[BacklashTest-Complete-Plan.md](BacklashTest-Complete-Plan.md)** — the complete specification: product framing, persona graph architecture, full mathematical treatment, all 24 dashboard panels, validation strategy, build phases, and an honest accounting of the risks.

## Status

Planning. Nothing implemented yet.

---

*The scoring weights in the plan are priors to be calibrated against a golden set, not validated constants.*
