# Test rebalance: glpi-project/glpi

2026-10-04 · window: 180 days (880 commits, 163 ignored as sweeps) · CI data: none

## Summary

GLPI's suite is in good shape. Most of it is integration tests on a real MySQL database. A 106-file Playwright suite runs on every PR and is concentrated on Forms, the area that's newest and most active. The one clear move is inside Forms: 15 browser tests submit a form and check the resulting ticket, which the PHP integration suite already checks field by field. No upgrade candidates met the bar.

| Level | Files | Tests |
| --- | --- | --- |
| e2e | 106 | 394 |
| api | 31 | 296 |
| integration | 523 | 3,536 |
| component | 1 | 8 |
| unit | 101 | 481 |

**Project helpers mapped before counting.**
- `DbTestCase` runs against a real database. Mapped to integration, including everything that inherits from it: `InventoryTestCase`, `AbstractInventoryAsset`, `AbstractDestinationFieldTest` and others. 381 classes extend it directly and many more inherit from it.
- `HLAPITestCase` drives the high-level API router in-process on a real database. Counted as api.
- The first pass flagged 9 Jest files as browser tests because jQuery's `$('...')` looked like WebdriverIO. Fixed.

## Move down

### tests/e2e/specs/Form/DestinationConfig, "Can create ticket..." tests → integration (confidence: medium)

- **Question it answers:** when a form is submitted, does the ticket get the right urgency, category, actors, location and so on, for each destination strategy?
- **Evidence:**
  - 16 spec files each pair a "Can use all possible configuration options" test with a "Can create ticket..." test: 15 of the latter in total.
  - The ticket-outcome half already has a direct PHP counterpart in `tests/functional/Glpi/Form/Destination/CommonITILField`, which has 30 field test classes. `UrgencyFieldTest`, for example, asserts the resulting ticket's urgency for the template, specific-value and from-question strategies.
  - The code underneath, `src/Glpi/Form/Destination`, had 12 non-sweep commits in the window.
- **Replacement:** keep each field's configuration-editor test in the browser, because the editor UI is the point there. Move the ticket-outcome assertions to the integration tests, adding any strategy they don't yet cover.
- **Keep:** one or two browser tests that submit a form end to end, so the full submit-to-ticket path stays covered.

## Move up

No candidates met the bar. Checked:
- **The Symfony kernel and routing layer:** `src/Glpi/Kernel` had 7 commits and `src/Glpi/Controller` 18, with dedicated `Kernel`, `Routing`, `Http` and `Controller` test folders.
- **Setup templates** (`templates/pages/setup`, 13 commits): an E2E `Setup` folder exists. The subject matching couldn't link it, so it's worth a manual look but isn't evidence of a gap.

## Leave it alone

- **The rest of the Forms browser suite** (question types, conditions, editor, rendering, translations): Forms is GLPI's newest major feature (`src/Glpi/Form` 51 commits), and the browser is where layout, conditions and the editor actually live.
- **Core ITIL objects in `src/`** (337 commits across the flat legacy classes), covered by 1,526 integration tests on a real database. That's the right level for code this tied to the schema.
- **The high-level API** (`src/Glpi/Api`, 24 commits): 158 API-level tests running in-process. Cheap and close to the contract.

## Worth a look (low confidence)

- 86 of the 106 E2E files didn't change in the window. That's healthy if they're passing on every PR, which the CI wiring suggests they are. CI timing data would show whether any of them are slow enough to be worth moving.

## Why-this-level annotations

```
Form/DestinationConfig: e2e for the configuration editor only; ticket outcomes per field live in CommonITILField integration tests. Revisit if destination config moves out of the browser editor.
Forms suite: e2e because Forms is new and still changing. Revisit when src/Glpi/Form churn settles.
```
