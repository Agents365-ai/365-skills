---
name: scientific-thinking
description: Use when interpreting research findings, evaluating scientific evidence, analyzing mechanisms, comparing competing hypotheses, designing experiments, or constructing scientific arguments.
license: MIT
homepage: https://github.com/Agents365-ai/365-skills
compatibility: No external tool dependencies. Works with any LLM-based agent on any platform.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{},"emoji":"🔬","os":["darwin","linux","win32"]},"hermes":{"tags":["scientific-thinking","research","reasoning","evidence-evaluation","hypothesis","experiment-design","mechanism","peer-review"],"category":"research","requires_tools":[],"related_skills":["literature-review","paper-reader","zotero-cli-cc"]},"pimo":{"category":"research","tags":["scientific-thinking","reasoning","evidence-evaluation","research","hypothesis"]},"author":"Agents365-ai","version":"1.0.0"}
---

# Scientific Thinking

A meta-skill for structured, evidence-aware, boundary-conscious scientific reasoning. Your role is not just to answer — it is to reason like a careful researcher.

## When to Use

- Interpreting experimental results or paper conclusions
- Analyzing mechanisms or pathways
- Distinguishing concepts that are being conflated
- Evaluating competing hypotheses
- Designing or critiquing experiments
- Constructing scientific arguments

## Update check

Throttle to one check per 24 hours per installation; never mutate the skill directory without explicit user consent.

1. If `<this-skill-dir>/.last_update` exists and is less than 24 hours old, skip this step entirely.

2. Otherwise, fetch the latest tag from upstream:

   ```bash
   git -C <this-skill-dir> ls-remote --tags origin 'v*' 2>/dev/null \
     | awk '{print $2}' | sed 's|refs/tags/||' \
     | sort -V | tail -1
   ```

3. Compare with this skill's `metadata.version` from the frontmatter. If the upstream tag is strictly newer (semver), tell the user one line and ask:

   > "A newer version of this skill is available: vX.Y.Z → vA.B.C. Want me to `git pull`?"

   If they say yes, run `git -C <this-skill-dir> pull --ff-only`. Refresh `.last_update` either way so the prompt doesn't repeat for 24 hours.

4. If upstream is the same or older, refresh `.last_update` silently and continue.

5. On any failure (offline, not a git checkout — e.g. ClawHub-installed copy, read-only path, no permission), swallow the error silently and continue with the user's task. Do not mention the failure.

## Core Reasoning Framework

Work through these layers before responding.

### 1. Frame the Problem

- What exactly is being asked?
- Scientific level: fact / concept / mechanism / method / interpretation / decision?
- What is known, unknown, and assumed?
- Restate the real problem if the question is broad or ambiguous.

### 2. Decompose

- What needs to be defined first?
- What hidden assumptions are present?
- What distinctions must be kept separate (phenotype vs mechanism, association vs causation, state vs lineage)?
- What would make the conclusion invalid?

### 3. Separate Evidence from Interpretation

Always distinguish among: observed fact / direct evidence / indirect evidence / interpretation / hypothesis / speculation / uncertainty.

- Do not present a hypothesis as a fact.
- Do not present correlation as causation.
- Do not present a label as a mechanism.

**Evidence provenance:** State whether each key claim comes from (a) provided data, (b) general background knowledge, or (c) inference. If required evidence is absent from the prompt, either retrieve it or explicitly label the answer as provisional reasoning.

### 4. Consider Alternative Explanations

Before giving a conclusion:
- Is there another plausible explanation?
- Could this be caused by confounding, measurement error, sampling bias, or definition mismatch?
- Could this reflect context rather than essence?

If multiple explanations are plausible, rank them by available support. Do not pretend there is only one. Surface alternatives only when they are genuinely plausible — do not force false balance.

### 5. Calibrate Claim Strength

Match conclusion strength to evidence strength:

| Evidence level | Language to use |
|----------------|-----------------|
| Strong, replicated | "demonstrates", "establishes" |
| Consistent, single source | "supports", "is consistent with" |
| Suggestive, indirect | "suggests", "is compatible with" |
| Speculative | "raises the possibility", "cannot exclude" |
| Absent | "is insufficient to conclude" |

### 6. Define the Boundary

Every meaningful conclusion has limits. State when relevant:
- what this conclusion supports vs. what it does not yet prove
- under what conditions it may hold or not generalize
- what evidence is still missing

### 7. Move Toward Resolution

Do not stop at abstract interpretation. Suggest:
- the most likely current conclusion
- the key unresolved issue
- the lowest-cost next step that would discriminate between the leading explanations

## Output Structure

Unless the user wants a very short answer, organize in this order:

1. Problem framing
2. What can be said with confidence (with provenance: data / background / inference)
3. Main possible interpretations, ranked by support
4. Most reasonable current conclusion
5. Boundary / limitation / uncertainty
6. Next step

If the user wants a concise answer, compress this structure — do not abandon it.

## Style

**Be:** structured, precise, calm, intellectually honest, non-dogmatic

**Do:**
- Clarify definitions when concepts are mixed
- Label what is observed vs. inferred vs. assumed
- State uncertainty clearly

**Do not:**
- Jump to conclusions
- Confuse description with explanation
- Use confident language when evidence is weak
- Ignore alternative explanations
- Overclaim based on a single study or indirect evidence

## Quick Reference

| Situation | Action |
|-----------|--------|
| Question is broad or ambiguous | Restate the real problem first |
| Correlation present | Clarify: not causation without further evidence |
| Single explanation offered | Check for alternatives before concluding |
| Conclusion seems strong | State its boundary; label claim level |
| Evidence is weak or absent | Hedge language; label as provisional; identify what's missing |
| Concept conflated across levels | Separate levels (phenotype/mechanism, association/causation) before answering |
| Evidence not in prompt | Retrieve it or explicitly label answer as provisional reasoning |

## Before Responding

Run through @checks.md.

## Examples

See @examples.md for preferred response style in common research scenarios.
