# Harbor — Engineering Decision Guidelines

These principles govern how decisions are made in this project.
They are about **how to think**, not what to build.

---

## Fact-First Debugging

When something breaks:

1. **Observe** — Read the actual error from logs, not from the user's description. The user sees a symptom; the log shows the cause.
2. **Reproduce** — Confirm the error is reproducible. If you can't reproduce it, you don't understand it yet.
3. **Diagnose** — Trace the request path end-to-end. Identify which component produced the error. Don't touch code until you know which component is at fault.
4. **Fix** — Change exactly one thing. Verify the fix resolves the error. If it doesn't, revert and go back to step 1.

**Never skip straight to step 4.** Guessing at fixes without evidence wastes time and introduces new bugs.

---

## Architecture-First Design

Every change must be evaluated against the full system, not just the local component.

- Before adding a new endpoint, ask: does this belong in the API layer, or should it be a separate Lambda?
- Before adding a new dependency, ask: does this violate the layered architecture (API → Service → Store)?
- Before changing a data model, ask: what downstream consumers will break?
- Before choosing a protocol or port, ask: what does the target runtime actually require? Check the documentation, don't assume.

**Local optimizations that break global invariants are bugs, not features.**

---

## Deployment Completeness

A feature is not done until it works end-to-end in the deployed environment.

- CDK deploy with all required context parameters
- Environment variables set correctly on all Lambdas
- Frontend built with correct environment (`.env.production`)
- CloudFront invalidation after S3 sync
- IAM permissions covering all resource ARN patterns (not just the obvious ones)

**If a deploy step is manual, document it. If it's easy to forget, automate it.**

---

## Documentation Accuracy

Documentation must reflect the actual deployed system, not the intended design.

- If the code changed, update the docs in the same commit.
- Architecture docs describe what IS, not what SHOULD BE.
- Steering files describe principles, not specific bugs or solutions.
- README demos use actual CLI output, not fabricated examples.
