# AGENTS.md

## Learning Project

- This is a learning project. Keep changes easy for the owner to read, understand, and maintain at their current level of experience.
- Make the smallest direct change that satisfies the request. A small request should produce a small, understandable diff.
- Follow the existing code structure. Explain any additional complexity that is genuinely required before introducing it.
- When asked to add meaningful tool return values, default to plain text returned directly from each existing tool function. Include enough information to understand the outcome and decide what to do next.
- Introduce wrappers, decorators, response builders, shared result helpers, or structured response models only when explicitly requested or agreed upon.

## Code Style

- Write code like a senior engineer teaching a junior developer. Keep the codebase approachable while avoiding unnecessary bloat.
- Prefer simple, explicit syntax over clever or complex abstractions. If five clear lines explain the intent better than one dense line, use the clearer version.
- Add abstractions only when they remove real complexity or match an established local pattern, subject to the learning project guidance above.
- Keep flow bouncing low. For a simple local boolean check, keep the check in the function instead of extracting a tiny helper that makes the reader jump away and back.
