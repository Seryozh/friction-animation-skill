---
name: friction-animation
description: "Create, refine, export, and verify native Friction animations in Codex on macOS with computer-use tools. Use when the user chooses Friction or asks to review an existing Friction scene."
---

# Friction Animation

Author in the user's live Friction scene, deliver a playable review, and check the saved export. Native authoring requires Codex on macOS with computer-use access; the video verifier runs independently. Tested operations were exercised with Friction **1.0.0-rc.3** on **2026-10-05**. Supporting notes distinguish those observations from source-backed features that still need UI testing. Recheck controls and capability claims for other versions or platforms.

## Working path

1. Bind Friction through the documented `mcp__cua_repl` app entry point. Inspect the scene, FPS, native frame range, selected object, playhead, relevant properties and keys.
2. Map the request to objects, properties, endpoints and timing. Inspect existing motion before editing. Read the relevant reference below.
3. Pause playback, edit through native controls, and read back committed values. Check the start, intermediate motion, arrival, transition boundaries and final state; screenshots alone do not prove timing.
4. Save the native `.friction` project. Use a saved revision before structural changes such as grouping or replacing animation curves.
5. Export a short movie for review, especially when editor playback lags. Inspect the playable result and use the verification helper where its assumptions fit.

## References

- [Native controls](references/native-controls.md): tool modes, colors, keyframes, easing, retiming, grouping and focus recovery.
- [Motion and composition](references/motion-and-composition.md): rolling, fixed lighting, a tested example and candidate reusable scene structure.
- [Preview and export](references/preview-and-export.md): preview lag, native MP4 settings, output dialogs and frame-count checks.
- [Automatic verification](references/verification.md): Python dependencies, helper usage, artifacts and measurement limits.
- [Test record](references/field-notes.md): exercised operations, failed approaches and unresolved version-specific behavior.

## Native UI constraints

Use `mcp__cua_repl` for app interaction and file/media tools for saved artifacts. At the recorded test date, the separate Friction API repository described a proof of concept; rc.3 source disables CLI rendering. See the sources in the test record. Do not assume an authoring API exists or replace the selected application without the user's agreement.

Accessibility IDs change. Locate controls by fresh labels/state and use coordinates only from the current screenshot. Numeric properties usually committed with click, **Cmd+A**, value, **Tab**; the current-frame field required double-click, Cmd+A, value, **Return**. Verify the committed value.

A yellow key selection does not prove keyboard focus. Global **Delete** can remove an object; **Cmd+Z** inside a numeric field can undo text. Use scoped actions or toolbar **Undo** and inspect the result. Read the selected child before editing fill/stroke: a group-level edit can affect several children. The Hex field uses **#AARRGGBB**, so opaque black is **#FF000000**. Scroll hidden fields into view before editing.

## Review scope

Keep travel, surface rotation, lighting and framing separate when the scene needs them. A rotating 2D seam is a stylized rolling cue, not physically accurate spherical projection. Expressions and linked scenes are source-backed candidates; their UI workflow was not exercised in the test record.

The helper checks export integrity and measures a combined foreground silhouette on a flat background. It cannot establish artistic intent, lighting behavior, rolling accuracy or separate motion of multiple objects. Report failed checks and distinguish native-project edits from changes made to an exported review movie.
