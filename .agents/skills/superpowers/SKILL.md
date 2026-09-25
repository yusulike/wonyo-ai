---
name: superpowers
description: >
  Core software engineering rigor and discipline framework by obra/superpowers.
  Enforces TDD-first (test before implementation), systematic debugging (no guessing,
  root-cause tracing), verification-before-completion (evidence before assertions),
  and disciplined planning. Use whenever the user mentions "superpowers", asks for
  rigorous engineering, or tackles complex architectural or financial/quant tasks.
license: MIT
---

# Superpowers: Rigorous Software Engineering Framework

Superpowers provides institutional-grade engineering discipline for AI agents.
It replaces speculative, sloppy coding with systematic verification and hard quality gates.

## Core Tenets

1. **Test-Driven Development (TDD First)**
   - Never write production code before writing an automated test that fails for the right reason.
   - Flow: **RED** (write failing test) → **GREEN** (minimal code to pass) → **REFACTOR** (clean up while tests stay green).
   - Delegated skill: `test-driven-development`

2. **Systematic Debugging (Zero Guesswork)**
   - Never make speculative fixes or patch symptoms.
   - Always reproduce the issue in an isolated test first.
   - Trace the exact data flow and schema backwards to identify the root cause.
   - Delegated skill: `systematic-debugging`

3. **Verification Before Completion**
   - Never claim a task, fix, or feature is working without fresh, empirical command output proving it.
   - Hard Evidence > Optimistic Assertions.
   - Delegated skill: `verification-before-completion`

4. **Disciplined Architecture & Planning**
   - For multi-step or architectural tasks: Explore intent → Brainstorm approaches → Write specification doc → Write implementation plan → Execute step-by-step.
   - Delegated skills: `brainstorming`, `writing-plans`, `executing-plans`

## The Superpowers Suite Reference

When active, Superpowers coordinates the following specialized skills in `.agents/skills/`:
- `using-superpowers`: Primary workflow dispatch and gatekeeper
- `test-driven-development`: Red-Green-Refactor execution
- `systematic-debugging`: 4-phase bug investigation
- `verification-before-completion`: Pre-commit proof verification
- `brainstorming`: Collaborative design and intent discovery
- `writing-plans`: Step-by-step engineering implementation plans
- `executing-plans`: Rigorous batch or subagent execution
