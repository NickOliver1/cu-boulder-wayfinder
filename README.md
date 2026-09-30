# CU Boulder Wayfinder

An unofficial, screen-reader-first guide to the University of Colorado Boulder campus maps, with door-to-door walking directions written for listening.

The official campus map notes that it "has known issues with certain assistive technologies." This app takes the same map data and presents it as structured, navigable text: every building and place has a written description, and walking directions describe turns, crossings, stairs, and surroundings in words.

**This is an independent accessibility project. It is not affiliated with or endorsed by the University of Colorado Boulder.**

## What it does

### Browse and search the campus maps
- All 9 official map layers: Buildings, Parking, Bus/Bike/E-Scooter/Car Share, Student Academic Resources, Inclusive Resources, Services, Health & Safety, Outdoor Recreation, and Accessibility. That is 1,190 places, including 167 buildings.
- Search by building name, four-letter code, department, or service. Results update as you type, and the number of matches is read aloud.
- Every place page gives, in this order:
  - where it is, in words
  - quick facts (building code and number, address, the map layers it is on)
  - a description of what the building looks like
  - the official description
  - the six nearest buildings, with distance and direction
  - the closest accessible parking, bus stop, bike share, food, computer lab, all-gender bathroom, and lactation room

### Walking directions
- **Door to door.** Routes start and end at real building entrances where they are mapped (280 entrances across campus), preferring main entrances, or entrances marked wheelchair accessible for step-free routes.
- **"Where you start".** Which door you leave from and which side of the building it is on, which way you face as you step out, how far to turn to begin, what the building looks like, and which buildings, roads, and paths are around you.
- **Route choices.** Each comes with its distance, time, flights of stairs, street crossings, number of steps, and a one-line description:
  - most direct
  - step-free
  - fewest road crossings
  - fewest turns
- **Every step is a heading.** Each step is its own level 4 heading ("Step 3 of 11: Turn left onto the walkway and go 600 feet"), so screen reader users can jump step to step with <kbd>H</kbd> or <kbd>4</kbd>.
- **Along the way.** Under each step, a list of every intersecting path, road, stairway, and crosswalk, the direction it runs, how far into the step you reach it, and the buildings you pass.
- **Route settings:**
  - Direction style: compass ("Walk north"), left and right ("Turn left"), or both ("Turn left to head north")
  - Detail: paths and buildings, paths only, buildings only, or turns only
  - Which route type to show first
  - Always avoid stairs
- **Use my location.** Fills the From box with the eight nearest buildings, closest first, plus an option to start exactly where you are. Your location stays on your device: it is never saved, never sent anywhere, and never put into a link.
- Show the return trip, copy the directions as text, or open the same trip in Google Maps.

### Accessibility details
- A skip link, labeled landmarks, breadcrumbs, and a logical heading outline on every page
- Focus moves to the new heading and the page title changes on every view
- Polite live-region announcements for search counts, route summaries, and setting changes
- The From and To boxes follow the ARIA 1.2 combobox pattern (arrow keys, <kbd>Enter</kbd>, <kbd>Escape</kbd>)
- Route options and settings are radio groups with descriptions; changing one never moves focus
- Visual maps are hidden from screen readers because the same information is in the text
- Text size setting (three sizes), feet or meters, light and dark themes, and a phone-friendly layout
- The typeface is Atkinson Hyperlegible, designed for low-vision readers

## Using it

- **On GitHub Pages:** once Pages is turned on for this repository (see below), open `https://<your-username>.github.io/<repository-name>/`.
- **On your computer:** open `index.html` in any modern browser. Everything, including all map data, is inside that one file. An internet connection is only used for fonts.
- **With location on your computer:** browsers only share location with secure pages. Serve the folder locally and open `http://localhost:8765`:
  ```bash
  python -m http.server 8765
  ```

### Publishing with GitHub Pages
1. In the repository, open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**, then select the `main` branch and the `/ (root)` folder, and save.
3. After a minute or two, the site is live at `https://<your-username>.github.io/<repository-name>/`.

GitHub Pages serves every site over HTTPS, so **"Use my location" works there**. Your browser asks for permission the first time you press the button.

## How it is built

`index.html` is generated. Edit `build/template.html`, then rebuild.

| File | Purpose |
|---|---|
| `build/template.html` | The app: markup, styles, and all JavaScript (routing, directions, accessibility) |
| `build/build_data.py` | Pulls places, descriptions, and photo descriptions from the campus map's public data feed → `data.json` |
| `build/build_paths.py` | Pulls walkways, sidewalks, stairs, and crosswalks from OpenStreetMap → `paths.json` |
| `build/build_entrances.py` | Matches campus buildings to OpenStreetMap footprints and their mapped entrances → `entrances.json` |
| `build/assemble.py` | Embeds the three data files into the template → `index.html` |
| `build/audit_directions.js` | Plans hundreds of routes in every style and checks the finished text for contradictions |

To refresh the data and rebuild (Python 3, no extra packages):

```bash
python build/build_data.py
python build/build_paths.py
python build/build_entrances.py
python build/assemble.py
```

To audit the directions after any change (Node.js; the last number is how many building pairs to test):

```bash
node build/audit_directions.js index.html 300
```

The audit checks the finished text for:
- identical steps back to back
- a turn word that doesn't match the change in compass heading
- a path said to "cross" while running the same way you are walking
- "left" or "right" appearing in compass mode

The current version passes on 1,954 routes (27,693 steps).

Routes are computed in the browser with Dijkstra's algorithm over the embedded path network, usually in about 10 to 70 milliseconds. Nothing is sent to a server.

## Limitations

- **Map data can be wrong or out of date.** OpenStreetMap is edited by volunteers, so a missing path, a misplaced door, or a closed crosswalk will produce a wrong route. Routes know nothing about construction closures or locked doors.
- **About 40% of building records have no mapped entrances.** For those, routes start and end on the nearest walkway, and the directions say so.
- **Stairs direction is unknown.** OpenStreetMap usually does not record whether stairs go up or down.
- **Distances are estimates.** Distances on place pages are straight lines between building centers.
- **Test routes you rely on.** Walk them once with a sighted companion before depending on them.

## Data sources and credits

- **Campus places, descriptions, and photo descriptions:** the official CU Boulder interactive campus map (Concept3D map 336), © University of Colorado Boulder. They are used here to make that information accessible. Please refer to [colorado.edu/map](https://www.colorado.edu/map) for the official map.
- **Walkways, sidewalks, stairs, crosswalks, building footprints, and entrances:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). The derived files `build/paths.json` and `build/entrances.json` are also made available under the ODbL.
- **Typeface:** [Atkinson Hyperlegible](https://www.brailleinstitute.org/freefont/) by the Braille Institute, served from Google Fonts.
