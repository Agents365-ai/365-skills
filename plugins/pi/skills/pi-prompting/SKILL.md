---
name: pi-prompting
description: Internal guidance for composing prompts that Pi runs (DeepSeek by default) handle reliably for coding, review, diagnosis, and research tasks
user-invocable: false
---

# Pi Prompting

Use this skill when `pi:pi-rescue` needs to ask Pi for help on a non-trivial coding or investigation task.

Pi runs whatever model the user has configured. By default this plugin targets DeepSeek V4 (Pro for review, Flash for everyday tasks). The guidance below assumes the prompt may run on either a non-reasoning model (Flash) or a reasoning model (Pro). Bias toward concrete, numbered checklists rather than abstract instructions — both model classes follow those reliably.

Core rules:
- Prefer one clear task per Pi run. Split unrelated asks into separate runs.
- Tell Pi what done looks like. Do not assume it will infer the desired end state.
- State explicit grounding rules whenever an unsupported guess would degrade quality.
- Use stable XML-style tag blocks so the prompt has obvious internal structure.
- Keep prose short. Prefer numbered checklists over paragraphs for procedural work.

Default prompt recipe:
- `<task>`: the concrete job and the relevant repository or failure context. Include file paths.
- `<output_contract>` (or `<structured_output_contract>` for JSON): exact shape, ordering, and brevity requirements.
- `<grounding_rules>`: required for review, research, or anything that could drift into unsupported claims.
- `<action_safety>`: required for write-capable tasks — name the directories and file kinds Pi may touch.

When to add extra blocks:
- Coding or debugging: add `<completeness_contract>` listing what counts as "done" (tests pass, lint clean, files touched).
- Review or adversarial review: rely on the shipped `prompts/adversarial-review.md` and `prompts/review.md`. Do not hand-craft another review prompt.
- Research or recommendation tasks: add a short `<sources>` block listing what Pi is allowed to consult.

How to choose prompt shape:
- Use the built-in `/pi:review` or `/pi:adversarial-review` commands when the job is reviewing local git changes. Those prompts already carry the review contract.
- Use `task` when the job is diagnosis, planning, research, or implementation and you need to control the prompt more directly.
- Use `task --resume-last` for follow-up instructions on the same Pi session. Send only the delta instruction instead of restating the whole prompt unless the direction changed materially.

Working rules:
- Prefer explicit prompt contracts over vague nudges.
- Do not raise reasoning (`--effort high`) by default — DeepSeek Flash will not benefit, and DeepSeek Pro takes longer. Tighten the prompt before escalating effort.
- For tool-heavy or long-running tasks, ask Pi for brief outcome-based progress updates inside its working notes.
- Keep claims anchored to observed evidence. If something is a hypothesis, mark it as such.

Prompt assembly checklist:
1. Define the exact task and scope in `<task>`.
2. State the output contract — JSON, bullet list, plain prose — and the maximum length.
3. Decide whether Pi should keep going on its own judgment or stop for missing high-risk details.
4. Add `<grounding_rules>` and `<action_safety>` only where the task needs them.
5. Remove redundant instructions before sending the prompt.
