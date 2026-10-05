# Motion, lighting and reusable controls

## Make motion perceptible

A uniformly colored circle does not reveal its rotation. Add a surface cue consistent with the requested design. A thin bowed seam was tested as one native option; the cue is a design choice, not a default for every ball animation.

For horizontal no-slip rolling at radius R, rotation is `(x − startX) / R` radians, or that value × 180/π degrees. Coordinate direction determines the sign. Bind rotation to actual travel when a verified expression workflow exists. Independent fitted easing curves can drift; check intermediate frames as well as endpoints.

A bowed line rotating in 2D is stylized. Real spherical markings change projected shape and visibility. If the requested fidelity requires spherical projection, test native path morph/visibility behavior before claiming that a simple rotation provides it.

Keep light separate from surface rotation when illumination should remain fixed relative to the scene. In the tested flat-design example, a white ellipse translated with the ball at a fixed offset without rotating around it. This is a stylized lighting treatment, not a physical lighting simulation.

## Verified example — values are not defaults

Scene: 1920 × 1080, white locked backdrop, 30 FPS, native range 0–59.

| Element | Tested values |
| --- | --- |
| Main ball | Radius 157.741, orange #FFF76E17, black #FF000000 outline width 10 |
| Travel | x 370.049 → 960, y 540, frames 0–21, Quad In/Out |
| Ball/seam rotation | 0 → 214.286°, frames 0–21, matched Quad In/Out |
| Bowed seam | Two-node open Path; no fill; stroke #FFD65012, width 5, round caps |
| Seam local endpoints | (0,0), (0,325.482); y translation 377.259; local pivot (0,162.741) |
| Seam inset | Uniform scale 0.965, keeping tips inside the outline |
| Fixed shine | White ellipse radii 24,16; ball offset (−47,−64); rotation unchanged |
| Zoom parent | Pivot (960,540); scale x/y 1 at frame 30 → 0.6 at frame 59 |
| Zoom easing | Cubic In/Out separately on x and y; both 0.780 at frame 45 |

Set a path's pivot while rotation is zero and scale one; verify that its appearance stays in place. Frame 21 is arrival (~0.7 seconds), frame 30 begins zoom after a hold, and the final scale is 0.6. Matching curves, fixed shine, scene centering and zoom were checked in the app and sample render. Export integrity is discussed separately.

## Faster scene architecture

The tested scene used matched translation curves on children. A candidate structure for a reusable starter scene is:

```text
Zoom group (framing/scale)
└── Travel group (one position animation)
    ├── Rolling group (rotation)
    │   ├── Ball
    │   └── Surface seam
    └── Shine (fixed offset, no rotation)
Backdrop (locked, outside zoom group)
```

This uses transform inheritance to avoid duplicating travel curves. It is source-backed design advice; this hierarchy was not exercised in the rc.3 test. Test in a saved copy and compare earlier frames before replacing an existing arrangement.

Useful reusable controls: radius, start/end position, arrival time, hold time, rotation multiplier, zoom start/end, outline width, shine offset and seam visibility. Prefer understandable names and defaults. Do not expose technical handles merely because they exist.

Native starter projects and duplicating complete objects/groups can save work. Source-backed expressions can use ECMAScript bindings, Calculate and Return; `.fexpr` files contain unique id, title, bindings, script and definitions. Import through the expression dialog loads a preset immediately; files placed directly in the macOS preferences Expressions folder load at startup. The expression entry/import workflow was not exercised in the rc.3 test.

Linked scenes and Frame Remapping are source-backed native reuse candidates for longer work. Their UI workflow was not exercised in the rc.3 test.

Sources: [official tips](https://friction.graphics/documentation/tips.html), [expressions](https://friction.graphics/documentation/expressions.html), [immediate import behavior](https://github.com/friction2d/friction/blob/v1.0.0-rc.3/src/app/GUI/Expressions/expressiondialog.cpp#L918), [linked scenes](https://github.com/orgs/friction2d/discussions/242).
