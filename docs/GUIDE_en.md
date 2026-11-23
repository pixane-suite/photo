# Pixane Photo user guide

Pixane Photo is a photo editor for Windows that retouches images with an AI running **on your own PC**
(no subscription, no photos sent over the Internet). It is part of the **Pixane Suite**.
This guide explains every tool and every setting: **what it is for** and **how to use it**. It is updated with
each new feature.
(Version française : `docs\GUIDE.md`.)

**Who is it for?** Pixane Photo is designed for people who are new to photo editing, or have little experience with it: the tools go straight to the point, the AI takes care of the hard work and the help explains every setting step by step. Pixane Photo does not claim to replace programs such as Photoshop, GIMP or Krita, which remain the reference for advanced work: it aims to make photo editing accessible to everyone.

## Before you start: an AI that runs 100% on your PC

- **No online AI.** All of Pixane Photo's AI actions (Erase, Fill, Expand, Upscale, object selection, background,
  noise reduction, sharpening, restoration…) run **on your computer**, with models installed on your disk. **No photo
  is ever sent over the Internet**; no account, no subscription, no usage limit. The Internet is only used to
  download the AI engine once (and its updates, if you accept them). After that, Pixane Photo works even offline.
- **Speed depends on your PC, above all on the graphics card**: it does the AI's calculations. **The more powerful it
  is and the more memory it has, the faster the processing.** A recent card with 12, 16 or 24 GB of memory is much
  faster than the test PC's; a more modest card is slower. System memory (RAM) matters too: when the graphics card
  runs out of memory, part of the model goes through RAM, which slows things down.
- **Times measured** on the test PC (NVIDIA RTX 3060 Ti 8 GB, 32 GB of RAM):

| Action | Time |
|---|---|
| AI engine start-up (when Pixane Photo opens) | about 20 seconds |
| Object selection, quick selection | about 1 second |
| Remove background, select subject, Remove tool (J), Reduce noise | a few seconds |
| Sharpen (AI) | 15 to 20 seconds |
| Fill, Expand image | about 1 minute per proposal |
| Erase | about 2 minutes |
| Sharp upscale | 20 to 30 seconds per 1024 px tile |
| Restore an old photo | about 2 minutes per proposal |

The first use of a model after start-up takes a little longer (it is loaded into memory).

For **Create an image**, **Edit with an instruction** and **Restore**, Pixane Photo measures the time on your PC: the window then shows “about … each, measured on this PC”. Before the first measurement, it gives the time on an RTX 3060 Ti, warning that it depends on the PC.

### System requirements

| | Minimum | Recommended |
|---|---|---|
| **System** | Windows 10 or 11, 64-bit | Windows 11, 64-bit |
| **Graphics card** | NVIDIA, **8 GB** of memory (for example RTX 3060 Ti, 3070, 4060) | NVIDIA RTX, **12 GB or more** (for example RTX 3060 12 GB, 4070, 4080, 4090) |
| **RAM** | 16 GB (Flux actions are then slow) | **32 GB** |
| **Disk** | 35 GB free for the AI engine | 60 GB free (with Flux Schnell and Flux Kontext), on an SSD |
| **Processor** | recent 4-core | 6 cores or more |

Pixane Photo has been tested on an **RTX 3060 Ti (8 GB) with 32 GB of RAM**. The minimum is an estimate: it has not been
tried on other PCs. **Without an NVIDIA card** (AMD or Intel card, laptop without a graphics card), Pixane Photo opens and
edits normally (layers, text, adjustments, filters, export…), but the AI actions do not work.

---

## 1. The window

| Area | Purpose |
|---|---|
| **Top bar** | Open, Save, Undo / Redo, settings of the chosen tool (size, New / Add / Remove…), zoom |
| **Tools (left)** | Hand, Move, selection tools, retouching tools, Crop, Text. A small triangle on a button = several tools: **right-click** (or click and hold) to choose |
| **"Text" panel (left)** | Text settings, shown with the Text tool (see chapter 7) |
| **Tabs (above the photo)** | One tab per open photo (as soon as there are two); a "•" marks a modified photo |
| **Rulers** | Above and left of the photo, in pixels (View > Rulers, Ctrl+R) |
| **Photo (centre)** | The photo; the selected area appears in transparent red |
| **"Artificial intelligence" panel (right)** | Erase, Fill, Expand image, Upscale |
| **"Layers" panel (right, below)** | The layers of the image (see chapter 6) |
| **Status bar (bottom)** | AI engine status (coloured dot), photo size |

**Colours**: Pixane Photo uses the accent colour chosen in Windows (Settings > Personalization > Colors)
and follows the Windows light / dark mode. **View > Theme** menu: *Same as Windows*, *Light* or *Dark*.
The sun / moon button in the top bar also switches between light and dark.

**Language**: Pixane Photo is available in **French** and **English**. By default it uses the Windows language
(French if Windows is in French, English otherwise). **View > Language** menu: *Same as Windows*, *Français*
or *English*; Pixane Photo then offers to restart to apply the language (the AI engine restarts too, about
20 seconds). Standard buttons (Yes / No / Cancel, right-click menu) follow the same language.
Layer names that already exist keep their original language.

**Interface size**: **View > Interface size** menu: from **75 %** (very compact) to **200 %**. Everything changes
together: text, icons, buttons, panels. This percentage comes on top of the Windows scaling: on a small laptop
screen, choose 85 % or 75 % to save space; on a 4K screen, 125 % to 200 %. Pixane Photo offers to restart to apply
it (the open image is reopened). **View > Tool icon size** (*Small*, *Normal*, *Large*, *Very large*) changes only
the tool bar on the left, right away.

**Preferences** (**Edit > Preferences…** menu, Ctrl+,): all lasting settings in one place, in tabs. Nothing changes
before **OK**; **Cancel** leaves everything as it was. The same settings stay in the menus.
- **Display**: theme, language, interface size, tool icon size, quick access bar, grid spacing. The language and the
  interface size change at the next start (Pixane Photo offers to restart); the rest right away.
- **Installed features**: *Similar font search*, *Spelling and hyphenation* and its languages: the options chosen at
  installation, which can be changed here.
- **Artificial intelligence**: *Put results in a new layer*, *Expand the image in full definition*; the AI engine
  folder and the *Install or complete the AI engine…* button.
- **Saving**: how often the **recovery copy** is made (every 1, 3, 5 or 10 minutes, or never) and the **images
  folder** offered to open and save.
- **Updates**: *Check for updates at startup*, and a button to check right now.

**AI engine**: when it starts, Pixane Photo launches the AI (ComfyUI) in the background, without a window. Allow about
20 seconds. The dot at the bottom left turns green when the engine is ready; AI actions are greyed out before that.

---

## 2. Opening and saving

- **File > Open** (Ctrl+O): JPG, PNG, TIFF, WebP, BMP, **HDR** images **.exr** (OpenEXR) and **.hdr** (Radiance),
  and the **.piximg**, **.ora** and **.psd** (Photoshop) layered files.
  The photo is rotated according to the camera orientation.
- Camera **RAW files** (Canon .CR2 / .CR3, Nikon .NEF, Sony .ARW, .DNG, Fujifilm .RAF, Olympus .ORF, Panasonic
  .RW2, Pentax .PEF…): they open like a photo, developed with the camera's white balance (LibRaw library); then
  retouch with the adjustments (Levels, Curves, Balance…). The RAW file is never replaced: **Save** suggests
  another file (JPG, or .piximg if there are layers).
- **Save** (Ctrl+S), **Save as** (Ctrl+Shift+S):
  - **.piximg** (Pixane Photo project): Pixane Photo's own format. Keeps **everything**: layers (names, order, visibility,
    opacity, lock), **editable texts** and **editable layer styles**. Suggested automatically when the image has several layers or a text.
  - **.ora** (OpenRaster): to **share with Krita or GIMP** (open format). Keeps the layers, but texts become
    images.
  - Good to know: a .piximg file is built like an .ora file; renamed to .ora, it also opens in Krita or GIMP.
  - **.psd** (Photoshop): to **work with Photoshop**. Keeps the layers (names, order, visibility, opacity, lock);
    texts become images. A photo opened from a PSD is suggested as PSD.
  - **PSD files opened in Pixane Photo**: RGB or greyscale, 8 or 16-bit, with layers, **groups**, **layer masks**,
    **blend modes** and **layer styles** (drop and inner shadow, glows, stroke, bevel, colour and gradient overlays),
    which stay editable. Pixane Photo does not reproduce Photoshop adjustment layers, clipping masks or groups in "pass
    through" mode (opened as Normal): a message says so when opening, as the result may then look different. A CMYK
    PSD opens flattened (a single layer). Large .psb documents are not supported.
  - **PSD files saved by Pixane Photo**: layers, groups, masks and blend modes are kept; styles are baked into the
    pixels; an adjustment layer becomes an image layer (the adjusted result).
  - **JPG** (quality 95), **PNG**, **TIFF**, **WebP**: the **flattened** image (what you see, layers merged).
    A message reminds you of this if the image has several layers.
  Camera information (EXIF) and the colour profile are kept.
- **Undo** (Ctrl+Z) / **Redo** (Ctrl+Y or Ctrl+Shift+Z): every edit and every selection can be undone (30 steps).
  The mouse **back** and **forward** side buttons do the same.
- **During work not yet confirmed** (Transform, Expand frame, Crop): Undo (or the back button) undoes **the last
  gesture** of that work (e.g. the rotation, keeping the size); at the start, it abandons the work. Redo (or the
  forward button) redoes the undone gesture.
- **History panel** (tab next to "Layers"): the list of steps. Click a step to go back to that moment; click a step
  further down to redo the next ones. A new edit discards the steps "ahead".
- **File > Recent files**: the last 10 images opened or saved (*Clear the list* empties it).
- **Several photos at once**: *Open* accepts several files at a time (Ctrl+click or Shift+click in the dialog),
  and several files can be dropped on Pixane Photo. Each photo has its own **tab** and its own **Undo** (Ctrl+Z only
  affects the photo shown). Switch photos: click the tab, **Ctrl+Tab** / **Ctrl+Shift+Tab**. **File > Close photo**
  (Ctrl+W, or the tab's cross) asks to save if needed. Opening a photo that is already open just goes to its tab.
- **Autosave**: every 3 minutes, each modified photo is copied (layers, texts, styles and masks included) to
  `%LOCALAPPDATA%\Pixane\recuperation`, without slowing you down. If Pixane Photo closes badly (crash, power cut), it
  offers to **reopen these copies** the next time it starts; they open "to be saved", with the original file name.
  The copies are deleted when the photo is saved or closed, and when Pixane Photo closes normally.
- **If an error occurs**: when a command fails, Pixane Photo shows it and writes it to
  `%LOCALAPPDATA%\Pixane\erreurs.log` (useful to report the problem).
- **File > Export as…** (Ctrl+Alt+Shift+W): a copy **for a normal send** (printer, friend, USB stick): full size,
  full quality, resolution, colour profile and camera information kept. JPEG, PNG (with transparency), TIFF or WebP.
  The open photo does not change (it still needs saving if it was modified); Pixane Photo never offers to overwrite the
  original photo and remembers the last format chosen.
- **File > Export for web…** (Ctrl+Alt+Shift+S): a light copy for the Internet, without touching the photo.
  - **Format**: JPEG (photos), **WebP** (lighter at the same quality, keeps transparency), PNG (lossless).
  - **Shrink: longest side** (for example 2048 px); never enlarged.
  - **Quality** (30 to 100; about 80 is enough for the web).
  - The **file size** is shown live.
  - Camera information (EXIF: model, date, sometimes location) is **removed** by default (box to keep it).
    Suggested name: `<photo>_web.jpg`.
- **File > Batch processing…**: the same work on **a whole folder** of photos.
  - **Photos to process** (source folder, never modified) and **Results in** (another folder).
  - Options: **Shrink** (longest side), **Auto adjust** (brightness, contrast, temperature, like the Auto button),
    **AI upscale ×2** (RealESRGAN), **Remove background** (results as transparent PNG), **Format** (keep, JPEG,
    WebP, PNG) and quality, **Add to name** (e.g. `_web`).
  - A bar shows progress; **Stop** finishes the current photo then stops. A photo that causes a problem is listed
    at the end; the others are done.
  - **Action**: an action recorded in the **Actions** panel (see chapter 9) is played on each photo.
  - RAW files in the folder are processed too.
  - Safety: if the results would go into the same folder under the same name, Pixane Photo refuses (the originals
    would be replaced).
- **File > Print…** (Ctrl+P): the visible image (all layers), with a **page preview**.
  - **Printer**, **Paper** (A4, A5, A3, Letter, 10 × 15, 13 × 18, 20 × 30 cm), **Orientation** (automatic: like
    the image), **Margins**, **Copies**.
  - **Size**: *Fill the page* (within the margins), *Actual size* (from the image resolution) or *Chosen width* in
    cm.
  - Pixane Photo shows the size on the sheet and the dots per inch; under 150 it warns that the print may be blurry
    (AI > Upscale can help).
- **File > New image…** (Ctrl+N): an empty image, as in Photoshop. A **preview** shows the shape of the sheet,
  its background and the guides (bleed, safe area).
  - **Ready-made formats** (on the left): **album covers** (CD, 12-inch and 7-inch vinyl, 3000 × 3000 px for
    Spotify, Deezer, Apple Music), **books** (pocket, novel, Amazon KDP, e-book), **social media** (Instagram, Story,
    Facebook, YouTube, X), **print** (A3, A4, A5, photos, posters, business card, flyer), **screen** (HD, Full HD,
    4K). **Save this format…** keeps your own formats in **My formats** (size, unit, resolution, bleed, safe area, mode and background); the last format used is offered next time.
  - **Width, height and unit**: pixels, inches, centimetres, millimetres, points or picas (1 inch = 2.54 cm =
    72 points = 6 picas). Changing the unit does not change the image.
  - **Orientation**: Portrait or Landscape swaps width and height.
  - **Resolution** (dpi, dots per inch): **300** for print, **72** for screen. It is **kept in the file** (.piximg,
    PSD, JPEG, PNG, TIFF): a printer will see the right size.
  - **Mode**: RGB colour or **greyscale** (see *Image > Mode*). A new image is in **8 bits per channel** (16.7 million
    colours, like JPEG, PNG and the web); for fine work, switch it to **16 bits** afterwards (*Image > Mode >
    16 bits per channel*).
  - **Background**: white, transparent, black or a colour of your choice.
  - **Bleed** (print): band added all around, trimmed off by the printer (usually 3 mm): the background must run to
    the edge of the image. **Safe area**: margin inside the finished size where nothing important goes (text,
    face). **Guides** are placed automatically on these two lines.
  - At the bottom: the size in pixels, the printed size and the memory used.
- **File > Export for print (CMYK)…**: for a printer who asks for CMYK (the four inks). Pixane Photo works in RGB and
  converts when exporting, as printers recommend.
  - **Format**: TIFF (the safest), PDF or JPEG.
  - **CMYK profile**: those installed in Windows, nothing to download. Ask your printer which one they use; in
    Europe it is often **Coated FOGRA39** (coated paper).
  - **Rendering intent**: *Perceptual* for photos, *Relative colorimetric* for logos and flat colours. **Black point
    compensation**: ticked, shadows keep their detail.
  - The **resolution** is written in the file; the photo is not changed (suggested name: `<photo>_cmyk.tif`).
  - Before exporting: **View > Print preview (CMYK)** (Ctrl+Alt+Y) shows on screen the colours as they will come out
    (very bright blues and greens often get duller). Click it again to go back to the normal view; the image is
    never changed.
- **File > New image from clipboard** (Ctrl+Alt+V): opens the copied image (screenshot, other program…).
  **Ctrl+V** with no photo open does the same.

---

## 3. Moving around the photo

| Action | How |
|---|---|
| Zoom | Mouse wheel (around the cursor), Ctrl++ / Ctrl+-, magnifier buttons |
| Fit to window | Ctrl+0 |
| Actual size (100%) | Ctrl+1 |
| Move the view | **Hand** tool (H), or hold **Space** and drag, or drag with the **middle button** |
| Move **a layer** | **Move** tool (V): only the selected layer moves (the Hand only moves the view) |

### Rulers, guides and grid (View menu)
- **Rulers** (Ctrl+R): in image pixels, 0 at the top-left corner of the photo; a line follows the mouse.
- **Guides**: drag from a ruler onto the photo to place a blue line (horizontal from the top ruler, vertical from
  the left one). With the **Move** tool (V), grab a guide to move it (the cursor becomes a double arrow
  over it); dragged off the photo, it disappears. *New
  guide…* places one at an exact position, *Clear guides* removes them all, Ctrl+; hides or shows them. They are
  saved in the .piximg file.
- **Grid** (Ctrl+'): regular lines over the photo; *Grid size…* sets the spacing (100 px by default).
- **Snap** (Ctrl+Shift+;, on by default): rectangle selection, gradient and shapes snap to guides, to the photo's
  edges and to the grid (when shown), within 8 screen pixels.

---

## 4. Selecting (telling the AI where to work)

The selected area appears in **transparent red**. You do not need to "outline" an object:
you can simply **paint over it**.

The selection tools share **two buttons** in the left bar (small triangle): the "by hand" tools and the
"automatic" tools. **Right-click** the button, or click and hold, to choose; or press their key directly.

| Tool | Key | Use |
|---|---|---|
| **Rectangle** | M | Rectangular selection |
| **Lasso** | L | Draw an outline freehand, button held down; the shape is closed automatically |
| **Selection brush** | B | Paint the area. Ideal for an object, some text, a wire… |
| **Selection eraser** | E | Remove from the selection by painting |
| **Object selection** (AI) | O | Drag a frame around an object, or click on it: the AI cuts it out |
| **Quick selection** (AI) | Q | Roughly paint over the object: the AI finds its outline |
| **Magic wand** | W | One click on a colour: the whole area of similar colour (no AI) |
| **Text selection** | Y | A frame around a text: only the letters, thin strokes included (no AI) |

- **Rectangle and lasso**, as in Photoshop: a new selection **replaces** the old one. Holding **Shift** when you
  start drawing **adds** to the selection, **Alt** **removes**. A single click without drawing **deselects**.
  The **New / Add / Remove** pills in the top bar choose the mode without a key.
- **Selection brush**: it always adds to the selection; **Remove** pill or holding **Alt**: it removes (like the
  selection eraser).
- **Brush size**: "Size" slider in the top bar, or the `[` and `]` keys.
- **Select** menu: *Select all* (Ctrl+A), *Deselect* (Ctrl+D), *Invert* (Ctrl+Shift+I).
- **Arrow keys** (with a selection tool: rectangle, lasso, selection brush, magic wand, quick or object selection):
  the selection moves by **1 pixel** (Shift: **10 pixels**). Only the outline moves, not the image; a single Ctrl+Z
  undoes all the presses.
- **Select > Modify selection**: *Expand…* or *Shrink…* by a number of pixels, *Soften edges…* (gradual edge,
  useful for image adjustments).
- **Select > Select subject (AI)** (Ctrl+Alt+S): the AI finds the main subject (person, animal, object) and selects
  it. See chapter 5, "Subject and background".

### Object selection and quick selection (AI)
They use Meta's **SAM 3.1** model (1.6 GB, installed with the AI engine). The AI understands the **whole object**
(a person, a car, a piece of furniture…), even when its colours vary, and follows its real outline. About one second
per request (a few seconds the first time).
- **Object selection (O)**: drag a **frame** around the object, or **click** on it. Like the rectangle: the new
  selection replaces the old one; **Shift** adds, **Alt** removes (or the New / Add / Remove pills).
- **Quick selection (Q)**: roughly **paint** over the object (on it, or along its outline). As in
  Photoshop, each stroke finds **its own** object, which is **added** to the selection: a stroke on a title then a
  stroke around a person give the title + the whole person. Green dots show what the AI must keep. **Alt + paint**
  over a part to leave out (red dots): the AI corrects the objects already found. A selection cleared (Ctrl+D) or
  changed by another tool starts again from scratch; so does **Esc**.
- Ctrl+Z undoes each step. Fine-tune the result afterwards with *Modify selection* (expand, soften…).

### Text selection (Y)
To take a **text** (cover title, handwritten letters, gradient or outlined text) without the background, even when a
similar colour touches it. No AI, in less than a second. In the magic wand's group (right-click its button) or key
**Y**.
1. **Drag a frame around the text**, leaving a little background all around: Pixane Photo looks at what touches the edge
   of the frame (the background) and selects what stands out from it (the letters). Very thin strokes and letter
   edges are taken softly (progressive selection). Nothing outside the frame is taken.
2. **Correct with a click**, inside that frame:
   - **Alt + click** on an extra piece (a bit of photo): it is removed;
   - **Shift + click** on a missed piece: it is added;
   - with **Ctrl** as well: this whole colour in the frame (handy for many fringes or spots).
3. **Shift + frame**: adds another text; **Alt + frame**: removes the text in that frame.
- **Solid letters** (tick box): the inside of the letters is taken too (patterns in a letter, inside of O and A).
  Handy to erase or move a text. Without it, only small holes (JPEG grain) are filled.
- Tips: a frame that cuts the letters a little on one side does not matter. If the background behind the text is a
  busy photo, a tight frame helps; a piece of photo entirely inside the frame is removed with Alt + click.
- Ctrl+Z undoes the last frame or the last correction.

### Find a similar font
Which font was used for this title? Pixane Photo searches **the fonts installed on the PC** for the ones that look most
alike (no Internet, nothing is downloaded).
1. Select the letters with **Text selection (Y)** (a solid block does not work: only the letters are needed).
2. **Selection > Find a similar font…**, or the **Similar font…** button in the tool bar.
3. **Type the same letters** as in the image, keeping capitals (separate lines with "/"), then **Search**. A few
   seconds (the more fonts are installed, the longer it takes).
4. The closest fonts are shown first, written with your letters, with their likeness in %.
   - **Apply to the chosen text**: if the chosen layer is a Pixane Photo text, it takes this font;
   - **Create a text with this font**: new text layer in place of the letters, with their colour (the letters in
     the image stay: erase them afterwards if needed);
   - **Copy the name** of the font.
- **Option** (box in the installer, or **View > Similar font search**): to be fast, Pixane Photo prepares the list of
  your fonts **once only**, in the background, one minute after starting. The time depends on the **number of
  installed fonts**: about 1 min 20 (and 15 MB) for 1,200 fonts. Unchecked: the feature is
  hidden, nothing runs in the background, and this list is deleted.

### Magic wand (W)
One click on a colour selects the area of similar colour. No AI, instant.
- **Adjust by dragging**: after the click, **keep the button down and drag right** (wider) **or left** (narrower): the
  selection follows live. The tolerance found is kept for the next click.
- **Tolerance** (0 to 255, 32 by default): accepted colour difference. Colours are compared the way the eye sees
  them, and the starting colour is taken over 3 × 3 pixels: photo noise matters less.
- **Contiguous** (ticked): only the area clicked; unticked: all similar colours in the image.
- **Soft edges** (ticked): gradual edge, no jaggies.
- **Fill holes**: adds what is completely surrounded (birds in a sky, reflections on an object…).
- **Visible image** or **Chosen layer**: what the colours are compared on.
- Shift adds, Alt removes, like the rectangle.

### Colour range (Select menu)
Selects **all the pixels of a colour**, across the whole image (the magic wand only takes neighbours).
- **Click** the colour you want in the preview; **Shift+click**: add a colour; **Alt+click**: remove one.
- **Tolerance**: how far similar colours are taken (soft edges). A darker red (in the shade) counts as red.
- The preview shows the **selection** (white = selected) or the **image**; the selection is also shown on the photo.
- *Invert*: everything but these colours. **Selection**: new, add to the selection or subtract from it.

### Refine edge (Ctrl+Alt+R, Select menu)
For a rough selection around **hair, fur, foliage or soft edges** (for example after *Select subject* or a quick
lasso): Pixane Photo recomputes the edge from the photo's colours.
- **Radius**: width of the band recomputed around the edge. Increase it until the strands appear; outside this
  band, nothing changes.
- **Smooth**: softens a jagged edge. **Edge contrast**: sharper edge. **Shift edge**: negative pulls it in (removes
  a fringe of the old background), positive pushes it out.
- **View**: the subject **on black**, **on white**, the mask in **black & white**, or the selection in red. Pick a
  background that contrasts with the old one to judge the edges.
- **Output**: a **new selection**, or the **mask of the chosen layer** (the background is then hidden, not erased:
  see *Layer masks*).
One step in Undo. The computation takes one to three seconds on a large photo.

### Cut, copy, paste, delete (Edit menu)
They work on the **layer chosen** in the Layers panel:
- **Copy** (Ctrl+C): copies what is selected (the whole layer if there is no selection). The copy keeps its
  transparency; it can also be pasted into another program.
- **Cut** (Ctrl+X): copies, then erases the selected area (it becomes transparent).
- **Paste** (Ctrl+V): puts the copied image in a **new layer**, at **the same place** if it comes from Pixane Photo, in the
  centre if it comes from elsewhere (screenshot, another program…). Then move it with the Move tool (V). To enlarge
  or shrink it: **Ctrl+T** (see *Transform layer*).
  - **Image larger than the photo**: it arrives **reduced to fit entirely**, with the *Transform* frame already
    open. Adjust its size and position, then press **Enter**. Nothing is ever cut off: what extends beyond the
    canvas is kept in the layer (see *Pixels outside the canvas*).
- **Delete selection** (Del): erases the selected area of the layer (transparent).

A **locked** layer is protected; a **text** that is cut or deleted becomes an image. Ctrl+Z undoes everything.

The other tools: **Move** (V) moves the content of the **chosen layer** (a moved text stays editable; what goes
outside the canvas is kept and can be brought back; refused on a locked layer).
- **Arrow keys** (Move tool): nudge the chosen layer (or the text) by **1 px**, **10 px** with Shift. Holding a key
  down: a single step in Undo. They also work right after a click in the Layers panel, and nudge the Transform
  (Ctrl+T) frame in progress.
- A **frame with handles** surrounds what is on the layer (or only the selected part, if there is a selection):
  **drag inside** to move; **a corner** changes the size keeping the proportions (Shift: free); **the middle of a
  side**, only the width or the height; **just outside a corner** (cross cursor), you rotate. As soon as a handle is
  touched, it is the *Transform* mode (like Ctrl+T): **Enter** to keep, **Esc** to cancel.
- **Quality**: the layer is resized as in Photoshop, each pixel taking into account all
  the ones it replaces: a reduced image (even a lot, for example after an Upscale) stays clean, without broken lines
  or grain. Without rotation, the layer is placed on whole pixels: a simple move never blurs it. During the gesture, the
  preview is fast; **as soon as the mouse is released**, the layer is at full quality, even if you move on without
  validating. Same quality for *Image > Image size* and for the Upscale (layer brought back to its size, other
  layers enlarged). A simple move changes no pixel.
- **No loss when shrinking then enlarging again** (like a Photoshop *smart object*, with nothing to do): each layer
  keeps its **best version** (for example the one after an Upscale). Shrink, validate, do something else, save,
  reopen the project… then enlarge again: Pixane Photo starts again from this best version, and the image comes back
  **exactly as it was, pixel for pixel**, up to its original size. Works with Move (handles), Ctrl+T,
  *Image > Image size*, rotate, flip, crop, align. It is saved in the **.piximg** project (which gets a little bigger).
  - If you **change the pixels** of the layer (brush, eraser, AI, filter…), the changed version becomes the new
    reference (the old one would erase the work).
  - Enlarging **beyond** the best version makes the image softer: those pixels never existed (use the Upscale).
  - Transforming only a **selected part** of the layer: the current version becomes the reference.
  - In Ctrl+T, the percentages are counted from the best version (100 % = its original size).
- The **Show transform controls** box (at the top) hides it if it gets in the way. No frame on an empty, locked,
  hidden or text layer (a text changes size with the Text tool).

The **Layer eraser** (G) **really** erases the pixels of the
chosen layer (see chapter 6); it is grouped with the colour brush and the clone stamp.

**Tip (text, cursive, thin objects)**: cover each letter completely, edges included, with a brush slightly wider
than the stroke; don't forget the shadow or outline if there is one. Pixane Photo already enlarges the area a little
(about 16 px) to catch blurry edges.

---

## 5. AI actions

Each action offers **several results**: you pick the best one, as in Photoshop.
The result you keep goes **into the chosen layer** (the one highlighted in the Layers panel): it becomes part of it
and follows it when you move, transform or resize it. Ctrl+Z goes back. The AI always works on the image **as you
see it** (all visible layers together): so choose the photo's layer before starting.
- The result **does not go outside the selection**: the AI retouches a little around it for the join, but Pixane Photo
  only keeps the inside, plus a blend of a few pixels, so that no edge shows.
- **Transparent** areas (transparent background, cut-out logo, text alone) **stay transparent**: no black is added,
  neither in the proposals nor in the result (Upscale too). So that the AI sees clearly what is on them, Pixane Photo
  shows these areas on a plain contrasting background (dark behind white text, white behind a dark logo), then
  removes that background from the result, letter edges included.
- It goes into a **new layer** ("Erase 1", "Fill 2"…) when the chosen layer cannot receive it (text, group,
  adjustment layer, hidden or locked layer), or when there is no selection and the image has several layers
  (otherwise the others would be copied into it). A message at the bottom says so.
- **AI > Put results in a new layer** (tick box): each result goes into a new layer, as before; handy to compare
  with the original by hiding the layer.
- **What the AI looks at**: the **visible image** (all layers together, as in Photoshop), so that the result
  matches what you see around it. The result itself goes **only** into the selected layer (or a new layer). A
  hidden layer is not seen by the AI: to make it ignore a layer, hide it before starting.
- **Transparent holes** (for example the letters of a text cut out of a cover): with **Erase** and **Fill**, the
  holes that are in the selection and surrounded by the image are **filled**, opaque, with what surrounds them.
  Transparency that continues outside the selection (around a cut-out photo, beyond the edge of a cover) stays
  transparent.

### Result chooser
- Click a thumbnail to see it full size.
- **Zoom in to see the details**: **mouse wheel** (zooms under the mouse), **drag** to move around,
  **double-click** to switch between the whole image and actual size (100 %) and back. **Fit** and **100 %** buttons
  at the bottom; keys **+** / **-**, **0** (fit) and **1** (100 %). The zoom level is shown at the bottom left.
- The zoom and the spot you are looking at **stay the same** when you switch thumbnails or hold "see the original":
  you compare exactly the same detail (even after an Upscale, where the original is smaller).
- **Hold to see the original**: while the button is held down, the photo from before is shown.
- **More options**: runs the AI again for new versions (they are added to the previous ones). They always start
  again from **the original image**: the selected thumbnail is not used as a starting point.
- **Start from this one** (Erase, Fill, Expand): when an option is **almost right**, select it and click here. The AI
  starts again from that option, on the same area, and only redoes part of it: it keeps the overall shape and
  changes the details. The **Close ↔ Free** slider sets how much it may change (Close: small touch-ups, almost the
  same image; Free: the same idea, reworked more; in the middle by default, then your last setting). The variations
  are added to the thumbnails ("Variation of 2"…): you can always go back to an earlier option, or start again from
  a variation. Same time as an option (about 1 min each). A big shape flaw (misplaced object) is only fixed by
  moving towards **Free**.
- **Keep this result**: applies the chosen version (can be undone with Ctrl+Z). The selection (brush, lasso,
  rectangle) then disappears; Ctrl+Z brings it back with the previous photo.

### While computing
A window shows the current step, a **progress bar**, the elapsed time and the **estimated time left**.
**Cancel** stops the computation.

### Erase (Shift+E)
Removes what is painted in red and rebuilds the background.
- Two combined methods: **LaMa** (fast, erases cleanly), then a finishing pass with **Flux Fill** (more realistic).
- Results offered: 2 Flux versions + the "LaMa only" version.
- Also works on a thin selection (letters picked with the magic wand): every pixel touched by the selection is
  erased, even on a soft edge.
- Typical time: about 2 minutes (8 GB graphics card).

### Fill (Shift+R)
Redraws the area painted in red.
- **Without text** (recommended): the AI invents something that fits the rest of the photo. It starts from the
  background cleaned by LaMa: even next to a title, it does not invent letters again.
- **With text** ("Optional text" field, preferably in English): describes what you want to see instead.
- 3 options, about 1 minute each.

### Edit with an instruction (Shift+M)
Changes the selected area from what you write, keeping the style of the image: “replace the text "burn the fire"
with "Flame"”, “make the jumper red”, “replace the cup with a glass”, “remove the glasses”… (**Flux Kontext**
model, to be added in Install the AI engine).
- Select the area (brush, lasso, object selection…), then **Edit** (AI panel card or AI menu). Without a
  selection: the whole image.
- Write the instruction. **Examples**: choose one, it is inserted; replace the “…”.
- **Between quotes** (« … » or "…"): text to be written as is (never translated).
- **Important: the AI only understands English well.** An instruction in French, Polish or any other language,
  sent without translation, works badly: the AI guesses, and the result is often random (nothing changes, the text
  is copied instead of replaced, or replaced twice…). Two solutions, your choice:
  - install the **translator** (French → English, 290 MB, on your PC, nothing is sent over the Internet): you
    write in French, **Translate** shows the English sentence, which you can correct;
  - or write the instruction **directly in English** (the only solution for other languages for now).

  If your instruction does not look like English and is not translated, Pixane Photo warns you when you click Edit; you
  choose: **Install the translator…**, **Correct**, or **Send anyway**.
- Write the text between quotes **exactly as in the image** (accents, capitals).
- The translator
  It is installed by **Pixane Photo's setup program** (“Instruction translator” page), with the “Install the
  translator…” button, or with its box in **AI > Install the AI engine**
  (“Install” window, or “Complete the AI engine” if ComfyUI was already there): ticked while it is not installed,
  greyed out afterwards. **Translator folder… Change…**: you choose where to store it (by default,
  `%LOCALAPPDATA%\Pixane\traducteur`). Not inside the folder where
  Pixane Photo is installed (D:\Programmes\Pixane\Pixane Photo…): it is replaced at each update, Pixane Photo refuses it.
- The translator starts in the background as soon as the window opens (about ten seconds, while you write), then stays ready until Pixane Photo is closed: each translation is then almost instant.
- The AI works on a piece around the selection (more detail than with the whole image); the result is only kept
  inside the selection and where it really changes: the rest keeps its original pixels.
- **Layer with transparency** (text, logo without background): the AI sees this layer alone, and the result keeps
  a transparent background. Otherwise it sees the visible image and the result is opaque.
- Proposals: 1 to 4, about 2 to 3 minutes each on an RTX 3060 Ti (the window shows the time measured on your PC). Elaborate handwriting is well imitated but slightly less fine
  than the original; accents and long texts are sometimes misspelled: ask for more proposals.

### Expand image (Shift+A)
Extends the photo beyond its edges: the AI invents the rest of the scene.

Two frames appear on the photo:

| Frame | Look | Purpose |
|---|---|---|
| **Expansion frame** | white dashes, **square handles** in the accent colour | Drag it **outward**: the added area is shown as a grey checkerboard |
| **"Damaged edge" frame** | **red** dashes, round red **handles** | Drag it **inward**: the red hatched strip is a damaged edge (border line, stroke, blur, torn corner…) that will be **discarded, then redrawn** by the AI |

- When both frames are on top of each other (at the start), the **direction of your drag** decides:
  outward = expand, inward = damaged edge.
- **Shift** while dragging: the opposite side moves the same way (expand left and right at once, for example).
- **Automatic detection**: when opened, Pixane Photo finds damaged edges and already places the red frame on them:
  light or dark border lines, a **frame** or border of another colour, a **blurred edge**, a plain band (thumbnail
  bar, edge of a screenshot), up to 4% of the side. You can adjust it or set it back to 0.
- **Bar at the top of the photo**:
  - **Expand** row: what is added on each side, as a % of the photo (0 to 200%);
  - **Damaged edge** row: the strip to redo on each side, in pixels;
  - **final size** of the image;
  - **Start** (or Enter) / **Cancel** (or Esc);
  - **Description** row (optional): what the AI should add, for example "crowd, smoke, cloudy sky". When empty, the
    AI guesses from the image and may invent off-topic objects or people; a description guides it (without
    preventing everything: "crowd" can bring a person into the foreground). In French or English (translated on
    this PC if the translator is installed). **Describe (AI)**: the AI looks at the photo and writes the description
    itself (in English: kind of image, style, scene, background, lighting, colours), which you can correct before
    starting; a few seconds. This button needs the **Qwen3.5 2B** model (4.2 GB, Apache-2.0), optional: box in the
    installer and in *AI > Install the AI engine*; without it, the button offers to install it.
  The boxes and the frames follow each other: changing one updates the other.
- **Final size** = original photo + expansion. The damaged edge does not shrink the image: it is replaced.
- **Image surrounded by empty space** (e.g. a square photo pasted into a wider image, with transparency on the left
  and right, or top and bottom): the frame starts from **the photo itself** (the dotted line shows the image
  edge). **You choose the size**: drag the frame into the empty space, just a little or up to the image edge (it
  snaps there), or beyond it to enlarge the image. The AI extends the photo inside the frame; the rest of the empty
  space stays transparent. The frame starts from the photo **of the selected layer**: what is in other layers
  does not count (so select the layer of the pasted photo). Thin isolated strokes do not count either. The **red circles** (damaged edge) work too: drag them inwards to have a doubtful edge of the photo redrawn. The half-transparent edge of a photo pasted then shrunk is always redrawn (no light line at the seam). Transparent holes inside the photo stay
  transparent.
- The join between the photo and the addition is made by Pixane Photo: the original photo is kept **pixel for pixel**,
  with a gradual blend and colour matching, so that no line is visible. In **plain backgrounds** (sky, wall, dark
  background), the addition is brought back to the photo's level right up to the edge: no lighter part and no bands
  ("ghosting"), and the faint **swirls** the AI sometimes leaves in these backgrounds are smoothed out (fine grain
  and what is really drawn, such as a star, are kept). This join is redone after *Full resolution*.
- 3 options, about 1 minute each.
- **Extended background**: when the edges to expand are **plain** (cover background, smooth sky, gradient), one more
  option, made **without AI**, is added to the others: Pixane Photo itself continues the photo's background, row by row,
  with the same grain. No visible join or swirl, and it is instant. It does not appear if an object touches the
  edge (it would be stretched). *Start from this one* and *Full resolution* do not apply to it (it is already at
  full size).
- **Full resolution** (box in the bar, ticked by default): the AI invents the addition on an image reduced to about
  1 million pixels, then the addition is enlarged to the size of the photo; on a large photo it would therefore be
  blurrier than the rest. With the box ticked, once the option is chosen, the addition is **redrawn at the real
  size**, in 1024 px pieces, keeping its shape: it becomes as sharp and detailed as the photo, and gets the **same
  grain**. Slower: about 30 s to 1 min per piece (the waiting window shows "Piece 2 of 6" and the time left).
  **Cancel** during this work keeps the option as it is. No effect on a small photo (already done at its real size).
- **Tips** for a realistic addition: expand in small steps (20 to 30% at a time) rather than 100% at once; compare
  the options ("More options"); mark a border or frame as a damaged edge.
- **Layers**: all layers are shifted onto the new canvas; the addition and the redone edge go into the chosen
  layer (usually the photo), or into an "Expand 1" layer with the *new layer* option.
- If the photo contains text, the AI sometimes invents meaningless letters in the addition: use "More options".

### Upscale (Shift+U)
Increases the resolution (number of pixels) of the photo.

| Setting | Values | Effect |
|---|---|---|
| **Sharp** | default | RealESRGAN enlarges, then **Flux redraws the details** tile by tile. Slower (about 20 to 30 s per 1024 px tile) but sharp |
| **Fast** | | RealESRGAN only: a few seconds, but may look smoothed ("plastic") |
| **Scale** | ×1.5 to ×4 (×2 by default) | How many times larger |
| **Strength** (Sharp mode) | 0.10 to 0.60 (0.35 by default) | Freedom given to Flux: low = faithful to the original, high = more invented detail |

**How to set the strength** (Sharp mode): RealESRGAN first enlarges (faithful but a little smooth), then Flux goes
over it to redraw the details; the strength sets how much this 2nd pass does.
- **0.10 to 0.25** (light): very faithful, few details added. For **faces, text, logos**, which must stay exact.
- **0.35** (default): good balance, recommended in most cases.
- **0.45 to 0.60** (strong): lots of detail, but the AI **invents** some (a face or a text may change a little).
  For **landscapes, vegetation, fabrics**, which lack texture.

The window recalls this under the Strength box (fuller tooltip on hover).

**Nothing invented in flat areas** (Sharp mode): without instructions, Flux tends to "see" things in a plain area
(cover background, smooth sky) and adds spots, ghost text or drawings there. So Pixane Photo keeps its work only where the
original image really has detail (lines, text, photo texture); flat areas are taken from the original image simply
enlarged, and the colours stay those of the original. Nothing to set: it is automatic.

**Graphic image** (cover, logo, poster: mostly flat areas): Pixane Photo recognises it and suggests strength **0.25** right
away, because on text Flux may change a letter (seen in a test: "fig. 5" became "ftp. 5"). For a very simple graphic,
**Fast** mode is often enough.

The window shows the final size before starting; while computing, the progress counts the tiles.

**What should be processed?** (top of the window; the last choice is remembered)
- **Whole image**: the whole image and all its layers get larger (e.g. 1000 × 1000 -> 2000 × 2000). A photo with a
  single layer is simply replaced by the result. With several layers (or the *new layer* option), all layers are
  enlarged (simple smoothing) and the AI result arrives, complete, on an "Upscale 1" layer on top.
- **The chosen layer, sharper**: it keeps its size and place, the AI redraws it sharper (e.g. a small pasted photo
  enlarged with Ctrl+T, now blurry). The whole image does not change.
- **The chosen layer, enlarged**: only this layer gets larger (e.g. pasted photo 400 × 400 -> 800 × 800, in the same
  place); **the whole image keeps its size** (e.g. 1000 × 1000) and the other layers do not move. What goes beyond the
  image is hidden but kept (bring it back by moving the layer).

For the chosen layer: only its content is sent to the AI, and around it the layer stays transparent. With the *new
layer* option, the result arrives in a layer on top and the original stays. A locked layer is refused.

### Subject and background
**BiRefNet** model (MIT, 444 MB, installed with the AI engine; if it is missing, **AI > Install the AI engine…**
adds it). A few seconds.
- **Remove background** (Shift+B, AI panel or AI menu): the background of the **chosen layer** becomes
  transparent, the subject stays. Save as PNG, PSD or .piximg to keep the transparency. Ctrl+Z undoes it.
- **Select subject** (Ctrl+Alt+S, Select menu): selects the subject without erasing anything, for example to
  adjust it (Ctrl+U), or *Invert* (Ctrl+Shift+I) to work on the background.

### Create an image from text (AI menu)
Describe the image (subject, colours, light, style): **Flux Schnell** creates it, about **30 seconds** per
proposal. Example prompts in the list (abstract background, landscape, texture, illustration, portrait); as with
*Edit with an instruction*, a prompt in another language can be translated into English on your PC.
- **Result**: *New image* (square for an album cover or social media, 4:3, 3:4, 16:9, 9:16) or *New layer in the
  open image*, at its size (for example a background behind a cut-out).
- Also works **with no image open**: a new image is created.
- In the result window, **Start from this one** gives variants of the chosen proposal.
- The AI is bad at writing text: add text afterwards with the Text tool.
- Flux Schnell model (Apache-2.0), installed with the AI engine (*Flux Schnell* box).

### Remove people (AI menu)
The AI (**SAM 3.1**) finds **each person** in the photo. A window shows them: **ticked** people (in red) will be
erased; **click a person** in the image (or their box) to tick or untick them. At first everyone is ticked except
the **main subject** (the person clearly larger than the others).
- **Erase the ticked people**: they are selected (with a small margin for shadows and hair), then **Erase**
  rebuilds the background behind them (the usual result window).
- **Only select**: to complete the selection, for example a person the AI missed (**Object selection** tool,
  Shift + click), before running **AI > Erase**.

### Portrait retouch (AI menu)
The AI (**SAM 3.1**) finds the face, neck, eyes, eyebrows, lips and teeth (a few seconds), then an adjustment
window opens, with a **live preview** on the photo:
- **Smooth skin**: softens spots, redness and fine lines; outlines (nose, eyes), eyelashes and strands of hair stay
  sharp.
- **Keep skin texture**: puts the fine grain back, to avoid a "plastic" look.
- **Brighten eyes**: more sparkle and sharpness in the eyes.
- **Whiten teeth**: less yellow, a little brighter.
Applies to the chosen layer (inside the selection if there is one); every face found is retouched.

### Reduce noise, Sharpen, Restore an old photo (AI menu)
These three actions work on the visible image; if there is a **selection**, only its inside changes. Like the other
AI actions, the result goes into the chosen layer (Ctrl+Z undoes it).
- **Reduce noise (AI)**: removes grain (night or phone photos) and JPEG compression artefacts while keeping detail.
  **SCUNet** model (Apache-2.0, 72 MB). A few seconds.
- **Sharpen (AI)**: makes a slight blur sharper (edges, text, details): the photo is enlarged ×4 by RealESRGAN
  then brought back to its size. It also smooths grain: on a very textured photo, the *Sharpen* filter (Filters
  menu) may be better. 15 to 20 seconds.
- **Restore an old photo…**: the AI **redraws** the whole photo, removing scratches, stains, dust, creases and
  grain, and making contrast and faces sharper. The photo keeps **exactly its size and proportions**.
  - **Restore** keeps the **original colours**: a black & white or sepia photo stays so, a colour photo keeps its
    colours. The AI only provides the light and the details; Pixane Photo then puts back the original's tint.
  - **Restore and colourise** also adds natural colours to a black & white or sepia photo.
  - The result arrives in a **"Restored"** (or **"Restored and colourised"**) layer, and *Save as* as well as *Export
    for web* suggest a name that says so: `photo_restored.jpg`, `photo_restored_colourised.jpg`.
   Two proposals, about **2 minutes each**; *More proposals* asks for others. The AI may change
  small details (facial features, letters): compare carefully with the original (layer eye). **Flux Kontext dev**
  model (11.9 GB, FLUX.1 [dev] licence, **non-commercial** use), optional: *Flux Kontext* box in **AI > Install the
  AI engine…**.

### Sky, colours, lighting, depth (AI)
- **Select > Select the sky (AI)**: the AI (SAM 3.1) finds the sky and selects it, with a slightly widened and
  softened edge so the horizon line blends. Pixane Photo then refines the edge from the colours: the sky seen between the
  branches of a bare tree is selected too (and, with *Replace the sky*, the branches keep their colour). Then every tool works on that selection (adjustments, Fill…). A few
  seconds.
- **AI > Replace the sky…**: choose the new sky on **example thumbnails** (blue sky with a few clouds, big clouds, sunset, stormy sky, starry
  night, dawn). Pixane Photo selects the sky (clouds included), Flux Kontext redraws the photo with that sky, and **only the
  sky** is kept: the rest keeps its original pixels. Two proposals, about 2 minutes each. At the edge of a roof or a
  tree, the AI may leave a small shifted remnant: choose the best proposal, or retouch it (stamp, Erase). The sky
  stays selected: to match it, a colour adjustment on the rest of the photo (Select > Invert) often helps.
- **AI > Colorize**: adds natural colours to a black & white photo (without restoring it); with a selection, only
  inside it. Flux Kontext, two proposals, about 2 minutes each.
- **AI > Change the lighting…**: golden late-day light, soft studio light, strong light from the left or the right,
  backlight, night lit by street lamps, coloured neon lights, overcast; an example thumbnail for each (double-click:
  choose and start). With a selection, only inside it. Flux Kontext redraws the photo with that
  lighting, keeping the people and objects. Compare carefully: the AI may change small details.
- **Filters > Depth blur (AI)…**: like a camera's background blur. The AI computes the distance of each point (a few
  seconds); a window shows that map (light = near, dark = far): **click what must stay sharp** (at first: the
  nearest thing). **Blur** sets the strength, **Sharp zone** the depth kept sharp around the point. **Keep the
  whole subject sharp** (ticked at first): subject detection fixes what the map wrongly puts far away, for example a
  grey jacket in front of a grey wall. **Do not blur what is nearer than the sharp point**: only useful when you
  click something far away (otherwise nothing is in front, the box changes nothing). **If the AI gets it wrong**: choose *Brush: keep sharp* or *Brush: make blurred* and paint on the map
  (green = sharp, red = blurred; *Brush size*; *Clear the brush strokes*). Live preview on the photo; applies to the chosen layer (inside the
  selection if there is one). **Depth Anything 3 Small** model (137 MB, Apache-2.0), optional: *Depth blur* box when
  installing Pixane Photo, or in **AI > Install the AI engine…**.

---

## 6. Layers

An image can have several **layers**, stacked like transparent sheets: the top one is in front.
An opened photo has a single layer, "Background".

### Pixels outside the canvas

As in Photoshop, a layer can be **larger than the canvas**: an image pasted at full size, an element pushed to the
edge with Move or enlarged with Ctrl+T. What extends beyond **is not visible, but is never cut off**: you can bring
it back, shrink it, show it again.
- **Move**, **Transform (Ctrl+T)**, the handle frame, **Canvas size**, **Image size**, **rotations** and
  **flips** work on the whole layer. The handle frame also shows what extends beyond.
- The **brush**, the **eraser**, the **filters** and the AI only change what is inside the canvas; the part
  outside stays as it is.
- **Image > Reveal all**: the canvas grows just enough to show everything that extends beyond (Ctrl+Z to undo).
- Saved in **.piximg**, **PSD** and **ORA** (Photoshop, Krita and GIMP read it back). JPEG, PNG… only save the
  canvas. **Crop** and **Flatten** delete what extends beyond.

### The Layers panel
| Element | Purpose |
|---|---|
| **List** | The top layer is at the top. Click a layer to select it (it is highlighted) |
| **Eye** | Show / hide the layer (handy to compare before / after an AI edit) |
| **Thumbnail** | Preview of the layer, shaped like the image; the grey checkerboard shows transparent parts |
| **Name** | Double-click the name to rename; double-click elsewhere on the row: layer style |
| **Opacity** | Transparency of the selected layer, from 0% (invisible) to 100%; shown under the name when < 100% |
| **Padlock** (right of the name) | Locks the layer to protect it: it can no longer be erased, deleted or merged, and its opacity is fixed; Flatten is disabled while a layer is locked. AI actions are refused with a message: Erase and Fill if the selected layer is locked, Expand and whole-image Upscale if any layer is locked (they change the size of every layer), layer Upscale if that layer is locked. It can still be hidden, renamed and moved up / down. The open padlock is discreet, the closed padlock clearly visible. The lock is kept in .piximg and .ora files |
| **Drag a layer** | Change its place in the stack with the mouse: grab the row (on the name) and drag it up or down; an **orange line** shows where it will go. Dropped just below a layer of an open group, it enters the group; a group moves with its layers. A single Undo step |
| **Blend mode** (list at the top of the panel) | How the layer mixes with what is below (see below) |
| **Mask thumbnail** (right of the thumbnail) | The layer's mask, if it has one. Click: you paint the mask (orange frame); click the layer thumbnail: you paint the pixels again. Shift+click: disable / enable the mask (crossed in red) |
| **Ctrl+click** on a layer | Adds it to the chosen layers (or removes it): you can choose several, they are highlighted in blue |
| **Shift+click** on a layer | Chooses all the layers between the active layer and this one |
| **Right-click** | Layer menu: rename, duplicate, delete, merge, flatten, group, style, mask, show / hide, lock, new layer. With several chosen layers: **Merge the chosen layers**, delete, show or hide them |

### The buttons (left to right)
| Button | Action |
|---|---|
| **New layer** | Adds an empty layer above the selected layer (Ctrl+Shift+N) |
| **New group** | Creates a folder of layers (Ctrl+G puts the chosen layers in a group) |
| **Mask** | Adds a mask to the selected layer (from the selection if there is one) |
| **Adjustment** | Menu: new adjustment layer (Levels, Curves, Colour balance, Black & white, Vibrance, Image adjustments) |
| **Duplicate** | Copies the selected layer (Ctrl+J); a group is copied with its layers |
| **fx** | Layer style (see below) |
| **Move up / down** | Changes the layer's place in the stack; enters an open group, leaves it at the edge; a group moves with its layers |
| **Merge** (Ctrl+E) | Several chosen layers: combines them into one (in place of the top one, with its name). Only one: combines it with the one below (opacity, mask and mode applied). Refused for a locked layer, a group or an adjustment layer |
| **Flatten** | Combines all visible layers into a single "Background" |
| **Delete** | Deletes the selected layer, or all the chosen layers (a group: with its layers) |

### Blend modes
The same as Photoshop, sorted by family: **Normal**; **Darken**, **Multiply**, **Colour burn** (darkening);
**Lighten**, **Screen**, **Colour dodge**, **Linear dodge (Add)** (lightening); **Overlay**, **Soft light**, **Hard
light** (contrast); **Difference**, **Exclusion**; **Hue**, **Saturation**, **Colour**, **Luminosity**. Examples:
*Multiply* for a shadow or dark texture, *Screen* for a glow, *Overlay* for a paper texture, *Colour* to tint. Kept
in .piximg, .ora and .psd files.

### Layer masks
A mask **hides part of a layer without erasing it**: black = hidden, white = visible, grey = half. You can always go
back by painting white.
- **Layer > Layer mask**: *Add: reveal all*, *Add: reveal selection*, *Add: hide selection*; *Paint mask / pixels*
  (Ctrl+\); *Disable mask*; *Invert mask*; *Mask to selection*; *Apply mask* (into the pixels); *Delete mask*.
- **Painting the mask**: select it (click its thumbnail), then use the **colour brush** (black hides, white
  reveals, grey half), the **layer eraser** (hides), the **gradient** (gradual fade, for example to blend two
  photos) or the paint bucket. Adjustments and filters also work on the mask.
- Example: *Remove background* then a mask rather than an eraser: a bit of the subject cut by mistake comes back by
  painting white.
- Masks follow the layer (Ctrl+T, crop, image size, Upscale) and are kept in .piximg, .ora and .psd.

### Groups
A **group** puts several layers in a folder: you can hide, move, duplicate or delete them all at once, and give the
group an opacity, a blend mode and a mask that apply to everything inside.
- **Ctrl+G** (Layer > Group layers): puts the chosen layers (Ctrl+click or Shift+click in the panel) in one new
  group, placed where the topmost one was; they keep their order. A chosen group goes in with everything inside it.
  With a single chosen layer: that layer alone. **Ctrl+Shift+G**: ungroups (the layers stay).
- The arrow left of the group **collapses** or **expands** it. Layers inside a group are indented.
- Move up / down takes a layer into an open group, or out of it.

### Quick access bar
A 2nd row of buttons under the top bar, always there whatever the tool: Transform (Ctrl+T), rotate the image 90°
left / right, flip the whole image, Group / Ungroup, flip layer, Align (6) and Distribute (2). Each button's tooltip
says what it does. **View > Quick access bar** hides or shows it (hidden: Align and Distribute come back in the Move
tool bar).

### Align, distribute, flip layers
In the **Layer** menu and in the **quick access bar**. Pixane Photo uses
what the layers really contain (without the transparent space around). A chosen group moves as one block; locked
layers do not move; a single Ctrl+Z undoes.
- **Align**: left edges, horizontal centers, right edges, top edges, vertical centers, bottom edges. **Several chosen
  layers**: they align with each other (e.g. "left edges": on the leftmost one). **A single layer**: it aligns to the
  **selection** if there is one, otherwise to **the image** (e.g. horizontal + vertical centers = centered in the
  image).
- **Distribute** (3 or more chosen layers): horizontally or vertically, the first and last stay in place; the others
  are placed so that the space between neighbours is the same everywhere.
- **Flip layer**: horizontal (left ↔ right) or vertical (top ↔ bottom). A single layer flips in place (with a
  selection: only the selected part). Several layers or a group flip together, as one drawing. A flipped text
  becomes an image. (Image > Flip flips the whole image, all layers.)

### Adjustment layers
An **adjustment layer** applies an adjustment (Levels, Curves, Colour balance, Black & white, Vibrance,
Image adjustments) to **everything below it**, without touching the pixels: you can edit it (double-click it, or
**Layer > Edit adjustment…**), hide it (eye), lower its opacity or delete it at any time.
- **Layer > New adjustment layer**, or the panel's **Adjustment** button. If there is a selection, it becomes the
  adjustment layer's mask (the adjustment only applies there).
- Inside a group, it only adjusts the group's layers below it.
- Kept as is in .piximg; in .ora and .psd it becomes an image layer (the result).

### Fill layers
**Layer > New fill layer** (or the Layers panel's **Adjustment** button, at the top of the list): a layer that
covers the whole sheet with a **solid colour**, a **gradient** or a **pattern**, and stays **editable**
(double-click it).
- **Gradient**: linear, radial, angle, reflected or diamond style; **Angle**, **Scale**, **Invert**. At first: from
  the paint colour to white.
- **Pattern**: a pattern from the library, at the scale you want.
- If there is a selection, it becomes the layer's **mask** (the fill only shows there).
- It is redrawn when the sheet changes size (image size, canvas size, crop…); kept in .piximg; in .ora and .psd it
  becomes an image layer. *Convert to image* (right-click) freezes it.

### Harmonize a composite (Layer > Harmonize with the background…)
An object pasted from another photo often clashes: colder light, weaker blacks… Choose its layer (the cut-out
object, with transparency around it, above the photo): it takes on the light of the photo around it.
- **Light (blacks and whites)**: the same blacks and whites as the surrounding photo.
- **Light colour**: the same light tint (measured on the bright parts: a red shirt placed on grass does not turn
  green).
- **Soften the edge**: a softer edge, towards the inside of the object.
Live preview, one step in Undo.

### Layer style: shadows, outline, glow, bevel… (Ctrl+Alt+F)
**Effects added to the layer**, always editable: the layer's pixels are not touched. To open it: **double-click** a
layer (anywhere but on its name), the **fx** button in the panel, or **Layer > Layer style…**. The photo shows the
result live; **OK** keeps the style (a single step in Undo), **Cancel** puts everything back.

| Effect | What it does |
|---|---|
| **Drop shadow** | Offset shadow under the layer. **Realistic shadow** box: sharp near the object, blurrier further away, like a real shadow |
| **Inner shadow** | Shadow inside the edges (carved look) |
| **Outer / inner glow** | Colour halo around the layer, or from its edges (or centre) inwards |
| **Outline** | Line around the layer: outside, centre or inside, any thickness |
| **Bevel and emboss** | Adds volume: inner bevel, outer bevel or emboss; up or down; light altitude |
| **Colour overlay** | Covers the layer with a colour (Normal, Multiply, Screen, Overlay modes) |
| **Gradient overlay** | Covers the layer with a linear or radial gradient, any angle and scale; click the gradient to open the gradient editor (several colours, opacity) |
| **Pattern overlay** | Covers the layer with a repeated pattern from the library (mode, opacity, scale 10 to 1000 %) |
| **Ground shadow** | For a cut-out object: shadow lying on the ground, in perspective, sharp at the base and blurred at the end. **Drag the round dot on the photo** to choose its direction and length |

- **Ready-made styles** (at the top): Soft shadow, Realistic shadow, Ground shadow, Sticker, Black outline, Outline
  only, Neon, Gold, Chrome, Emboss, Engraved, Fire, Candy, Glass. Thumbnails are computed **on your layer**. One
  click tries it, then every effect can still be adjusted.
- **The same effect several times** (two outlines, three shadows…): ⧉ button. The first in the list is in front.
  ▲ / ▼ change the order, ✕ deletes, the tick box turns an effect off without losing it.
- **Fill**: opacity of the content only, effects stay. At 0%: only the outline or shadow remains (outlined text,
  glass…).
- **Same light** (ticked by default): all layers share one light; changing its angle on one layer changes it
  everywhere.
- **Save this style…**: it joins the ready-made styles (right-click it to delete it).
- Effects **follow the layer**: Ctrl+T, Image size and Upscale enlarge or shrink them with it. They also follow an
  edited text or a moved layer.
- **Layer** menu: **Copy style** / **Paste style** (onto another layer), **Remove style**, **Merge style into pixels**
  (to erase or paint the layer with its effects).
- Saving: in **.piximg**, styles stay editable. In **.psd** and **.ora** they are merged into the pixels (visible in
  Photoshop, Krita, GIMP, but no longer editable). Styles of an opened PSD are imported and stay editable (see chapter 2).
- Merge and Flatten also put the effects into the pixels.

### Layer eraser (G)
Erases the pixels of the **selected layer** with the round brush (size: "Size" slider or `[` `]`).
Example: an AI edit that worked except along one edge → select its layer and erase that edge; the original
photo shows through underneath. Erased areas of a single layer appear as a checkerboard.
Not to be confused with the **Selection eraser** (E), which only affects the red of the selection.
On a locked layer, the eraser does nothing and a message at the bottom of the window says so.

All layer actions can be undone with Ctrl+Z (changing the selected layer does not count).

---

## 7. Text

**Text** tool (key **T**, "T" icon in the toolbar). The **Text** panel opens on the left.

### Writing, moving, rotating
- **Click on the photo**: a new text "Text" appears at that spot, on **its own layer**.
  Just type: the suggested word is replaced. The panel's box accepts several lines (Enter).
- **Click on an existing text**: it is selected and its settings are shown; it can be edited at any time,
  even after saving as **.piximg** and reopening.
- The text is applied **as you go**: nothing to confirm.
- **Drag the text**: move it (also with the Move tool, V). A dashed frame surrounds the selected text.
- **Round handle** above the frame: rotate the text (**Shift**: in 15° steps), or the *Rotation* box.
- The layer name follows the first line of the text (as long as you have not renamed it yourself).
- With no text selected, the panel settings are used for the **next** text; Pixane Photo also remembers the last
  style used (font, colour, effects…). The size of a new text is calculated from the photo.

### Panel settings
| Setting | Effect |
|---|---|
| **Font** | All fonts installed in Windows. The list shows each font **with the beginning of your text** (or of the part selected in the box), otherwise "Aa Bb Cc 123". Hovering over a font **applies it at once to the text on the photo** so you can see the result; closing the list without choosing puts it back as before |
| **Size** | Letter height, in pixels of the photo |
| **Colour** (swatch) | Letter colour, with transparency (alpha channel) |
| **B / I / U / S** | Bold, italic, underline, strikethrough |
| **Alignment** | Left, centred, right (for several lines), **justified** (text in a box: lines stretched to both edges) |
| **Letters** | Space added between letters, as a % of the size (negative = tighter letters) |
| **Lines** | Space between lines, × the letter size |
| **Rotation** | Angle in degrees |
| **Curve** | Text on an arc: positive = arch, negative = dip, 360° = full circle |
| **Width / Height** | Stretch or squash the letters (100% = normal) |
| **Case** | As typed, ALL CAPS, all lowercase, Small caps, First Letter Capitalized (the typed text does not change: you can go back) |
| **Position** | Normal, **superscript** (m², 1st) or **subscript** (H₂O): smaller letters, raised or lowered |
| **Baseline** | Raise (positive) or lower (negative) letters, in % of the size |
| **Kerning** | *From the font*: spacing corrected between some pairs (AV, To…); *None*: raw spacing |
| **Here** | Manual kerning between the two letters around the cursor, in thousandths of the size (also **Alt+arrows** in the box, **Ctrl+Alt+arrows**: 5 times more) |
| **Ligatures, Fractions, Oldstyle figures** | Font options (OpenType): joined fi/fl, 1/2 → ½, figures of varying heights. No effect if the font lacks them |
| **Smooth edges** | Unchecked: sharp, pixel-by-pixel edges (for pixel art or small text) |
| **Vertical text** | Letters one below the other; each line becomes a column (right to left) |
| **Text in a box** | Lines wrap by themselves at the **box width**; **box height**: what overflows is hidden (0 = auto: fit the text) |
| **Indent / Between paragraphs** | Indent of the first line of each paragraph; space added between paragraphs (% of the size) |
| **Warp** | Like Photoshop's "Warp Text": Arc, Arc Lower / Upper, Arch, Bulge, Flag, Wave, Fish, Rise, Fisheye, Inflate, Squeeze, Twist. **Bend**: -100 to 100%; **Horiz. / Vert. distortion**: perspective effect |
| **Outline** | Line around the letters: colour and thickness |
| **Drop shadow** | Colour, distance, direction (0° = to the right, 90° = down) and blur |
| **Background** | Coloured rectangle behind the text: colour, margin and corner rounding |

Effect sizes (thickness, distance, blur, margin, rounding) are a **% of the letter size**:
they stay in proportion when you change the text size.
**Transparency** of the whole text: **Opacity** slider in the Layers panel.

### Change only some letters
**Select letters in the panel's text box** (with the mouse or Shift+arrows): font, size, colour, bold, italic,
underline, strikethrough, letters, width, height, case, position and baseline change **only for them** (a line under
the box reminds you). Example: one word in red, a "2" as subscript.
Without a selection, a setting changes **the whole text**, letters with their own style included. Letters typed
afterwards take the style of the one before them.

### Text on a path, glyphs, styles
- **Text on a path**: **Draw a path** button (Layout part), then drag on the photo: the text follows the line you
  draw (it is smoothed). **Start**: where the text begins along the path; **Remove**: the text becomes straight
  again. The path follows the text when you move or rotate it; it is shown dotted.
- **Glyphs** (**Ω** button next to the size): all the characters of the font (symbols, arrows, accented letters, ½,
  ©, emojis…). One click inserts the character at the cursor; the recently used ones stay at the top. Search by
  name (*arrow*, *heart*, *euro*) or by code (*U+2192*).
- **Text styles** (bottom of the panel): **Copy** remembers the font, colour, effects and settings of the text;
  **Paste** gives them to another text (its text and position do not change). **+** saves the style under a name;
  it stays in the list for next time (choosing one applies it); **−** deletes one.

### Spelling, hyphenation, find and replace
- **Spelling**: in the Text panel's box, misspelled words are **underlined in red**. **Right-click** on an
  underlined word: the suggestions (missing accents, swapped, extra or missing letters, words stuck together),
  *Ignore* (until Pixane Photo is closed) or *Add to the dictionary* (kept for good).
- **Language** (Paragraph part): the language of the text, for spelling and hyphenation; *Pixane Photo's language* by
  default. French and English.
- **Hyphenation** (text in a box): long words are split at line ends, with a hyphen, following the language's
  rules. When justified, a line with a single word stays on the left (its letters are not spread).
- **Option** (box in the installer, with the choice of languages, or **View > Spelling and hyphenation**): unticked,
  nothing is underlined or split. **View > Spelling languages…**: tick or untick a language; a language that is not
  installed is downloaded after you agree (LibreOffice dictionary: French 1.4 MB, English 0.6 MB), into
  %LOCALAPPDATA%\Pixane\dictionnaires.
- **Find and replace** (**Ctrl+H**, Edit menu): in all the texts of the image. *Next* chooses the text and selects
  the word in the panel; *Replace*, *Replace all* (a single Undo step); *Match case*, *Whole word*. Letters with
  their own style keep it. Locked texts are not changed.

### A photo inside the letters (clipping mask)
As in Photoshop: put the photo (or a texture, a gradient…) **on a layer just above the text**, then **Ctrl+Alt+G**
(Layer menu > *Clipping mask*, or right-click on the layer). The photo is now only visible **inside the letters**;
the text stays editable (text, font, size…) and the photo can be moved. In the Layers panel, the clipped layer is
indented with an arrow ↳. Ctrl+Alt+G again: removed. Works with any layer (not only a text). Kept in .piximg and
.psd; in .ora it is merged into the pixels.

### Good to know
- Every change can be undone with Ctrl+Z; typing several letters is undone in one go.
- **Expand** and **Upscale** keep texts editable: they are shifted or redrawn sharp at the new size.
- The **Layer eraser** on a text turns it into an image (a message says so; Ctrl+Z to go back).
  So do **Merge** and **Flatten**.
- A text on a **locked** layer can be neither moved nor edited.
- To keep texts editable, save as **.piximg** (in an .ora file, they become images).

---

## 8. Crop, paint, retouch

The manual editing tools, as in Photoshop. Everything can be undone with **Ctrl+Z**; a **locked** layer is
protected. Tools sharing a button (small triangle) are chosen by **right-clicking** the button.

### Crop (C)
1. Drag a frame on the photo: the part kept stays bright, the rest is darkened, and a rule-of-thirds grid helps
   place the subject. The size of the result is shown below the frame.
2. Adjust it: the **handles** (corners and middles of the sides) change its size, dragging **inside** the frame
   moves it. The frame never goes beyond the photo (to enlarge, see *Expand image*).
3. **Aspect ratio** (top bar): *Free*, *Same as the photo*, 1:1, 4:3, 3:2, 16:9, and the same in portrait.
4. **Enter**, double-click inside the frame or the **Crop** button: done. **Esc** or **Cancel**: the frame goes
   away without changing anything. What is outside the frame is deleted, including what already extended beyond
   the canvas (as in Photoshop).

All layers are cropped together; texts stay editable. **Selection > Crop to selection** menu: keeps the smallest
rectangle containing the selection.

### Colour brush (P)
Paints on the **layer chosen** in the Layers panel (tip: an empty layer above the photo lets you correct without
touching the photo).
- **Colour**: swatch in the top bar. **Alt+click** on the photo picks the colour at that spot (eyedropper).
- **Size** (or `[` and `]`), **Opacity** (100% fully covers, less lets what is below show through) and **Hardness**
  (100% sharp edge, 0% very soft edge).
- **Swatches**: the **SWATCHES** panel (tab next to History) keeps your colours: **one click** on a colour makes it
  the paint colour. **+** adds the paint colour, **−** removes the chosen one, right-click: *Rename*, *Remove*;
  **…**: **Import** Photoshop (.aco) or GIMP (.gpl) swatches, **Export** as .aco, **Restore the starting colours**.
  The swatches also appear under "Custom colors" in the colour windows.
- Going over the same spot during one stroke does not darken the colour; a new stroke does.

#### Editable brush layer
**Editable layer** box in the top bar (unchecked at first). When checked, the first brush stroke creates a **brush
layer** above the chosen layer (the photo is not touched), and the following strokes go into it too. This layer
keeps the **path** of each stroke, not just its pixels:
- **even later**, select it in the Layers panel with the colour brush: the top bar shows its settings; changing the
  **colour**, **size**, **opacity**, **hardness**, **rotation** (↻) or **brush shape** (and its Settings…)
  **redraws all its strokes**. Each change can be undone with Ctrl+Z;
- **moving** it, transforming it (Ctrl+T, without a selection), rotating or flipping the image, changing its size,
  cropping, Expand, Upscale: it **stays editable** (the strokes are redrawn sharp);
- a brush layer has **one setting for all its strokes**: for another colour kept separate, choose another layer (or
  the photo) before painting, and a new brush layer will be created;
- the **eraser**, a filter, the AI, the paint bucket… turn it into an ordinary image layer (a message says so; Ctrl+Z
  to go back). Right-click on the layer > **Convert to image** does it too;
- it is kept in **.piximg** files; in a PSD, PNG, JPG… it is saved as an image. In the Layers panel, it is marked
  "editable brush".
Box unchecked: you paint directly on the chosen layer, as before.

### Shaped brushes: the library (like Photoshop, Krita)
The colour brush (and masks), the **layer eraser** and the **selection brush** can take a **shape**: chalk, pencil,
grass, leaves, watercolour, splatters… Each tool keeps its own choice.
- **To paint normally**: the **Colour brush** (key **P**; it shares its button with the layer eraser, the gradient
  and the paint bucket: right-click the button to choose it). Key B is the *selection* brush, which does not paint.
- **Brush** (top bar): opens the library. Groups on the left, thumbnails on the right; double-click to choose.
  **Plain round** goes back to the usual round brush (its hardness is set in the top bar).
- **Size**: up to **5000 px** (progressive slider, or type the value; [ and ] keys). **Rotation**: the **↻** box
  next to Brush (arrows: 15° per step, or type the angle).
- In the library, the **Thumbnails** slider enlarges the thumbnails; on the right, a **large preview** of the chosen
  item (patterns at their real size, to see their grain).
- The groups, in order:
  - **Ready-made styles**: one click chooses the shape **and** its settings: Pencil, Charcoal, Chalk, Ink (pen),
    Felt-tip pen, Calligraphy, Watercolour, Oil paint, Palette knife, Dry brush, Airbrush, Spray can, Foliage,
    Grass, Stars and glitter, Clouds and smoke, Splashes. You can then fine-tune them with **Settings…**; choosing
    another brush after a style restores the default settings;
  - **Basic**: everyday brushes: hard round, soft round, airbrush, square, flat, chisel;
  - then Krita's brushes **by family**: Pencil and charcoal, Paint, Nature, Effects, Textures, Shapes;
  - finally the files you have added.
- **Shipped with Pixane Photo**: 235 brushes and 87 patterns (Krita resources, CC-0 licence), plus the basic brushes and
  the ready-made styles.
- **Add files…**: Photoshop brushes (**.abr**), GIMP and Krita brushes (**.gbr**, **.gih**), Krita bundles
  (**.bundle**), or a plain image (black paints; a colour image keeps its colours). Each file becomes a group;
  **Remove this group** takes it away. Brushes are stored inside Pixane Photo: the original can be moved or deleted.
- **Storage**: each added brush and pattern is stored separately, **at its original size with no loss of quality**
  (PNG), along with its thumbnail. Pixane Photo only opens the brush you use: even an .abr over 1 GB opens **without
  waiting** (library, brush settings, start-up), and takes less space (1.7 GB → 0.86 GB for a large .abr). Adding a
  very large file takes the time to store it (about 3 minutes for 1.7 GB).
- Brushes added **with an earlier version** are stored this way **once**, in the background, at the first start
  (message in the status bar); Pixane Photo stays usable meanwhile.
- An “animated” brush (.gih: grass, leaves…) has several shapes that alternate along the stroke.
- **Settings…** (a dot “•” shows when a setting is changed), with a stroke preview:
  - **Shape**: spacing between dabs, angle (or “angle follows the stroke”, like a pen), roundness;
  - **Scatter**: dabs spread away from the stroke, several at once, random size, angle and roundness;
  - **Texture**: a pattern carves the stroke (chalk on grainy paper); scale, strength, invert;
  - **Dual brush**: a second shape cuts into the first;
  - **Colour**: hue, saturation, brightness varying at each dab, mix with white;
  - **Transfer**: flow (below 100%, dabs build up, like an airbrush), variations;
  - **Tablet**: with a stylus, pressure changes the size (and, if you wish, opacity or flow).
- With a graphics-tablet stylus, even the round brush follows pressure.

### Clone stamp (S)
Copies one part of the photo onto another: to remove a small defect by hand, duplicate a texture…
1. **Alt+click** on the area to copy (a cross marks it).
2. Paint where it should be copied: the cross follows, at the same distance.
3. The next strokes keep the same offset (like Photoshop's "Aligned" option). A new Alt+click chooses another
   area.

The stamp copies the photo **as you see it** (all visible layers) and paints on the chosen layer. Size, opacity
and hardness as for the brush.

### Patterns: paint bucket, Fill, Pattern stamp, Pattern overlay
The **87 shipped patterns** (paper, canvas, wood, stone…) and those you add to the library (Photoshop **.pat**,
GIMP, Krita, or a plain image) are used in four places. The pattern is **repeated** from the top left corner of the
image: two fills with the same pattern join seamlessly. **Scale**: 100 % = actual size (10 to 1000 %).
- **Paint bucket**: in the top bar, the list next to *All layers* switches from **Colour** to **Pattern**; the
  pattern thumbnail appears (click: choose another pattern) with its scale.
- **Edit > Fill with a Pattern…**: covers the chosen layer with a pattern (only inside the **selection** if there
  is one); pattern, scale and opacity of your choice. Ctrl+Z to go back.
- **Pattern stamp** (in the Clone stamp group: right-click its button): you **paint** with the pattern, at the
  brush size, opacity and hardness. No Alt+click needed.
- **Layer style > Pattern overlay**: the layer (a text for instance) takes the pattern, without touching its
  pixels; can be changed at any time.

### Remove (J, AI)
Paint over a small flaw (power line, stain, spot, dust): **on release**, it disappears (LaMa). As with *Erase*, the
result goes **directly into the chosen layer**. With the AI menu option "Put results in a new layer", it goes on a
"Removals" layer, reused for the following strokes. For a large object, use *Erase* (Shift+E), which offers several
results.

### Healing brush (R)
Like the clone stamp, but the copy **takes on the surrounding light and colour**: ideal for a wrinkle, a skin
blemish, a scratch on a graded sky.
1. **Alt+click** a clean area.
2. Paint over the flaw: the raw copy shows while painting; **on release**, it is blended with its surroundings.

### Gradient (D)
Drag from the start to the end of the gradient (**Shift**: horizontal, vertical or 45°). Top bar: **Linear** or
**Radial**, then the **gradient preview**: click it to open the **gradient editor** (as in Photoshop). Inside the
selection if there is one. While you drag, the result shows **live** on the layer; it is applied when you release
the mouse (Ctrl+Z to go back).
- On a **text layer**, the gradient goes **on the letters only**, as a "Gradient overlay" style: the text stays
  editable, and a new gradient replaces the previous one. The direction and length of the drag give the angle and
  scale; to adjust them: **Layer > Layer style**.
- **Keep transparency** (box in the top bar): on an image layer, the gradient only goes on what is already painted
  (a cut-out object, a drawing); the empty space around stays empty.
- On a **mask** (mask thumbnail selected in the Layers panel; the top bar then shows **"→ in the mask"**), the
  gradient does not colour: it makes the layer more or less transparent, for a gradual fade (for example to blend
  two photos). Colours become greys there, and the transparent part of the gradient becomes the grey opposite to
  the paint colour (white for a dark colour). To colour, click the layer thumbnail first.
- The editor sets the **next** gradient: open it before dragging. In the Layer style window, on the other hand,
  each change in the editor shows on the layer straight away (Cancel brings back the previous one).

**Gradient editor**:
- At the top, the **ready-made gradients** (paint colour to transparent, black to white, rainbow, gold, chrome,
  copper, fire, sky…) and the ones you saved: one click loads one.
- The **bar** shows the gradient (the checkerboard = transparent). **Below the bar**, the **colour** stops; **above**,
  the **opacity** stops (black = opaque, white = transparent).
- **Add a colour**: click below the bar where you want it; the new stop takes the colour found there.
  **Double-click** the stop (or click the "Colour" box) to choose its colour. The **Paint colour** box makes the stop
  follow the current paint colour (small "P" in the stop).
- **Add an opacity stop**: click above the bar, then set its **Opacity** below.
- **Move** a stop: drag it, or type its **Location** in %. **Remove**: pull it away from the bar, press **Delete** or
  click **Delete** (there are always at least two stops of each kind).
- The small **diamonds** next to the selected stop set the **midpoint** of the transition between two stops: closer to
  a stop, the transition happens faster on its side.
- **Reverse** turns the gradient around. **Save to list…** keeps your gradient (with a name); **Remove from list**
  takes it away.
- The chosen gradient is kept from one session to the next.

### Paint bucket (K)
**What it is for**: filling a plain-coloured area in a single click, without painting it by hand. For example:
changing the colour of a plain background or a banner, filling the inside of a letter or a shape, colouring an area
of a line drawing, or filling a selection.

**How**: choose the colour (swatch in the top bar, or **Alt+click** on the photo to pick it), then click inside the
area: it fills until the colour changes.
- **All layers** (box in the top bar): where the bucket looks for the area to fill.
  - **Unticked** (default, as in Photoshop): in the **selected layer** only. On an empty layer, one click fills **the
    whole layer**, whatever is on the other layers.
  - **Ticked**: in the **visible image** (all layers together). Useful to colour a drawing whose lines are on
    another layer: the fill stops at the lines. Beware: it also stops at the edges of everything you see, even from
    another layer; if you then delete or move that layer, a "hole" appears in the fill.
- **Tolerance** (top bar): at 0, only the exact colour is filled; higher, the fill spreads to nearby shades (useful
  for a slightly graded background or a JPEG photo).
- If there is a **selection**, it stays inside it. It paints on the selected layer (tip: an empty layer above makes
  it easy to go back).

### Retouch brushes: Dodge, Burn, Sponge, Blur, Sharpen, Smudge, History
Two families in the toolbar (right-click or press and hold to choose), like Photoshop. They change the pixels of
the **chosen layer**, under the brush; **Strength** (top bar) says how much, size and hardness are set as for the
brush. Going over the same place during one stroke does not strengthen the effect; a new stroke does. Each stroke is
one Undo step.

| Tool | What it does |
|---|---|
| **Dodge** | Lightens. **Tones**: *Shadows*, *Midtones* or *Highlights* (only those tones move: lighten the shadows of a face without burning the forehead) |
| **Burn** | Darkens, with the same choice of tones (darken a sky, an edge) |
| **Sponge** | **Desaturate**: dulls the colours (down to grey); **Saturate**: boosts them |
| **Blur** | Blurs (a background, skin texture, a flaw). On a **mask**, softens its edge |
| **Sharpen** | Makes details sharper (eyes, letters); at low strength, or grain appears |
| **Smudge** | Spreads the colour along the stroke, like wet paint; the strength says how far it spreads |
| **History brush** | Paints back the **snapshot**: at first, the photo as it was opened. To undo an effect in some places only. **Take a snapshot** (top bar) keeps the current state. It is under the Clone stamp, and also at the bottom of the **History** panel (*History brush* button) |

### Liquify (Filters > Liquify…, Ctrl+Shift+X)
To shape the image with a brush, like Photoshop's Liquify: slim a silhouette, stretch a letter, bloat a detail. A
window opens with the chosen layer; you paint on it with one of the tools:

| Tool | What it does |
|---|---|
| **Push** | The image follows the stroke (move an outline, stretch) |
| **Bloat** | Enlarges what is under the brush; keep the button pressed or go over again to strengthen |
| **Pucker** | Shrinks what is under the brush |
| **Twirl** | Turns what is under the brush |
| **Reconstruct** | Gradually goes back to the original image where you paint |

**Size** (in photo pixels) and **Pressure** are set on the left. **Undo the last stroke** and **Reconstruct all** let
you go back before applying. The preview is reduced to stay fast, but the result is computed at full resolution at the
end, without blur. With a selection, only the selected area changes. The whole Liquify is one Undo step.

### Shapes (U)
Drag to draw a **rectangle**, **rounded rectangle**, **ellipse**, **star**, **polygon**, **line** or **arrow**
(**Shift**: square, circle, straight line). **Sides**: number of points of the star or sides of the polygon. Top bar:
**Fill** and **Outline** (boxes, each with its colour: click the colour to change it) and the outline **thickness**.

Each shape goes on a **shape layer** ("editable shape" in Layers), as in Photoshop: choose that layer with the Shapes
tool or the Pen, and the top bar shows its settings; changing them redraws the shape (one Undo step). Moved, resized,
rotated (Ctrl+T), or the image enlarged: the shape is redrawn sharp and stays editable; it is kept in the .piximg
file. The eraser, a filter or the AI turn it into an ordinary image (a message says so; Ctrl+Z to go back); Layer >
right-click > **Convert to image** too.

### Pen (A)
To draw free shapes, with straight lines and curves, point by point (like Photoshop's Pen):
- **click**: a corner point; **click and drag**: a curve point (you pull its handles); **Shift**: at 45°;
- **click the first point**: the path closes; **Enter** or **double-click**: it stays open (a stroke);
- **Backspace** removes the last point, **Esc** drops the path.

**Mode** (top bar): **Shape** (the path becomes a shape layer, with the fill and stroke of the bar) or **Selection**
(the closed path becomes the selection; Shift when finishing: added, Alt: removed).

With a shape layer chosen, the Pen shows its points: drag a **point** to move it, or a **handle** to change the curve
(the other handle follows; **Alt**: the handle moves alone and makes a corner).

A **text** retouched with the brush or the stamp becomes an image (a message reminds you; Ctrl+Z to go back).
Groups and adjustment layers have no pixels: a message asks you to choose an image layer or a mask.

---

## 9. Image adjustments

**Image > Image adjustments…** menu (Ctrl+U): correct light, colours and sharpness.

| Setting | From … to | Effect |
|---|---|---|
| **Brightness** | -100 to +100 | Lightens or darkens, keeping black and white |
| **Contrast** | -100 to +100 | Spreads or brings together lights and darks |
| **Saturation** | -100 to +100 | More vivid or duller colours; -100 = black and white |
| **Hue** | -180° to +180° | Rotates all colours (red becomes orange, green…) |
| **Temperature** | -100 to +100 | Warmer (orange) or cooler (blue) |
| **Sharpness** | 0 to 200% | Enhances details |

- The adjustment applies to the **layer chosen** in the Layers panel; if there is a **selection**, only inside it
  (with its soft edges). The window reminds you at the top.
- **Preview on the photo**: you see the result live while moving the sliders (on a large photo it arrives after a
  fraction of a second). Untick to compare with the original.
- **Reset** sets everything back to zero, **Apply** keeps the result, **Cancel** (or Esc) leaves the photo as it
  was. After Apply, Ctrl+Z undoes the adjustment.
- **Auto**: suggests a brightness, contrast and temperature (from the photo, or the selection); the sliders can
  still be adjusted afterwards.
- A **locked** layer is protected; an adjusted **text** becomes an image.

### Levels, Curves, Colour balance, Black & white, Vibrance… (Image > Adjustments menu)
As in Photoshop, with live preview and histogram. They change the pixels of the **selected layer** (inside the
selection if there is one). To be able to come back to them later, use an **adjustment layer** instead (chapter 6).

| Adjustment | Shortcut | What it does |
|---|---|---|
| **Levels** | Ctrl+L | Input black, grey (gamma) and white points, output black and white; per channel (RGB, red, green, blue). **Auto** sets black and white from the photo |
| **Curves** | Ctrl+M | Tone curve: click to add a point, drag to move it, right-click to remove it; per channel. An S curve adds contrast |
| **Colour balance** | Ctrl+B | Pushes **Shadows**, **Midtones** or **Highlights** towards Cyan–Red, Magenta–Green, Yellow–Blue; *Preserve luminosity* |
| **Black & white** | Ctrl+Alt+Shift+B | Converts to black & white choosing the lightness of each colour (reds, yellows, greens, cyans, blues, magentas); **Tint**: colours the greys (sepia…) |
| **Vibrance** | — | Mostly boosts dull colours, sparing those already vivid (skin); **Saturation**: all colours equally |
| **Replace colour** | — | Click the colour to change in the preview (Shift+click: add one, Alt+click: remove one), set the **Tolerance**, then the **Hue**, **Saturation** and **Lightness**: only those pixels change, folds and shadows kept (a red jumper turns blue) |
| **Photo filter** | — | Like a colour filter in front of the lens: warming, cooling, sepia… or a custom colour; **Density**; *Preserve luminosity* |
| **Channel mixer** | — | Each output channel (red, green, blue) is made of a share of red, green, blue and a constant; **Monochrome**: custom black & white |
| **Gradient map** | — | Dark tones take the colour on the left of a gradient, light tones the one on the right ("duotone", poster effects); *Invert* |
| **Invert** | Ctrl+I | Inverts the colours |
| **Threshold** | — | Black or white depending on lightness (stamp, stencil effect) |
| **Posterize** | — | Keeps few shades per colour: flat areas like a poster |

All of them also exist as an **adjustment layer** (Layer > New adjustment layer), editable at any time.

### Filters (Filters menu)
**Gaussian blur**, **Motion blur** (angle, distance), **Radial blur** (*Rotation*: pixels spin around the centre;
*Zoom*: they streak towards the centre; amount, centre in %), **Lens blur** (like a real lens: each point becomes a
small disc; very bright points become **round highlights**: set their strength and threshold), **Surface blur**
(smooths skin or a sky while keeping edges sharp; *Threshold*: from which colour difference an edge is kept),
**Noise reduction** (strength, keep details, colour noise),
**Sharpen** (amount, radius, threshold: Photoshop's unsharp mask), **Vignette** (darken or lighten the edges:
strength, centre size, softness, round). Same behaviour as adjustments: live preview, selected layer, inside the
selection if there is one, one step in Undo. They also work on a mask.

### Actions (ACTIONS panel)
As in Photoshop: **record** a series of operations, then **replay** it in one click on other photos.
- **● Record**: give a name, then do your work: **adjustments** (Image > Adjustments), **filters**, **image size**
  (kept as a percentage when the proportions do not change: it works on photos of any size), **rotations** and
  **flips** are added to the action. **■ Stop** ends it.
- **▶ Play** (or double-click): the action replays on the open photo, with no window, with the same settings;
  **a single step** in Undo.
- **…**: *Rename*, *Delete the action or step*, *Export* / *Import* actions (.json, to keep or share them).
- **File > Batch processing**: choose an action to play it on **a whole folder**.

---

## 10. Image menu: size, rotation, transform

- **Mode**: **RGB colour** or **Greyscale**. In greyscale the image is shown and saved in grey (JPEG, PNG, TIFF in
  true grey); the layers keep their colours, so you can go back to RGB without losing anything.
- **8, 16 or 32 bits per channel** (*Image > Mode*, like Photoshop): in 8 bits each colour has 256 shades; in
  **16 bits**, 65,536; in **32 bits (HDR)**, floating-point numbers (see below). Useful for strong edits (levels, curves, brightening a dark photo), **gradients** and skies: no **banding**
  (visible steps) even after several adjustments. The window title shows **(16 bits)**. Ctrl+Z undoes the change.
  - **Opened in 16 bits automatically**: 16-bit PNG, TIFF and PSD files, and **RAW photos** (developed in 16 bits).
  - **Saved in 16 bits**: .piximg, PSD, TIFF, PNG. JPEG, WebP and BMP only have 8 bits: the image is saved in 8 bits
    there, with **dithering** (see below).
  - **Computed in 16 bits**: layer blending (blend modes, adjustment layers, masks), all **adjustments** (Image
    adjustments, Levels, Curves, Balance…), **filters** (blurs, sharpen, noise, vignette), the **Gradient** tool and
    fill layers, image size, rotate, flip, straighten, transform, crop, Expand.
  - **Brushes work in the image's depth**: brush, eraser, clone stamp, history brush, Dodge / Burn, Sponge, Blur,
    Sharpen and Smudge (in 16 bits, without rounding to 256 shades).
  - The other tools (paint bucket, text, AI…) work in 8 bits, **only where they change the image**: the rest of the
    layer keeps its 16 bits. The AI always returns an 8-bit result, placed only in the area it worked on.
    *Content-aware scale* brings the whole layer back to 8-bit precision.
  - A 16-bit image takes **twice as much memory**, and filters are a little slower.
- **32 bits per channel (HDR)** (*Image > Mode > 32 bits per channel (HDR)*): for **HDR** photos (merged exposures,
  3D renders). A colour can be **brighter than white**: the sun, a lamp or a very bright sky keep their detail, and
  the exposure can be lowered afterwards without losing anything. The window title shows **(32 bits)**.
  - **Opened in 32 bits automatically**: **.exr** (OpenEXR), **.hdr** (Radiance) and **32-bit TIFF** files.
  - **Saved in 32 bits**: .piximg, EXR, HDR, TIFF. PSD and PNG are saved in 16 bits, JPEG in 8 bits: whatever is
    brighter than white becomes white there (first switch to 16 or 8 bits with *HDR toning* to choose how to bring
    it back).
  - **Computed in 32 bits**, without clipping to white: layer blending, adjustment layers, adjustments, filters,
    Gradient, fill layers, size, geometry, and brushes (the **clone stamp** also copies the areas brighter than
    white). An adjustment treats a too-bright colour while keeping its brightness.
  - **View > 32-bit exposure…**: makes the on-screen preview brighter or darker (in stops) to look at the areas
    brighter than white. The image and its exports do not change.
  - **HDR toning**: when switching a 32-bit image to 16 or 8 bits, a window opens if the image has colours brighter
    than white: **Exposure** (lower it to recover the sky), **Gamma** (midtones), and **Compress the highlights**
    (everything is brought smoothly under white, nothing is clipped). A preview shows the result.
  - A 32-bit image takes **four times as much memory** as in 8 bits.
- **Dither to 8 bits** (*Image > Mode*, checked by default): when a 16 or 32-bit image is shown on screen, exported to JPEG /
  WebP, or brought back to 8 bits, a very light invisible grain is added so gradients show no steps (like Photoshop's
  "dither"). Uncheck it for a grain-free conversion to 8 bits.
- **Canvas size…** (Ctrl+Alt+C): enlarges the sheet **without stretching the image** (for example to add a bleed
  or a band for a title), or crops it.
  - New **width** and **height** in pixels, inches, cm, mm, points, picas or **percent**; **Relative**: you type
    what you add (e.g. +200 px).
  - **Anchor**: where the image stays (centre, top left…); the arrows show where the sheet grows.
  - **Preview**: the new sheet, the added colour and the image in its place; what will be cropped is shown faded,
    with a red dashed outline.
  - **Added colour** on the bottom layer: white, transparent, black or a colour of your choice.
  - Texts stay editable, guides follow; Ctrl+Z undoes it. What extended beyond the canvas reappears if it falls
    inside the new canvas.
- **Reveal all**: the canvas grows to show all the pixels that extend beyond the layers.
- **Image size…** (Ctrl+Alt+I): in pixels or %, proportions kept (tick box), quick buttons (for example 1920 px
  for screen and Internet). No AI: to enlarge with more detail, prefer Upscale. **Preview**: the centre of the
  image at 100%, before (left) and after (right), to judge sharpness.
- **Content-aware scale…**: change the **proportions** (a square to 16:9, a landscape to 4:5…) **without squashing
  the subject**: mostly the areas without detail (sky, wall, plain background) are stretched or compressed.
  - **Width**, **Height**, or a quick **format** (1:1, 4:3, 3:2, 16:9, 3:4, 4:5, 9:16: the longest side is kept).
  - **Protect the selection**: first select the subject (Select > Select subject): it is not distorted at all.
  - **Content protection**: 0% = ordinary stretch, 100% = only areas without detail change.
  - **Preview** of the result. All layers follow, masks and selection too; texts, shapes and brush strokes become
    images (Ctrl+Z to undo).
- **Rotate** 90° right, left or 180°, **Flip** horizontally or vertically: the whole image, all layers, lossless.
  Flipped texts become images; rotated ones stay editable.
- **Rotate by an angle…**: the whole image rotates by the typed angle, **to the degree** (or tenth of a degree),
  from -359.9° to +359.9° (positive: clockwise). The canvas grows to keep everything; the corners are transparent.
- **Straighten…**: rotate by a small angle (-45° to +45°) with a grid to align the horizon or a wall.
  *Crop to remove the empty corners* (ticked by default); unticked, the image grows and the corners are
  transparent.
- **Perspective crop**: for a **facade, a painting, a document, a screen photographed at an angle**. Drag the
  **4 corners** onto the edges of the object (a perspective grid helps follow its lines; inside: move everything),
  then **Enter**, double-click or **Crop**: the object becomes a **straight rectangle** filling the image (width and
  height of its longest edges). Texts become images. Esc: cancel; Ctrl+Z while adjusting puts the previous corner
  back.
- **Edit > Transform layer** (Ctrl+T): a frame surrounds the **chosen layer**. To enlarge, shrink or rotate **a
  single element** of the layer, **select it first** (rectangle, lasso, magic wand…): the frame surrounds only that
  element, the rest of the layer does not move, and its original place becomes transparent.
  - **corner**: size, proportions kept (Shift: free); **side**: width or height only;
  - **inside**: move; **outside** (the cursor becomes a round arrow): rotate, **degree by degree** (Shift: by 15°);
  - the top bar shows **Width**, **Height** (in %) and **Angle** (in degrees) in boxes where you can **type the
    exact value** (arrows: 1°; Shift+arrows: 10°); **Enter**, double-click or **Apply** to keep, **Esc** or
    **Cancel** to go back. Changing tool also applies.
  - **Mode** (top bar, or **Edit > Transform**):
    - **Free**: as above. **Ctrl+corner**: that corner moves on its own (switches to *Distort*).
    - **Perspective**: a dragged corner moves the neighbouring corner **as a mirror** (dragged down, the edge
      shrinks; dragged sideways, it widens): like a facade seen at an angle.
    - **Distort**: each corner moves on its own, to **put an image on a screen, a box, a wall, a 3D sleeve**; an
      edge middle moves that whole edge.
    - **Warp**: a **grid of 16 points** (circles for handles, squares at the corners): drag them to bend, inflate,
      fold the image (flag, mug, waving page). A corner takes its two handles along.
    - In these three modes, **inside** = move, **outside** = rotate the whole shape; Ctrl+Z undoes the last move.
      The Width / Height / Angle boxes are greyed out.
  A transformed text becomes an image (to keep a text editable, use the Text tool).

Everything can be undone with Ctrl+Z.

---

## 11. Shortcuts

| Key | Action |
|---|---|
| H, V, M, L, B, E, G, T | Hand, Move, Rectangle, Lasso, Brush, Selection eraser, Layer eraser, Text |
| C, P, S | Crop, Colour brush, Clone stamp |
| J, R, D, K, U | Remove (AI), Healing brush, Gradient, Paint bucket, Shapes |
| Alt+click | (Colour brush, Paint bucket) pick a colour; (Clone stamp, Healing brush) area to copy |
| `[` / `]` | Smaller / larger brush |
| Space (held) | Move the view |
| Shift / Alt (when starting a rectangle or a lasso) | Add / Remove |
| Alt (held, selection brush) | Remove for one stroke |
| Shift+E, Shift+R, Shift+A, Shift+U | Erase, Fill, Expand, Upscale |
| Ctrl+Z, Ctrl+Y | Undo, Redo |
| Ctrl+A, Ctrl+D, Ctrl+Shift+I | Select all, Deselect, Invert |
| Ctrl+X, Ctrl+C, Ctrl+V, Del | Cut, Copy, Paste (new layer), Delete selection |
| Ctrl+U | Image adjustments |
| Ctrl+L, Ctrl+M, Ctrl+B, Ctrl+Alt+Shift+B | Levels, Curves, Colour balance, Black & white |
| Ctrl+I | Invert |
| Ctrl+G, Ctrl+Shift+G | Group, Ungroup |
| Ctrl+Alt+G | Clipping mask (the layer only shows inside the one below) |
| Ctrl+H | Find and replace in texts |
| Ctrl+\ | Paint the layer's mask / pixels |
| Ctrl+Alt+R | Refine edge |
| Ctrl+R, Ctrl+', Ctrl+;, Ctrl+Shift+; | Rulers, Grid, Guides, Snap |
| Ctrl+W, Ctrl+Tab, Ctrl+Shift+Tab | Close photo, Next photo, Previous photo |
| Ctrl+Alt+Shift+S, Ctrl+Alt+Shift+W | Export for web, Export as |
| Ctrl+P | Print |
| Arrows (Shift: x10) | Move the selection (selection tools) |
| Ctrl+N, Ctrl+Alt+V | New image, New image from clipboard |
| Ctrl+Alt+I, Ctrl+Alt+C | Image size, Canvas size |
| Ctrl+Alt+Y | Print preview (CMYK) |
| Ctrl+T | Transform layer (Enter apply, Esc cancel) |
| Ctrl+Alt+F | Layer style |
| Ctrl+Shift+N, Ctrl+J | New layer, Duplicate layer |
| Ctrl+Alt+S, Shift+B | Select subject, Remove background (AI) |
| O, Q, W, Y | Object selection (AI), Quick selection (AI), Magic wand, Text selection |
| Drag after a magic wand click | Adjust the tolerance live |
| Right-click on a tool with a small triangle | Choose another tool of the group |
| Ctrl+0, Ctrl+1 | Fit, 100% |
| Enter / Esc | (Expand) Start / Cancel; (Crop) Apply / Cancel |
| Shift (while rotating a text) | Rotate in 15° steps |
| F1 | Guide, opened at the shortcuts (Help > Pixane Photo guide: the whole guide, with a search) |

---

## 12. Hardware and licences

**Installation**: run `Pixane-Photo-Setup-<version>-64bits.exe`.
1. Installation language (it will also be Pixane Photo's language, which can be changed later in View > Language).
2. Just for me (default, no administrator rights) or for all users.
3. Installation folder: by default `…\Pixane\Pixane Photo` (the `Pixane` folder gathers the programs of the
   Pixane Suite). An older installation (`…\Pixane`) is moved there automatically: settings, projects, AI engine
   and shortcuts are kept.
4. **PC check**: NVIDIA graphics card and its memory (8 GB recommended), free space, AI engine (ComfyUI) found or
   not. If ComfyUI is installed elsewhere, use **Browse…** to select its folder.
   Without ComfyUI, Pixane Photo opens, edits (layers, text) and saves photos, but the AI actions do not work.
5. **AI engine** (only if ComfyUI is not found): list of what will be downloaded, with size, site and licence
   (21.5 GB to download, about 31 GB on disk); engine folder (default `%LOCALAPPDATA%\Pixane\moteur`); optional
   **Flux Schnell** box for "Sharp upscale" (11.8 GB more); the **I accept the FLUX.1 [dev] licence** box
   (non-commercial use) is required to install the engine. You can also untick it: Pixane Photo installs without the
   engine.
6. Options: desktop icon; open .piximg files with Pixane Photo; **interface size** (normal, compact 85 %, large
   125 %, very large 150 %; does not replace a choice already made in Pixane Photo).
7. At the end, the **Install the AI engine** window downloads and installs everything (ComfyUI portable, its
   extensions, the models). It shows progress, speed and time left. You can **Stop** at any time: the download
   resumes later where it stopped (even after a connection loss). Each file is checked (SHA-256 checksum).

The same window opens from **AI > Install the AI engine…** (for example to add Flux Schnell later, or **Flux
Kontext** — 11.9 GB, optional — for *Restore an old photo*), and Pixane Photo
offers it at start-up if it finds no engine. If a ComfyUI installed another way is already there (ComfyUI Desktop, portable
ComfyUI…), Pixane Photo uses it as it is: at start-up it asks ComfyUI what it already has and, if extensions or models are
missing, offers the **Complete the AI engine** window (also from **AI > Install the AI engine…**). It lists **only
what is missing** (size, licence, source, folder) and puts it into that ComfyUI's folders, even a shared models
folder, without replacing or deleting anything. Flux Schnell and Flux Kontext can be added as options. If new
extensions are added to an open ComfyUI Desktop, close it and open it again so that it loads them. A ComfyUI too
old for a feature (for example object selection) is reported: Pixane Photo does not update it itself.

**AI engine updates**: the versions of ComfyUI, the extensions and the models are chosen and tested with each
version of Pixane Photo; nothing changes on its own. When a new version of Pixane Photo needs other versions, Pixane Photo offers
it once at start-up (list and download size), and the **Install the AI engine** window shows the state of each
item (*up to date*, *new version*) with the **Update** button. Only what changed is downloaded. ComfyUI is replaced
while keeping its models, extensions and settings; a replaced old model is deleted. The engine is stopped during the
update and restarted afterwards. A ComfyUI installed another way (for example ComfyUI Desktop) updates itself:
Pixane Photo does not touch it.

**Help > Check for updates…** (or at startup, if *Check for updates at startup* is ticked): when a new version exists, a window shows **what's new** (new features, fixes) in every version you do not have yet; **Download** opens the download page. A new version installs over the old one (settings kept). To uninstall: Windows Settings > Apps. The uninstaller
asks two questions (default answer "No"):
- also delete the **AI engine installed by Pixane Photo** (ComfyUI, extensions, models)? A ComfyUI installed another
  way, such as ComfyUI Desktop, is never touched;
- also delete the **settings** (language, theme, last folder, text style, engine folder) and the logs?

**Licences and test hardware**:
- Pixane Photo: Pixane Licence 1.3, © 2026 Georges Christophe (chrypox): free of charge, may be modified and shared,
  author's name required, no sale (of Pixane Photo or a modified version); file `LICENSE` (French text prevails;
  translation `LICENSE.en.txt`).
  Third-party items: `docs\LICENCES_TIERS.md`.
- Tested on an 8 GB NVIDIA graphics card (RTX 3060 Ti). The times given come from this PC.
- Models used: Flux.1 Fill dev (**non-commercial use**; GGUF Q8 version when installed by Pixane Photo, same
  quality), Flux.1 Kontext dev (**non-commercial use**, optional), Flux.1 Schnell (Apache-2.0), LaMa (Apache-2.0),
  RealESRGAN x4plus (BSD-3), SCUNet (Apache-2.0), BiRefNet (MIT), SAM 3.1 (Meta SAM License).
- Engine: ComfyUI (GPL-3.0) and its extensions Inpaint nodes, Inpaint Crop and Stitch, Ultimate SD Upscale
  (GPL-3.0), ComfyUI-GGUF (Apache-2.0).
