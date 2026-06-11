# Code Structure

## Source Hierarchy

Source code organization should mirror the architectural structure defined in `docs/arch/04`. The specific layout depends on the technology stack chosen.

Source code is derived from designs in the `docs/design/` folder.

## Test Hierarchy

Test organization should diverge into `system/` and `unit/` folders.

The `unit/` folder is for unit tests that mirror the source hierarchy, with test files co-located or in parallel directories depending on project conventions.

The `system/` folder is for system tests that integrate multiple units and focus on use cases and system archetypes, so should use those to guide the structure.
