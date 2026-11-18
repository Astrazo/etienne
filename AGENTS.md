# Code style

- Write code like a senior engineer teaching a junior developer: approachable,
  explicit, and without unnecessary bloat.
- Organise functions into logical chunks. Keep statements for the same task
  together, and separate different stages with a blank line.
- Introduce each meaningful chunk with a short comment explaining its purpose,
  such as `# Build request body` or `# Read the current device states`.
  Comment stages of work rather than narrating every assignment.
- Prefer straightforward loops and named intermediate values when a
  comprehension, generator, nested expression, or assignment expression makes
  the reader work to understand the flow.
- Keep validation, preparation, the main operation, and the UI/result update
  visibly separate where those stages apply.
- Add abstractions only when they remove real complexity or match an established
  local pattern. Do not extract tiny helpers merely to shorten a function.
- Keep simple local checks inside the function so readers do not have to jump
  between functions to follow them.
- For UI builders, label the main layout sections and keep each section's
  widgets together. Explain callbacks and state changes where they affect how
  the page behaves.
