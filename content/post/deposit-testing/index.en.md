---
title: "Exchange Deposit Testing: From Manual Construction to a Standardized Platform"
date: 2026-02-12
description: "How I turned exchange wallet deposit testing from 'depends on who's testing' into a repeatable, standardized process — and my thoughts on fake deposit detection."
categories: ["testing"]
tags: ["blockchain", "deposit testing", "test engineering", "tooling"]
pinned: false
draft: false
---

## What Wallet Testing Really Is

Exchange wallet testing boils down to two things: **deposits** and **withdrawals**.

Sounds simple, but the complexity on the deposit side far exceeds most people's expectations. From my hands-on experience, deposit testing breaks down into four layers, each escalating in difficulty and value:

**Layer 1: Happy Path Deposits**
Standard native coin and token transfers. The most basic layer — ideally automated in CI/CD pipelines and run on every release.

**Layer 2: Edge Case Deposits**
On-chain failed transactions, contract-based deposits, zero-amount transfers, batch deposits… In past testing practice, this layer was almost entirely missing — not because we didn't want to test it, but because **the cost of constructing these transactions was prohibitively high**. Building an on-chain failed transaction requires precise gas parameter control. Building a contract deposit requires deploying and calling smart contracts. Every case heavily depends on the tester's on-chain expertise. Replace the person, and the capability disappears.

**Layer 3: Idempotency**
What happens when the same transaction is processed twice? Testers must deeply understand how deposit idempotency is implemented, why it works that way, and under what circumstances manual review must be triggered. This is as much a business comprehension challenge as a technical one.

**Layer 4: Fake Deposits**
The deep end. Previous approaches relied heavily on research docs listing known fake deposit types — but those were surface-level, conventional cases. Real fake deposit attacks hide in complex transaction structures, and missing one means a P-1 production incident.

---

## Where the Pain Is

Looking back at these four layers, the biggest pain points concentrate in the first two:

- **Extreme construction cost**: Building a single edge-case transaction on-chain could take an entire day
- **Heavy reliance on individual expertise**: Only people fluent in on-chain operations could do it — knowledge couldn't transfer
- **No standardization**: Test coverage depended entirely on the executor's experience, with no unified baseline
- **Can't scale**: Long onboarding cycles for new team members, limited team growth

One sentence: **Deposit test quality should not depend on who's doing the testing.**

---

## My Solution: deposit.bolab.dev

Based on this conviction, I built [Chain Deposit Lab](https://deposit.bolab.dev) — a multi-chain deposit testing platform.

**The core goal is singular: enable anyone — even someone with zero blockchain knowledge — to complete a standardized deposit test in minutes.**

### What It Does

The platform currently covers **21 chains** (13 EVM / BTC / 3 UTXO / 3 Cosmos / Solana), with five major test categories for EVM chains:

- **Basic transfers**: Standard native coin and token deposits
- **Batch transfers**: Multiple transfer events in a single transaction via helper contracts
- **Amount boundaries**: Zero amount, minimum unit (1 wei), and other edge values
- **Failed transactions**: Insufficient balance, insufficient gas, contract revert — 6 failure types
- **Fake deposits**: Fake tokens, fake events — 6 attack simulations

What used to take **days** to construct now takes **minutes**.

### But Standardization Isn't Enough

The platform solves rapid construction of known scenarios, but testing needs are sometimes highly customized — a new chain with unique transaction structures, or a business team needing to verify a specific edge case. Fixed buttons and forms can't cover every possibility.

To address this, I built a **transaction-crafting bot** powered by an AI Agent (based on OpenClaw). Testers describe what they need in natural language, and the bot automatically constructs the corresponding on-chain transaction.

More importantly, the bot **generates daily reports** summarizing all custom requests from the team. I review these: which ones are frequent? Which have general applicability? Those worth standardizing get added to the platform — **real-world demand feeding back into tool iteration**.

This creates a closed loop:

> Standardized platform → covers known scenarios → AI Agent handles custom requests → daily reports surface frequent cases → feed back into platform updates

---

## Next: Fake Deposit Detection

Everything above deals with "known transactions." But as test engineers, our job isn't just verifying that known things pass correctly — we need to provide quality assurance from a holistic perspective: **can the system correctly handle transaction types we haven't seen before?**

This is the core challenge of fake deposit detection.

### Narrowing the Scope

One key insight: beyond low-level code bugs (like failing to filter reverted transactions), most fake deposit vulnerabilities stem from **complex transaction structures**. And the most complex transaction structures exist on chains that support smart contracts.

So the scope narrows dramatically: **go deep on EVM chains, then sweep through other major chains one by one.**

### Two Exploration Directions

**Direction 1: On-chain Data Analysis**

Pull large volumes of real transaction data from target chains and feed them to AI for type classification. Compare against known types in the platform — if transaction structures appear that don't match any known category, aggregate them and assess whether they need test coverage.

The advantage: **data-driven discovery** of blind spots we "don't know we don't know." The risk: uncertain ROI, and token consumption for large-scale analysis needs evaluation.

**Direction 2: Mock Bombardment**

Pull large volumes of real transactions, replace all `to` addresses with exchange deposit addresses, and submit them in bulk. Essentially using real-world transaction diversity to stress-test the system, seeing which transactions can "fool" the deposit detection.

More direct, more aggressive, and closer to real attack scenarios.

Both directions have trade-offs — most likely the final approach combines them: use Direction 1 to discover blind spots, then Direction 2 for stress validation.

---

## Closing Thoughts

Deposit testing has long been an apprenticeship model — all the capability lives in people's heads, and walks out the door when they leave. What I'm trying to do is straightforward: **turn experience into tools, turn individual capability into team capability, turn one-off testing into repeatable standardized processes.**

The tool is just the starting point. The real goal is building a complete deposit quality assurance system — from standardized testing, to customized supplementation, to unknown threat discovery — forming a layered defense.

> Platform: [deposit.bolab.dev](https://deposit.bolab.dev)
