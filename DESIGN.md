---
name: Revoice
description: A graphite voice studio in a native Mac window.
colors:
  bg: "#171b21"
  side: "#14181e"
  panel: "#1c2128"
  raised: "#282e36"
  ink: "#f4f5f7"
  muted: "#a5aebb"
  line: "#343d48"
  accent: "#b3f16b"
  accent-ink: "#17210e"
  error: "#ffb4a9"
typography:
  display:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif'
    fontSize: "42px"
    fontWeight: 650
    lineHeight: 1.12
    letterSpacing: "-.035em"
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif'
    fontSize: "23px"
    fontWeight: 650
    letterSpacing: "-.025em"
  title:
    fontSize: "16px"
    fontWeight: 600
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif'
    fontSize: "14px"
    lineHeight: 1.45
  label:
    fontSize: "13px"
rounded:
  field: "8px"
  button: "9px"
  device: "10px"
  stage: "15px"
  dialog: "16px"
spacing:
  small: "8px"
  control-gap: "12px"
  routing-gap: "14px"
  section: "18px"
  compact-stage: "20px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.button}"
    padding: "11px 17px"
  button-outline:
    rounded: "{rounded.button}"
    padding: "11px 17px"
  field:
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "12px"
  stage:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.stage}"
    padding: "23px 28px 10px"
---

# Design System: Revoice

## Overview

**Creative North Star: "Graphite voice studio"**

The approved world uses a matte catalog sleeve, charcoal working surfaces, pearl text, and lime action signals. The implementation is an offline web interface inside a native Mac launcher. This document records actual source rules, including their responsive changes; it does not certify pixel fidelity to the approved image.

The nativeMac system typography is user-pinned. The hero image comparison failed at 58% and remains open. Its geometry and current values are implementation evidence, not a declaration that the reference has been matched.

**Key Characteristics:**

- Readable named voices with locally bundled animated DiceBear Waves avatars.
- Layered graphite surfaces with restrained borders and soft depth.
- State-driven feedback and visible keyboard focus.

## Colors

One lime accent sits over a cool graphite neutral family.

### Primary

- **Lime signal** (`accent`): primary actions, active meter bars, live status, selected voice edge, range controls, and focus.
- **Dark lime ink** (`accent-ink`): text on filled lime controls.

### Neutral

- **Graphite ground** (`bg`) and **catalog sleeve** (`side`): app background and sidebar.
- **Working charcoal** (`panel`) and **raised charcoal** (`raised`): stage/dialog and selected rows/picker menus.
- **Pearl** (`ink`): readable foreground; **cool gray** (`muted`): supporting labels.
- **Hairline graphite** (`line`): section separators and main panel boundary.
- **Warm error** (`error`): errors and remove action. It is a semantic signal rather than a second brand accent.

**The Signal Rule.** Lime communicates actions, selection, focus, and measured live activity. Use actual application state to drive it.

## Typography

**Display and body font:** macOS system sans-serif, with BlinkMacSystemFont, Helvetica Neue, and sans-serif fallbacks.

The type is compact and familiar in the Mac window. Strong voice names establish identity; smaller mixed-case labels describe controls. The nativeMac choice is an explicit user exception to a generic prohibition on system display fonts.

### Hierarchy

- **Display:** selected voice name; uses the frontmatter display role, stepping to 37px at 950px and 30px at 700px.
- **Headline:** the main screen heading.
- **Title:** routing section headings.
- **Body:** inherited interface copy; voice descriptions use 15px.
- **Label:** field and dialog labels. General helper text uses 13px; voice-settings helper text uses 12px. Compact status, meter, and library metadata still contains 11–12px source values; these are not recommended as a universal text scale.

**The Native Type Rule.** Preserve the user-pinned system family across controls and identity text.

## Layout

The wide app uses a 225px sticky full-height sidebar and flexible main column. Main padding is 25px; the stage has an 1100px maximum width and a minimum height based on the viewport. Device pickers sit in two equal columns, and advanced sliders also use two columns. Monitoring and conversion each occupy a clearly labeled row. Microphone mute is integrated into the input meter. A dedicated recorder follows conversion, with elapsed capture time, progress, playback, and save controls. The former routing sentence and three-button action dock are absent from the current surface.

At 950px, the sidebar narrows to 195px, main padding becomes 16px, stage padding becomes 20px, and identity size decreases. At 700px the web surface becomes a single column: the library turns into a horizontally scrolling row, routing and advanced fields stack. That narrow web fallback does not imply a mobile release. The native window opens at 1060 × 790 and enforces an 820 × 650 minimum.

The repeated spacing vocabulary is compact: 8px control spacing, 12px action gaps, 14px routing gaps, and 18–20px section padding. Flexible widths, wrapping voice headings, and minimum-width resets avoid rigid screenshot dimensions.

## Elevation & Depth

Tonal layering carries most depth. Soft shadows lift actions, the avatar, picker menus, switch thumb, and modal; borders separate adjacent graphite surfaces. The modal adds a dark translucent backdrop with 4px blur.

### Shadow Vocabulary

- **Action:** `0 2px 5px #0003`.
- **Avatar:** `0 8px 20px #0003`.
- **Picker menu:** `0 14px 28px #0005`.
- **Switch thumb:** `0 1px 3px #0004`.
- **Modal:** `0 22px 70px #0008`.

## Shapes

Controls use gently curved corners; the field, button, device, stage, and dialog roles are recorded in frontmatter. Avatars and capture indicators are circular. A selected library row has a thin lime edge. Meter segments use small 3px corners. Line SVG icons share round caps and joins.

## Components

### Buttons

Filled lime identifies import and empty-library actions. Conversion uses a switch rather than a filled start button. Outline controls use charcoal fill and a muted border; ghost actions use supporting text without a container. Filled and outlined controls have a 44px minimum height. Hover changes the fill; keyboard focus uses a 2px lime outline with a 4px offset. Disabled controls lower opacity to .45 and do not imply availability. Ghost utility actions also have a 44px minimum height after the height refinement.

### Cards / Containers

The stage is the principal working container, bounded by a single hairline. The identity uses 12px top and 18px bottom margins; the selected avatar is 124px square. Monitoring and conversion now use 18px vertical padding. Device containers have 10px 15px padding and a visible border. Avoid promoting every section into a separate card.

### Inputs / Fields

Text fields use a darker inset ground, a muted border, 8px corners, and 12px padding. Custom voice and device listboxes inherit the same system typography. Device triggers have 44px height; option rows have a 44px minimum height. Menus use a raised charcoal ground, a visible border, 12px corners, 6px padding, and a soft menu shadow. Selected options use lime text and subdued green fill. Arrow keys, Home, End, and Escape navigate or dismiss; selecting an option restores trigger focus. The normal audio profile is the only product profile; the quality/profile picker is absent. Range controls use lime. Error copy remains separate from placeholder text.

### Navigation

Named voice rows carry circular avatars, a selected tonal fill, and a thin lime edge. Selection is also exposed through `aria-pressed`. The library search field is always visible; its search icon focuses that field. The active app navigation item receives a darker fill. Training is visibly unavailable. The compact web fallback hides app navigation and turns the library into a scrolling row.

### Status and input meter

Ready and attention states are neutral; connected Voice on and Natural voice states use the live treatment, and muted microphone state uses warm subdued brown. State text remains visible alongside its color. Thirty-two meter segments follow actual unmuted input; they are not decorative activity. The inset input console uses a dark ground, a border, 10px corners, and 18px-high segments. Control transitions take 140ms; meter colors take 80ms. Connecting dims the meter and pulses the microphone icon in a 1.6s ease-in-out cycle. Reduced-motion preference removes transitions and animations.

### Conversion and monitoring switches

The visible track is 44 × 26px within a 52 × 44px button. Its circular thumb moves 18px when enabled. The track changes to lime, and `aria-checked` carries the current state. Conversion off passes the natural voice through the same virtual microphone. Monitoring and microphone mute remain distinct controls. Microphone mute is the 44px icon control within the input console; the visible On/Muted label and pressed state describe it. Muting gives the icon a warm treatment and flattens the meter into subdued brown-gray segments.

### Voice avatars

DiceBear Waves 10.6.0 is generated offline from the normalized voice name, permanent voice ID and saved creation time. Renaming changes its seed; reloads preserve it. Library, picker and selected voice use the same artwork. Each inline instance has scoped IDs and rewritten references. The shared animation clock moves six layers, gated by visibility, background state and Reduce Motion. Avatar movement is decorative identity and does not indicate audio activity.

### Recorder and playback

A dedicated recorder has a 44px Record/Stop control and a dark capture panel with 12px corners and 18px 20px padding. Its warm recording indicator, prominent 22px elapsed time, tabular numerals, and thin 5px progress bar describe the 20-second sample limit. Actual Starting… and Saving… transitions temporarily disable the record control; pending capture presents explanatory text and a saving indicator instead of elapsed/progress feedback. Recording feedback comes from actual capture seconds. A completed sample reveals a dark inset playback container with 10px corners and 14px 18px 16px padding, a circular 44px lime play/pause button, seek slider, elapsed/duration labels, and a 44px save icon. Loading playback… and an aria-busy state remain until audio metadata is ready, with play and seek disabled. Playback errors preserve saving while disabling unavailable playback. The native audio element is hidden while its playback events update these controls. Test recordings remain temporary bytes in backend memory until explicitly saved. A 44px close X discards those bytes, removes the player source, and revokes the preview URL; polling cannot restore the discarded preview. Save writes a WAV directly to Downloads, then discards the temporary preview and displays the saved filename. There is no Show in local files recording action. Save/discard failures remain visible and preserve a recoverable preview when cleanup has not succeeded.

### Voice removal

Removal occupies a separate management row below voice settings, separated by a hairline. The subdued red outlined Remove voice button has a trash icon, 44px minimum height, 8px corners, and a muted red border. Hover adds a warm dark fill. This treatment keeps a destructive library action distinct from voice tuning.

A custom dialog names the selected voice and pairs Keep voice with a warm filled Remove voice confirmation. Keep voice receives initial focus. Submission disables confirmation and shows Removing…; an inline error preserves the dialog when removal fails. Successful removal closes the dialog, releases any recording preview, and refreshes the library.

## Do's and Don'ts

### Do:

- **Do** keep named voice navigation readable and pair controls with clear labels.
- **Do** use visible focus and honor reduced motion.
- **Do** reserve live feedback for actual input and engine state.
- **Do** preserve nativeMac system typography and responsive reflow.

### Don't:

- **Don't** add effects racks, gamified audio skins, or fake metrics; the product commitment rejects them.
- **Don't** imply training or an absent driver is ready.
- **Don't** treat the approved mockup's illustrative voices or active meter as public app content.
- **Don't** claim reference fidelity until the open hero comparison is resolved.

**Not canonized:** the historical failed 58% hero comparison remains open after this simplification; no reference-fidelity pass is claimed. Remaining 11–12px metadata text is not promoted into a universal text scale. Ghost action targets are now 44px. General helper text is 13px and settings helper text is 12px; the 24px seek/range control heights and smaller timing metadata are implementation limits, not universal control or text rules. Documentation does not repair implementation limits.

0.1.3 refinement: consolidate engine status into microphone label (Connecting, Voice on, Natural voice, Muted, Disconnected); no standalone phase pill. Genuine offline Waves SVG geometry is rendered inline with instance-scoped IDs and a common requestAnimationFrame clock. Only visible avatars animate; reduced motion and background windows remain static. Capture and preview have one clear panel each, real elapsed/progress and explicit Starting/Saving/Loading playback states. In 0.1.4, Close discards temporary audio from memory; Save writes directly to Downloads then discards the preview.

Mobbin references: [Fireflies](https://mobbin.com/screens/f519c0d2-0551-4855-8c27-b353efbe7d85) centers recording elapsed/stop; [Krea AI](https://mobbin.com/screens/dd7edfc3-286b-4181-8f2c-090b31d451e3) keeps recording controls, timeline and state together; [Suno](https://mobbin.com/screens/d82f95a1-7d66-4997-bb38-ea323c6f6639) gives recording a clear dismiss action. Adapt these control hierarchies to Revoice's inline graphite surface without modal interruption.

Historical installer draft (superseded below): `dmg-background.swift` draws a static 720 × 460 graphite surface with a native system semibold Revoice title, pearl installation instruction, muted supporting copy, a thin separator, and a lime arrow connecting the app and Applications positions. `build-beatrice-dmg.py` sets Finder icon view, 100px icons, 14px native filename labels, and fixed icon centers at (190, 230) and (530, 230). Finder supplies the app and Applications icons and the drag interaction; the artwork is their background, not an interactive app screen. Its one action reads “Drag Revoice into Applications,” followed by guidance to open the installed app. The footer identifies the internal preview and Apple Silicon/macOS 13+ target.

This is a source-grounded extension of the incumbent graphite world. Its installation-only composition and artwork values are not new global tokens or a replacement type scale. The app's existing palette, controls, animated avatars, and responsive layout remain the design authority. The original draft was visually reviewed and replaced at the user’s request; it is retained here as historical context. The existing legacy sidecar and historical hero-reference comparison are not migrated or resolved by this release note. The installer's 10px footer text is an observed limitation, not a general text-size rule.


### Native installer revision · 2026-10-06

The user rejected the Finder white filename plates and explicitly requested a click-to-install animation. The DMG now opens a separate native SwiftUI installer with graphite ground, pearl typography and a lime primary action. Installation travels visually from app to destination with one eased one-second transition, disabled under Reduce Motion. Actual copying uses an activity indicator rather than invented percentage progress. Completion offers Open Revoice. Copy and open failures use separate recovery actions. A minimal pearl Finder entry surface replaces the white-plate layout. This revises only installation; the accepted in-app voice library stays unchanged.


### Dual installation and header refinement

The user restored the requirement for both drag-and-drop and button installation. Finder shows Revoice.app, Applications and the guided installer. The native installer also exports the actual app file URL via a drag provider and validates drops against its own payload before invoking the same guarded installation flow. It uses the actual macOS Applications icon. The header reads Revoice at left and Meet your next voice at right; the redundant ready status and FOR YOUR MAC label are removed. Three fine gradient strands form the curved guide. App motion follows an animatable parabolic position; reduced motion still disables travel.


Final waveform revision: user confirmed native drag-and-drop works. The header weights now use bold Revoice and semibold supporting headline. Parallel decorative strands are replaced by a single curved waveform of 39 short amplitude bars, with a traveling brightness pulse only while copying or hovering over the destination. Idle and Reduce Motion modes do not animate the waveform. App travel adds a restrained scale/tilt over the parabolic path. This motion reports activity, not a percentage or physical copy progress.


### 0.2.1 restoration

The approved native installer is preserved exactly: graphite, bold Revoice/header, 39-bar parabolic wave, genuine app/Applications icons, drag/drop and lime Install button. Finder now exposes only Install Revoice.app with a minimal matching graphite entry screen; the actual app is under .payload. The native installer resolves that payload while retaining compatibility with earlier root-level layouts. DMG volume/version changed to avoid confusion with previously mounted identically named releases. This supersedes the pearl three-icon Finder entry.

The native menu adds Settings, Audio (conversion, monitor, mute, Release/Resume microphone) and Window actions with keyboard shortcuts and state-aware availability. Release closes audio streams and persists pause; device refresh does not resume capture. The advanced panel adds a Noise reduction switch, using an existing row pattern. Voice volume applies only to conversion; natural passthrough is not boosted by that control. Accepted app visual identity is otherwise preserved. Detector advisories concern existing approved shadows/removal colors and a stale design sidecar; no broad redesign was performed.
