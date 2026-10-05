# Version-specific test record

Recorded **2026-10-05** for **macOS Friction 1.0.0-rc.3**. These are observations from a small native scene and helper tests, not coverage of every Friction feature. Keep exercised operations distinct from researched candidates.

## Exercised successfully

- Native circles, rectangles and bowed open paths; keyboard tool modes.
- Scalar position/rotation recording; Quad and Cubic In/Out through the Command Palette.
- Baked-key retiming through S with an outside playhead and individual key events.
- Flat fill/stroke, opaque black ball outline, backdrop layering and locking.
- Separate fixed shine; seam rotation cue; grouping foreground and final scale animation.
- Toolbar Undo; committing numeric fields; native menu Cancel recovery.
- Save native .friction project; Format dialog → silent H.264 MP4; queue finished; movie opened in QuickTime; GIF/contact-sheet analysis outside the app.
- Automatic helper: actual clip checks, known stationary geometry, no-foreground scene, one-frame sampling, optional GIF, self-baseline comparison, unchanged source hashes and linked local artifacts. The expected 60-frame check correctly failed on the 59-frame export.

## Attempts that failed or misled

- Tool-button checkbox appearance did not ensure the actual drawing mode changed.
- Global Delete removed an object despite visually selected keys.
- Cmd+Z while a field held focus undid text rather than the scene.
- Repeated clicking hidden Hex, Profiles and preview Resolution controls was ineffective.
- Typing into the queue's destination text field was ineffective; use its file dialog.
- Group-level stroke editing changed a child highlight. Select the intended Circle row.
- Live playback lag made review difficult. Export a lightweight movie early instead of repeatedly playing the editor.

## Researched, still needs an isolated UI test

- Expression entry/import, parameter controls and rotation bound directly to travel.
- Linked scenes, Frame Remapping, property copy/paste and starter-scene duplication.
- Preview Cache state and reliable 25% resolution change.
- G endpoint retiming and group-to-layer promotion.
- SVG import and optional render Profiles shortcut.

The external API available in this test record is a proof of concept, and rc.3 source disables CLI rendering. Recheck the release/API status when the installation changes.

## Remaining investigation

The example 0–59 range encoded 59 frames. The source intends inclusive endpoints, but no cause has been established and no universal export bug is claimed. Reproduce with a tiny isolated scene and inspect first/last frame behavior before proposing a fix.

The tested curved seam is a 2D rotating cue. A physically accurate sphere requires projected/deforming markings and visibility, not only a rotation angle. Use a small isolated test if that is the requested quality standard.

A useful future object-specific verification is fixed-shine tracking: detect the enclosed white highlight, normalize its offset by the ball's radius, and check stability through travel and zoom. This is a proposed extension, not implemented by the silhouette helper. A rendered-outline check could measure darkness and continuity, but movie pixels cannot prove the source stroke's alpha value. Do not claim these checks run automatically yet.

Sources: [rc.3 release](https://github.com/friction2d/friction/releases/tag/v1.0.0-rc.3), [CLI disabled](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/main.cpp#L75), [API proof of concept](https://github.com/friction2d/friction-api), [maintainer API discussion](https://github.com/orgs/friction2d/discussions/724).
