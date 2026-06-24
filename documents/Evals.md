# Evals

"Evals" is short for evaluations. In the AI world, an eval is a structured test you run against a language model (or AI system) to measure how well it performs on a specific task or behavior. Think of it as QA testing, but for AI outputs instead of software functions.

Just like you'd write test cases to check if an API returns the right response, you write evals to check if a model gives the right answer — or at least a good one.

---

# AI Evals — Beginner's Guide

A complete guide to understanding AI evaluations (evals) from scratch.

---

## Table of Contents

1. [What are evals?](#what-are-evals)
2. [Why do we need evals?](#why-do-we-need-evals)
3. [The 4 parts of an eval](#the-4-parts-of-an-eval)
4. [Types of evals](#types-of-evals)
5. [How grading works](#how-grading-works)
6. [The eval loop](#the-eval-loop)
7. [Key concepts and terminology](#key-concepts-and-terminology)
8. [Common mistakes beginners make](#common-mistakes-beginners-make)
9. [Popular eval frameworks and tools](#popular-eval-frameworks-and-tools)
10. [Evals vs traditional unit tests](#evals-vs-traditional-unit-tests)

---

## What are evals?

Evals is short for evaluations.

An eval is a structured test you run against an AI model (like Claude or GPT) to measure how well it performs on a specific task or behavior.

Think of it like QA testing — but instead of testing if a function returns the right value, you're testing if an AI gives the right answer.

> **Simple definition:** An eval = a question you give the AI + a way to check if the answer is good.

---

## Why do we need evals?

With regular software, you can write a test like:

```javascript
expect(add(2, 3)).toBe(5); // always passes or fails clearly
```

But with AI, you can't do that. If you ask an AI to summarize an article, it might give you a perfectly correct summary — just in different words every time. You can't use `===` to check natural language.

Evals solve this by giving you a repeatable, systematic way to measure AI quality — so you can:

- Know if your AI is getting better or worse after changes
- Compare two different models or prompts
- Catch regressions before shipping to users
- Make decisions based on data, not gut feeling

---

## The 4 parts of an eval

Every single eval case has exactly 4 parts:

### 1. Input

What you send to the AI — the prompt or user message.

```
"Summarize this in one sentence:

NASA's James Webb Space Telescope captured images of a 
star-forming region 1,300 light-years away, revealing 
thousands of never-before-seen young stars."
```

### 2. Expected output (gold standard)

What a correct answer looks like. Written by a human when building the dataset.

```
"The James Webb Space Telescope photographed a star-forming 
region 1,300 light-years away, revealing thousands of 
previously unseen young stars."
```

### 3. Grader

The logic that compares the AI's actual answer to the expected answer and decides if it's good. (More on grading below.)

### 4. Score

The final result — pass/fail, 1–5 rating, or 0–1 number. Aggregated across many test cases to get your overall model score.

---

## Types of evals

### Functional evals — Does it do the task?

Tests whether the AI can complete the job correctly.

Examples:
- Summarize this article
- Extract the phone number from this text
- Classify this review as positive or negative
- Answer this customer support question

### Safety evals — Does it misbehave?

Tests whether the AI produces harmful, wrong, or dangerous outputs.

Examples:
- Does it refuse harmful requests?
- Can it be jailbroken with tricky prompts?
- Does it handle edge cases without crashing?

### Quality evals — Is it actually good?

Tests whether the AI output is high quality, not just technically correct.

Examples:
- Is the tone appropriate?
- Is it factually accurate?
- Is it helpful and clear?
- Which prompt version is better? (A/B testing)

---

## How grading works

Grading is the hardest part of evals. Here are the main approaches from simplest to most powerful:

### Exact match

```
output === expected
```

Works for structured outputs like yes/no, JSON fields, or class labels.
Breaks on anything where phrasing can vary.

### Keyword / regex check

```
output.includes("James Webb") && output.includes("stars")
```

Good for extraction tasks where you just need to verify key information is present.

### LLM-as-judge (most widely used)

You send the AI's output to another LLM (like Claude or GPT) and ask it to score it based on a rubric.

```
Prompt to judge model:
"Here is a reference answer: [expected]
Here is the model's answer: [actual]
Does the model's answer correctly capture the same meaning? 
Score 1-5 and explain why."
```

Fast, flexible, scales to thousands of test cases. Most eval frameworks use this approach.

### Human annotation

Real humans rate the responses. The most accurate method but expensive and slow. Usually used to build the initial dataset, not to grade every run.

---

## The eval loop

Evals aren't a one-time thing — they're a loop you run continuously:

```
1. Build dataset     →  collect real input examples + write gold answers
        ↓
2. Run evals         →  send inputs to your model, collect outputs
        ↓
3. Score results     →  run grader, calculate accuracy/quality scores
        ↓
4. Analyze failures  →  look at which cases failed and why
        ↓
5. Fix prompt        →  update your prompt or fine-tune the model
        ↓
6. Repeat            →  run evals again to see if score improved
```

This is identical to a CI/CD pipeline in software engineering — you run tests every time you make a change to make sure you didn't break anything.

---

## Key concepts and terminology

| Term | What it means |
|------|---------------|
| Eval case | One single test — one input + one expected output + one score |
| Eval suite | Your full collection of test cases for a capability |
| Eval run | One execution of the entire suite against a model |
| Grader / evaluator | The logic that scores the AI's output |
| Gold standard | The reference "correct" answer written by a human |
| LLM-as-judge | Using an AI model to grade another AI model's outputs |
| Benchmark | A public, standardized eval dataset used to compare models fairly |
| Custom eval | An eval you build yourself for your specific use case |
| Regression | When a change breaks something that was previously working |
| Coverage | How many different scenarios your eval dataset covers |

---

## Common mistakes beginners make

### 1. Starting without a dataset
Don't write grading logic first. Start by collecting 20–50 real examples of inputs your system needs to handle. The dataset IS the eval.

### 2. Only testing the happy path
Easy examples will all pass. Evals earn their value on edge cases: empty inputs, ambiguous phrasing, non-English text, adversarial prompts.

### 3. Trusting one aggregate score
A model with 72% accuracy isn't automatically worse than one with 78%. Look at which cases failed — the breakdown matters more than the number.

### 4. Not versioning your eval datasets
If you keep editing your test cases, scores over time become incomparable. Treat your dataset like code — version control it.

### 5. Confusing eval score with real-world performance
A model can score 90% on your eval suite and still fail in production if your test cases don't reflect real user behavior. Feed real production examples back into your eval set over time.

---

## Popular eval frameworks and tools

| Tool | What it's for |
|------|---------------|
| Anthropic Evals | Anthropic's internal framework; used heavily for safety red-teaming |
| OpenAI Evals | Open-source framework; supports LLM-as-judge and custom graders |
| Braintrust | SaaS platform for logging, scoring, and managing eval datasets |
| LangSmith | LangChain's eval + tracing platform, great for agent pipelines |
| Promptfoo | CLI-first tool for comparing prompts side-by-side |
| Ragas | Specialized for RAG pipeline evaluation (retrieval + generation) |

---

## Evals vs traditional unit tests

| | Traditional unit test | AI eval |
|--|----------------------|---------|
| Input | Fixed function argument | A prompt or user message |
| Expected output | Exact value | A rubric, range, or reference answer |
| Grader | `===` or `toBe()` | LLM-as-judge, regex, or human rating |
| Result | Pass / Fail (binary) | Score (0–1, 1–5, etc.) |
| Deterministic? | Yes — always the same | No — model outputs vary |
| When to run | Every code change (CI) | Every prompt or model change |

The spirit is the same — check that your system behaves correctly. The mechanics are different because language is fuzzy and AI outputs are probabilistic.

---

*Documentation written by Roja Shuruthika Kathiravan*

*Last updated: June 2*
