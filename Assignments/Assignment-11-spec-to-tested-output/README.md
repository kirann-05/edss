# Assignment 11: SDLC Factory: from a spec to a tested output

Lab 11 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 11 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

From a spec to a tested output

## What was built, and where

V1 to V9 as a hard gate; `make acceptance`

## How to show it

`make acceptance`: 94 fault trials over 18 plans, all caught and repaired, in about 2 seconds

## How it is proved

[`docs/acceptance-report.md`](../../Course-Project/docs/acceptance-report.md), and the command fails if one slips through

Run it (from the repository root):

```bash
cd Course-Project
make acceptance
```

Result when this README was written: **94 fault trials, 0 problems** (every injected fault caught and repaired inside the budget of 3).

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
