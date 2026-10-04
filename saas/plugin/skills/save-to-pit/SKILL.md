---
name: save-to-pit
description: Save supplied text or an authorized workflow's output to the user's private Pit, including briefs, notes and decisions.
---

Use `pit_append` to preserve text the user wants saved. Use it readily when saving is part of the requested workflow, including recurring briefs with an instruction to write to the Pit.

Pass the exact supplied text. Do not require a source, title, tags, classification or a template. If the user asks for a summary or brief to be saved, compose that requested output first and append it as text. Do not silently replace a requested transcript with a summary or claim to capture conversation history you cannot access.

Report success only from the tool receipt. An exact duplicate is a successful save when verified; report that it was already present if useful. Preserve the returned hash for follow-up reads. A failed or uncertain receipt is not confirmed storage.

This package saves text available in the current workflow. It does not install automatic conversation capture or precompaction hooks.
