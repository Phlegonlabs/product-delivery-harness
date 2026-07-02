# Foundation Notes

Sources:

- OpenAI Codex manual: https://developers.openai.com/codex/codex-manual.md
- Codex Goal mode: https://developers.openai.com/codex/prompting#goal-mode
- Codex skills: https://developers.openai.com/codex/skills
- Codex automations: https://developers.openai.com/codex/app/automations
- OpenAI Harness Engineering: https://openai.com/index/harness-engineering/
- Addy Osmani, Loop Engineering: https://addyosmani.com/blog/loop-engineering/
- Sonar, loop engineering verification: https://www.sonarsource.com/blog/loop-engineering-without-verification-is-just-automation/
- Martin Fowler, Harness Engineering memo: https://martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html

These links are provenance only. Do not browse them unless current product behavior, source wording, or missing context matters.

## Codex Facts

- Goal mode uses the goal text as both the starting prompt and the completion criteria.
- Good goals include a specific outcome, measurable target, or test criteria.
- Codex performs better when prompts include context, constraints, reproduction or validation steps, and "done when" criteria.
- Skills package reusable workflows; Codex loads the full `SKILL.md` only after selecting the skill.
- Automations can use skills. Use thread automations when recurring work must preserve thread context; use standalone/project automations when runs should be independent.

## Loop And Harness Facts

- Loop engineering is the bounded cycle that keeps an agent moving toward a measurable objective.
- Harness engineering is the environment around the agent: context, tools, constraints, tests, observability, CI, state, and review gates.
- A reliable loop has a heartbeat, isolated workspace, task context, durable state, budget, stop condition, and verification gate.
- Deterministic checks are the hard halt: tests, linters, typechecks, static analysis, browser checks, reproducible scripts, or CI.
- LLM review can find issues, but it should not be the only final verifier for high-impact changes.

## Verification Ladder

1. Define or reproduce the observable target.
2. Identify the smallest deterministic check.
3. Add focused regression coverage when changing behavior.
4. Run broader checks after the focused check passes.
5. Record commands, exit codes, screenshots, logs, or artifacts.
6. Stabilize flaky fixtures, seeds, and environments before trusting the loop.
7. If deterministic checks are impossible, use structured review and name residual risk.
