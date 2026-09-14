# Known Limitations

[← Back to README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/tldraw/README.md)

- **Native UML notation**: tldraw renders filled `triangle`/`diamond` arrowheads (fine for inheritance/composition *sketches*) but not the *hollow* heads strict UML uses. For publication-grade UML/ERD figures, use drawio-skill
- **Swimlanes / nested auto-layout**: tldraw *does* have native `frame` containers (labeled boxes you can nest shapes inside, and stack to approximate swimlanes), but no automatic layout *within* them — child positions are still placed by hand. For drawio-style swimlane pools with auto-flow, use drawio-skill
- **PDF export not supported**: tldraw-cli supports PNG and SVG only. Convert SVG to PDF post-hoc if needed (e.g. `rsvg-convert`)
- **Self-check requires vision**: The auto-fix step reads exported PNGs using the model's vision capability. Models without vision support skip this step
