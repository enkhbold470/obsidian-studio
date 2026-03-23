# Design System Specification: High-End Video Editorial

## 1. Overview & Creative North Star
**Creative North Star: "The Obsidian Studio"**

This design system is built to transform a functional utility into a premium cinematic environment. Moving away from the "cluttered dashboard" trope, "The Obsidian Studio" treats the UI as a dark, high-end editing suite where the interface recedes to let the content—the video—be the hero. 

The aesthetic is defined by **Tonal Depth** and **Asymmetric Focus**. We break the traditional grid by using expansive negative space (breathing room) contrasted with dense, high-precision control panels. By utilizing layered surfaces instead of rigid lines, we create a fluid, sophisticated workspace that feels "molded" rather than "assembled."

---

## 2. Colors & Surface Philosophy
The palette is rooted in deep, charcoal-ink tones, punctuated by high-energy electric accents.

### The Color Tokens (Material Design Mapping)
- **Primary (Electric Purple):** `#b6a0ff` (Primary), `#7e51ff` (Primary Dim)
- **Secondary (Neon Blue):** `#00e3fd` (Secondary), `#00d4ec` (Secondary Dim)
- **Tertiary (Soft Rose/Punch):** `#ff96bb` (Tertiary)
- **Backgrounds:** `#0e0e0e` (Surface), `#1a1a1a` (Surface Container)
- **Accents/Errors:** `#ff6e84` (Error)

### The "No-Line" Rule
To achieve a high-end editorial feel, **1px solid borders are strictly prohibited for sectioning.** Do not use lines to separate the timeline from the preview or the sidebar from the stage. 
- **Method:** Define boundaries through background shifts. Place a `surface_container_high` (#20201f) property panel against a `surface` (#0e0e0e) workspace. The eye perceives the edge through the shift in value, creating a cleaner, more expensive look.

### Surface Hierarchy & Nesting
Treat the UI as physical layers of obsidian glass.
1.  **Level 0 (Base):** `surface` (#0e0e0e) – The main application backdrop.
2.  **Level 1 (Panels):** `surface_container_low` (#131313) – Non-interactive structural areas.
3.  **Level 2 (Active Areas):** `surface_container` (#1a1a1a) – Main editing timeline or sidebars.
4.  **Level 3 (Interactive Elements):** `surface_container_highest` (#262626) – Cards, hovered states, and active tool settings.

### The "Glass & Gradient" Rule
For floating menus (e.g., playback controls over video), use **Glassmorphism**:
- **Background:** `surface_container` at 60% opacity.
- **Blur:** 12px-20px backdrop-blur.
- **Gradients:** Use a subtle linear gradient from `primary` to `primary_dim` for "Render" or "Export" buttons to provide a "lit from within" soul.

---

## 3. Typography
We employ a dual-typeface strategy to balance high-end editorial vibes with technical precision.

- **Display & Headlines (Manrope):** Used for large-scale branding, project titles, and modal headers. Its geometric yet warm curves provide the "Signature" feel.
    - *Headline-LG:* 2rem / Manrope (Bold)
- **Interface & Data (Inter):** Used for the dense "working" parts of the UI—timecodes, layer names, and tooltips. Inter’s high x-height ensures legibility at small sizes.
    - *Title-SM:* 1rem / Inter (Medium) — For panel labels.
    - *Body-SM:* 0.75rem / Inter (Regular) — For technical metadata.
    - *Label-SM:* 0.6875rem / Inter (Bold, All Caps) — For button labels and micro-interactions.

---

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering**, not drop shadows.

- **The Layering Principle:** A "floating" card should be `surface_container_highest` set against a `surface_dim` backdrop. This creates "soft lift."
- **Ambient Shadows:** Only use shadows for top-level modals. Use a `16` blur radius with 6% opacity, tinted with the `primary` color (#b6a0ff) rather than black. This mimics the glow of a high-end monitor in a dark room.
- **The "Ghost Border" Fallback:** If a divider is mandatory for accessibility (e.g., in a high-density timeline), use `outline_variant` (#484847) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons
- **Primary (Action):** `primary` background with `on_primary` text. Use `roundedness-md` (0.75rem). Use a 2px inner-glow (white at 10% opacity) on the top edge to create a "tactile" feel.
- **Secondary (Utility):** No background, `outline` border (Ghost style), `primary` text.
- **Tertiary (Ghost):** No background, `on_surface_variant` text. High contrast on hover.

### Video Timeline & Tracks
- **No Dividers:** Use `surface_container_low` for the track background and a `surface_container_high` for the active clip.
- **Active State:** Clips currently being edited should have a subtle `secondary` (#00e3fd) outer glow rather than a thick border.

### Input Fields
- **Styling:** Use `surface_container_lowest` for the field background. 
- **States:** On focus, the background remains dark, but the "Ghost Border" becomes `primary` at 100% opacity.

### Tooltips
- **Styling:** `surface_bright` background with `on_surface` text.
- **Shape:** `roundedness-sm` (0.25rem). 
- **Motion:** 150ms "Slide and Fade" from the direction of the cursor.

### Specialized Component: The "Scrub" Head
- The playhead should be a 2px vertical line of `secondary` (#00e3fd) with a glassmorphic "handle" at the top to ensure it never gets lost against complex video frames.

---

## 6. Do's and Don'ts

### Do
- **DO** use the `20` (4.5rem) spacing token for margins between major functional blocks (Preview vs. Timeline). Space is luxury.
- **DO** use `tertiary` (#ff96bb) for "Destructive" or "Warning" actions to keep the interface looking sophisticated rather than using a standard "Alert Red."
- **DO** use minimalist, 1.5px stroke weight line icons.

### Don't
- **DON'T** use 100% white (#FFFFFF) for body text. Use `on_surface_variant` (#adaaaa) to reduce eye strain in dark mode. Reserve pure white for headlines and active states.
- **DON'T** use `roundedness-none`. Everything in this system has a slight radius to feel approachable and modern.
- **DON'T** stack more than three levels of surface containers. If you need more depth, use a Backdrop Blur.

---

## 7. Technical Tokens Reference

| Category | Token | Value |
| :--- | :--- | :--- |
| **Corner Radius** | `DEFAULT` | 0.5rem |
| | `md` | 0.75rem |
| **Spacing** | `4` (Gutter) | 0.9rem |
| | `8` (Section) | 1.75rem |
| **Typography** | `display-md` | Manrope / 2.75rem |
| | `body-md` | Inter / 0.875rem |
| **Colors** | `surface` | #0e0e0e |
| | `primary` | #b6a0ff |
| | `secondary` | #00e3fd |