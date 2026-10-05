# Native controls: macOS rc.3

## Selection, tools and fields

Tested: **F1** object selection/transform, **F3** Path Create, **F5** Circle, **F6** Rectangle. Shift-drag with Circle makes a circle. Tool-button accessibility checkboxes sometimes changed appearance without switching the internal mode; keyboard commands were reliable. Verify the resulting interaction.

Tested numeric properties: click the field, **Cmd+A**, type, **Tab**. Read it back after committing. For the current-frame field, double-click, Cmd+A, type, **Return** worked when a single click edited an unintended value. Frame numbers and values must be read back before subsequent operations.

Tested recovery: toolbar **Undo** affected scene authoring; Cmd+Z while a spinbox retained focus affected field text. Delete removed an entire circle even when keys looked selected. Scope keyboard focus explicitly before deletion; visual yellow keys alone are insufficient. Restore accidental scene changes through a verified Undo and inspect the result.

An open native menu sometimes survived Escape and blocked screenshots. A fresh menu element's documented `performSecondaryAction(..., 'Cancel')` dismissed it. Locate the menu in the current state rather than reusing an element ID.

## Colors, outline and backdrop

The Fill & Stroke **Hex** field uses **#AARRGGBB**, with alpha first. Opaque black is **#FF000000**; white is **#FFFFFFFF**. Choose **Flat** before editing a flat color. Width and alpha are independent: a wide stroke may still be transparent.

Scroll until Hex is visible; an accessibility click on the offscreen field failed. Inspect the selected object before setting style. In the test scene, a group selection changed the highlight as well as the ball; selecting the main Circle row directly scoped the edit correctly.

Tested backdrop: F6, rectangle beyond the canvas, Fill Flat opaque white, Stroke None, **Object → Lower to Bottom**. Lock the backdrop through its Timeline row before selecting foreground objects. The source also exposes **End** / palette **Lower Object to Bottom**, but use a verified current action.

## Keyframes and easing

Select the target object, inspect **Transform → Translate → x**, set the start frame and enable that property's recording dot. At the end frame, edit the value. Without recording, an edit may alter the whole motion rather than create a key. Verify both endpoints and an intermediate value.

Select at least two keys on the same scalar property before easing. Clear old key selections, select the earliest key first, then Shift-click the latest key (or select a chronological range and verify its endpoints). rc.3 uses the first and last selected keys as its span without sorting, so selection order and scope matter. Presets bake fitted Bézier keys; extra intermediate keys after easing are normal. Applying another preset replaces the selected span. Scalar easing does not apply to smart-path morph keys.

The tested route was **Help → Command Palette**, default **Option+Space** on macOS rc.3. Search the exact action, e.g. **Ease In/Out Quad** or **Ease In/Out Cubic**, then Return. Select the keys before opening it. The published shortcut table lists Ctrl+Space; the macOS source overrides the palette binding to Option+Space. Ctrl+Space triggered preview in the tested configuration. Inspect current menus and shortcut settings before relying on either binding.

Choose easing for the intended motion. Quad In/Out was tested for travel and Cubic In/Out for zoom; these are examples, not a universal definition of realism. Cubic In/Out has roughly 14.8%, 50%, 85.2% progress at one-third, one-half and two-thirds; linear gives 33.3%, 50%, 66.7%. Fitted curves may differ slightly.

## Retiming

**Tested baked-curve example:** pause, set playhead to **−1**, select all keys in the intended span, press **S**, then send **0**, **period**, **7**, **Return** as separate key events. This moved a 0–30 range to 0–21. Pasting the modal scale text was ineffective. The outside pivot avoided a key at zero distance. These values apply to that example; calculate and verify a different span separately.

Scaling pivots around the current frame. rc.3 graph-key scaling divides by original distance from that pivot; a pivot coincident with a selected key is unsafe. Rounding can merge nearby keys or perturb handles. Adapt the calculation to the requested range and verify endpoints and motion afterward.

**Source-backed, not exercised:** select only the endpoint key, **G**, signed frame offset, Return. At 30 FPS, a frame-30 endpoint moved by −9 ends at frame 21. Reapply easing only after confirming the new span. Do not claim this route is tested until used in the live app.

## Grouping

Tested: lock backdrop, F1, focus canvas, Cmd+A selects unlocked foreground objects. **Object → Group** retained child transforms and keys and centered the parent pivot. Group at the settled frame for a centered final zoom; verify the pivot and earlier child motion afterward.

Ordinary group opacity does not apply according to official tips. Promote to a layer when opacity, blending, masks or raster effects are required; this was researched rather than exercised.

Sources: [usage](https://friction.graphics/documentation/usage.html), [shortcuts](https://friction.graphics/documentation/shortcuts.html), [tips](https://friction.graphics/documentation/tips.html), [easing selection](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/GUI/graphboxeslist.cpp#L54), [palette actions](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/GUI/extraactions.cpp#L631), [Mac palette binding](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/GUI/menu.cpp#L777), [G retiming](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/GUI/keysview.cpp#L411), [scale pivot](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/core/Animators/graphkey.cpp#L156), [curve baking](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/core/Animators/qrealanimator.cpp#L304).
