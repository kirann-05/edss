# Parallel domain agents: benchmark

Written by `make benchmark` on 2026-10-26, on arm64 (Darwin, 10 cores), Python 3.12.15. Median of 3 runs each. One full run of the graph for the current year with all four areas, on synthetic data and the canned model.

**The delay is simulated.** Each domain agent waits the stated time before it reads, to stand in for a slow university system. The real reads are from memory and take far less than a millisecond, so the rows below show the shape of parallel work, not how fast the university's systems are.

| Delay per agent | Domain phase, parallel | Domain phase, one at a time | Speed-up | Whole run, parallel | Whole run, one at a time | Agents, parallel | Agents, one at a time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 ms | 1 ms | 1 ms | none to measure | 16 ms | 13 ms | one at a time | one at a time |
| 250 ms | 258 ms | 1026 ms | 4.0 times | 280 ms | 1060 ms | all four at once | one at a time |
| 700 ms | 709 ms | 2828 ms | 4.0 times | 739 ms | 2862 ms | all four at once | one at a time |
| 1000 ms | 1008 ms | 4027 ms | 4.0 times | 1035 ms | 4058 ms | all four at once | one at a time |

How to read it: with four agents each waiting the same time, one at a time takes four waits and in parallel takes one, so the best possible speed-up is four times. With no delay there is nothing to win, which is why the demo states its simulated delay on screen.

How it is measured: the domain phase runs from the first agent starting to the last one finishing, taken from the run's own events. One at a time is the same graph with LangGraph's `max_concurrency` set to 1, and the events confirm the agents did not overlap.
