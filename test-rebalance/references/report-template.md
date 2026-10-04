# Test rebalance: <repo name>

<as-of date> · window: <N> days · CI data: <N runs | none>

## Summary

<Two or three sentences: the suite's current shape and the single most useful change.>

| Level | Files | Tests |
| --- | --- | --- |
| e2e | | |
| api | | |
| integration | | |
| component | | |
| unit | | |

## Move down

### <test file or group> → <target level> (confidence: high/medium)

- **Question it answers:** <one line>
- **Evidence:** <commits, fix commits, last real change, failure rate, seconds>
- **Replacement:** <what the new test asserts, which boundary is mocked or bypassed>
- **Keep:** <any thin smoke coverage that should stay at the current level>

## Move up

### <test file or group> → <target level> (confidence: high/medium)

- **Question it answers:**
- **Evidence:**
- **Why the current level is no longer enough:**

## Leave it alone

- <file>: <why it's expensive but right where it is>

## Worth a look (low confidence)

- <file>: <what's suggestive, what evidence is missing>

## Why-this-level annotations

```
<file>: <level> because <reason>. Revisit if <condition>.
```

## Appendix: per-file evidence

| File | Level | Test commits | Subject commits | Fix commits | Failure rate | Mean s |
| --- | --- | --- | --- | --- | --- | --- |
