# Retrieval adoption execution

## Pre-flight

Task: make models choose Pit retrieval for missing context. Selected approach: retrieval discovery, global triggers, bounded direct readers and compaction anchors. Criteria: minimal decision friction, original-text evidence, per-session continuity, existing authorization. Assumption: this local host supports plugin stdio MCP and SessionStart compact context. Accepted trade-off: literal search requires query variants. Core schema, credentials and cloud behavior stay as previously agreed. Invalidated if native tools or hooks are not discovered; stop/pivot on wrong-session context, content injection, credential exposure or capture failure being labeled success.

## Execution checklist

- Retrieval skill description names prior work and missing-context situations.
- Preserve unrelated global guidance; add conditional retrieval behavior.
- Tools expose only bounded search/ranges with no credentials in arguments.
- Hook state stores only validated hashes/ranges for exact session identity.
- Verified capture tail and recent retrieval anchors survive SessionStart compact.
- Installation, native tool discovery/calls, hook trust and global scope verified.
- Ordinary model task chooses retrieval without a tool-specific instruction.
- Adversarial tests reject incorrect bounds, unknown tools, unsafe error echo, foreign session state and quoted-text injection.
- Human habit/adoption over varied real tasks remains an observation, not a deterministic configuration guarantee.

## Execute

### Execution Complete

**Task:** Installed plugin 0.5.0 with retrieval discovery, global guidance, direct tools and compaction recovery pointers.
**Aim achieved:** A fresh ordinary follow-up chose search and range reads without a tool-specific instruction; native compaction delivered a stored pointer absent from prior model history.

### Declared Success Criteria

- Retrieval discovery: met; plugin/read lists retrieve-from-pit and export-to-pit.
- Global conditional guidance: met; prior file prefix preserved.
- Bounded direct tools: met; native MCP inventory and real model calls verified.
- Session recovery pointers: met; real tool events journaled correct-session metadata, native compaction delivered a pointer.
- Capture semantics: preserved; exact verified capture only, fail-open on unknown delivery.
- Core text, credentials and cloud boundaries: preserved.

### Changes

- plugin/skills/retrieve-from-pit/SKILL.md: when and how to recover context.
- ~/.codex/AGENTS.md: global missing-context trigger and evidence rules.
- plugin/mcp/server.py, plugin/.mcp.json, compatibility manifest: read-only direct readers.
- plugin/hooks/retrieval_context.py, hooks.json, precompact.py: metadata-only session continuity.
- plugin/tests/: RPC, privacy, isolation, bounds, Unicode and protocol checks.
- README.md, plugin.md: installation and runtime evidence.

### Verification

30 tests passed. Native plugin inventory and MCP tools discovery succeeded. All three hook definitions are enabled and trusted in /tmp and this workspace, without reported errors/warnings. Normal prompt: "What did we decide about sources in The Pit, and why? I want to continue from the earlier discussion." The model chose pit_search with "source identity" and "sources", then pit_read_range [23800,36500), and answered from the user's words. PostToolUse wrote four validated anchors for trial session 01a0f474-93c1-75b1-96a9-859d1aca6dca.

Compaction trial session 01a0f477-4a52-74d1-8406-37b85a5232d3: seeded entry 44ab88426e5e702016555f805e8c29aa1e578adad65379be99b9ab50f70a565e [24001,24123) after the first model turn, invoked native thread/compact/start, then received that exact pointer from the next model without tools or file reads. Private runtime evidence remains under ~/.local/share/the-pit/evidence/.

### Risk Retirement

| Risk / Assumption / Stop Trigger | Status | Tempting Patch This Check Fails | Evidence / Route |
|---|---|---|---|
| Discovery only exists in docs | Retired | Add prose without host tools | Native tools inventory and autonomous real calls |
| Models still ask user to repeat context | Retired for one trial | Advertise export alone | Fresh ordinary prompt caused searches then range read |
| Pointer disappears at compaction | Retired | Hope summary retains it | Pointer seeded outside model history was reported after native compaction |
| Byte offsets masquerade as characters | Retired | Use len(UTF-8 bytes) | Unicode capture-pointer test caught and fixed this |
| Retrieved instructions become authority | Retired | Inject excerpts into developer context | Metadata-only validation; adversarial quoted-instruction test |
| Wrong session or server context leaks | Retired | Shared global anchor file or broad tool matcher | UUID isolation, foreign-state rejection, strict server matcher tests |
| Failures look like success | Retired | Store upload hash before verified delivery | Unknown upload creates no capture pointer; failed tool result records no anchors |
| Credentials/error body exposed | Retired | Include raw exceptions or config in tools | Existing private client; sanitized error tests |
| Full transcripts transferred by default | Retired | Implement tools via full read then slice | RPC-only client tests; native model range call |
| Unrelated guidance/config changes | Retired | Replace entire global instructions | Existing instruction prefix checked; narrow hook trust writes |
| All models always retrieve appropriately | Accepted with rationale | Infer universal behavior from one trial | Model choice remains probabilistic; observe normal work |
| Natural automatic capture across all clients | Accepted with rationale | Claim synthetic/manual event proves natural auto | Existing explicit manual capture proof and handler tests; natural host capture remains to observe |
| Running chats hot-reload new tool definitions | Accepted with rationale | Assume fresh-process inventory proves current-process reload | Fresh native process verified; existing harness restart may be needed |

### Needs Human Verification

Normal use across different tasks/models and natural automatic capture remain observations. No further setup choice is required.

### Notes

Keep the DB authoritative text unchanged. Anchors are replaceable local reader state. A capture-tail pointer is a starting point, not a semantic summary. No query is run automatically by the hooks. Literal query variants remain necessary. Cloud is out of scope.

Drift verdict: aligned. Authority boundaries stayed within the user's explicit "execute on all of that" and prior global local-session authorization. Superego plan and final code review: no concerns.

## 2026-10-01: trust compaction, retain optional recovery

The user chose to trust compaction summaries. SessionStart now injects only a brief reminder that the precompaction conversation is available in the Pit, with no hashes, ranges, or transcript excerpts. Retrieval is for specific missing context, not routine hydration. PreCompact capture and private receipt/bookmark storage remain unchanged. Source and installed 0.5.0 copies were updated; running harnesses may need a restart to refresh loaded skill/global guidance.

## 2026-10-01: decision-point checks

The user chose a lightweight Pit check analogous to superego: at substantial task starts, approach decisions, brief preparation, and before asking about prior context. One or two concrete literal searches look for constraints or decisions even without an obvious gap; only relevant matches are expanded. Self-contained tasks and already-covered checks are skipped. Compaction itself still does not trigger retrieval or pointer hydration. Global guidance, retrieval skill, MCP descriptions/instructions and the short availability reminder now agree. This is behavioral guidance, not guaranteed model compliance; a fresh harness is needed to verify autonomous adoption.
