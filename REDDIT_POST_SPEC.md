# Reddit Post Spec

This document defines the target format for the daily Reddit post generated from the arXiv popularity tracker output.

## Goal

Produce **one daily roundup post** for **r/MachineLearning** based on papers that:
- appeared in Hugging Face daily papers
- were selected by the tracker as strong candidates
- have deconstructedpapers.com breakdown links available

The post should feel like a human-curated roundup, not an automated spam dump.

## Subreddit

Always post to:
- `r/MachineLearning`

Do not generate multiple subreddit variants.

## Daily Count

Include:
- **3 to 5 papers** per post

If fewer than 3 good papers qualify, it is acceptable to emit fewer rather than pad the post with weak picks.

## Title Format

The title should center the fact that breakdowns were generated.

Preferred title pattern:
- `I generated breakdowns for {N} Hugging Face daily papers today`

Examples:
- `I generated breakdowns for 4 Hugging Face daily papers today`
- `I generated breakdowns for 5 Hugging Face daily papers today`

## Intro

Preferred intro text:

`I went through today’s Hugging Face daily papers and generated breakdowns for the ones that seemed most worth reading.`

Notes:
- Keep the intro short.
- Focus on the breakdowns as the value add.
- Do not sound overly formal or overly promotional.

## Per-Paper Format

Each paper should use this exact structure:

```text
1. Paper Title
Why it stood out: short, casual sentence or fragment.
arXiv: <arxiv link>
Breakdown: <deconstructedpapers link>
```

Example:

```text
1. MegaTrain: Full Precision Training of 100B+ Parameter Large Language Models on a Single GPU
Why it stood out: getting real attention today.
arXiv: https://arxiv.org/abs/2604.05091
Breakdown: https://www.deconstructedpapers.com/s/PXivKgm2
```

## Tone for “Why it stood out”

The line should be:
- casual
- human
- lightly opinionated
- specific when possible
- allowed to be a partial sentence

It should **not** sound like raw scoring output.

### Good examples
- `getting real attention today.`
- `feels genuinely useful, not just flashy.`
- `practical enough that people might actually use it.`
- `one of the cleaner ideas in today’s batch.`
- `not new-new, but still very relevant.`
- `people seem to actually care about this one.`
- `less hypey than most, more useful than most.`
- `worth a look if you care about inference efficiency.`

### Avoid
- `strong multi-source momentum signal`
- `balanced signals across sources`
- `well-starred repo with citations`
- `this work delves into`
- `this paper showcases`
- anything that sounds like marketing copy or model-written filler

## Link Order

Always place the links in this order:
1. `arXiv:`
2. `Breakdown:`

Rationale:
- arXiv first makes the post feel paper-first
- the breakdown reads as an optional helpful extra rather than a bait link

## Disclaimer

End every post with this disclosure line:

`Disclosure: I run deconstructedpapers.com. These breakdowns are free — just sharing them in case they’re useful.`

Notes:
- Keep the disclosure at the end of the post.
- Do not hide affiliation.
- Do not over-explain.

## Full Template

```text
I went through today’s Hugging Face daily papers and generated breakdowns for the ones that seemed most worth reading.

1. Paper Title
Why it stood out: short casual reason.
arXiv: <arxiv link>
Breakdown: <deconstructedpapers link>

2. Paper Title
Why it stood out: short casual reason.
arXiv: <arxiv link>
Breakdown: <deconstructedpapers link>

3. Paper Title
Why it stood out: short casual reason.
arXiv: <arxiv link>
Breakdown: <deconstructedpapers link>

Disclosure: I run deconstructedpapers.com. These breakdowns are free — just sharing them in case they’re useful.
```

## Example

```text
I went through today’s Hugging Face daily papers and generated breakdowns for the ones that seemed most worth reading.

1. MegaTrain: Full Precision Training of 100B+ Parameter Large Language Models on a Single GPU
Why it stood out: getting real attention today.
arXiv: https://arxiv.org/abs/2604.05091
Breakdown: https://www.deconstructedpapers.com/s/PXivKgm2

2. LlamaFactory: Unified Efficient Fine-Tuning of 100+ Language Models
Why it stood out: feels genuinely useful, not just interesting in theory.
arXiv: https://arxiv.org/abs/2403.13372
Breakdown: https://www.deconstructedpapers.com/s/PoNNgLc3

3. OpenHands: An Open Platform for AI Software Developers as Generalist Agents
Why it stood out: ambitious idea, and people seem to actually be building around it.
arXiv: https://arxiv.org/abs/2407.16741
Breakdown: https://www.deconstructedpapers.com/s/CHw0cWKE

4. Efficient Memory Management for Large Language Model Serving with PagedAttention
Why it stood out: not new-new, but still one of the most useful papers in this area.
arXiv: https://arxiv.org/abs/2309.06180
Breakdown: https://www.deconstructedpapers.com/s/yMQ2YoM7

Disclosure: I run deconstructedpapers.com. These breakdowns are free — just sharing them in case they’re useful.
```

## Non-Goals

This spec does not define:
- automatic Reddit posting
- subreddit diversification
- cross-posting behavior
- title A/B testing

Those can be handled separately if needed.
