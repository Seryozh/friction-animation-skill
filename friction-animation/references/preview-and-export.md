# Preview, render and export integrity

## Review without lag

Pause before editing and stop an old cached preview before checking fresh motion. Scrub the canvas to verify changes, then rebuild preview. Source-backed options are **View → Preview Cache** and lower canvas **Resolution**. Let a cache finish before judging real-time speed.

In the rc.3 test, canvas resolution was 50%; attempted changes to 25% did not commit. Read the control back before assuming a resolution change worked. Canvas preview resolution and render resolution are separate.

A rendered review MP4 gave reliable playback in the test. Generate a modest GIF if helpful for inline looping; keep the exported movie as the timing reference.

## Tested native MP4 route

1. Pause preview. Use the toolbar **Render** action to open the render queue and add the job. Expand that job and inspect its scene/range/resolution.
2. Open the job's **Format** dialog directly. The Profiles button did not reliably open a popup in the rc.3 test.
3. Choose **MP4** in Format. Keyboard navigation Home, Down, Down, Return selected MP4 from the observed list, but confirm the live list before reusing that sequence.
4. Enable **Video**. MP4 automatically enabled Audio too; disable Audio for a silent scene. Tested codec was libx264, yuv420p, default approximately 9 Mbps. Adapt settings to delivery needs.
5. Use **Select output file** to open the native save dialog. In rc.3 the queue destination field is read-only despite misleading accessibility editability; typing into it is ineffective.
6. Confirm the output, stop preview and render. Wait for **Finished**, then inspect the saved file. Queue **View/Play → default** opened the movie in QuickTime.

Native rendering uses bundled FFmpeg libraries. The CLI tools used by the verification helper are separate and should be discovered; do not install another Friction renderer.

## Verify the export

Measure codec, dimensions, FPS, decoded frame count, duration and full decode success. Check initial and final visible states. Then use the review helper for contact sheets and trajectory measurements.

An example rc.3 range **0–59 is intended to contain 60 frames**. Source `FrameRange::span()` is max−min+1 and submission iterates through the maximum. The test MP4 contained **59 decoded frames** at 30 FPS, duration 1.966667 seconds. This is an observed export discrepancy, not an exclusive-end convention or proof of a universal rc.3 bug. Its cause remains unconfirmed. Do not add one to every export endpoint as a blanket fix.

When a check fails, retain the source and review artifacts, report the discrepancy, and investigate the native range/encoder behavior separately. A Finished job or attractive final screenshot does not prove that every requested frame was encoded.

Sources: [export](https://friction.graphics/documentation/export.html), [preview](https://friction.graphics/documentation/usage.html#preview), [canvas resolution](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/ui/widgets/canvastoolbar.cpp#L143), [performance options](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/ui/widgets/performancesettingswidget.cpp), [inclusive range](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/core/framerange.h#L70), [frame submission](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/renderhandler.cpp#L378).
