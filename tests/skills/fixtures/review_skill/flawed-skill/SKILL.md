---
name: myBadSkill
description: Helps with things
allowed-tools: Read, Glob, Grep, Edit, Write, Bash
---

This skill processes files provided via `$ARGUMENTS` and generates output.

1. **Gather inputs**
   - Read the files specified by `$ARGUMENTS`
   - Parse contents and identify key sections

2. **Process and transform**
   - Apply transformations to extracted sections
   - Generate a summary of changes made
   - Write output files to the project directory

3. **Final report**
   - Print a summary of what was done
   - List any warnings encountered
