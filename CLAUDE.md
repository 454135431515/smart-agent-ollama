# Working Agreement

This is a portfolio project. After every refactoring iteration, the README must reflect the actual state of the code. Inflated claims hurt more than honest gaps.

## After every iteration, you MUST:

1. **Update README.md** to reflect changes made in this iteration:
   - Update the "What's inside" section if new components/patterns appeared
   - Update the "Tech stack" list if new dependencies were added
   - Update setup/run instructions if they changed
   - Update the project structure tree if files moved/were deleted
   - If something was removed (e.g., a redundant file) — remove it from README too

2. **Update the "Changelog" section** at the bottom of README:
   - Add a new entry under today's date (`YYYY-MM-DD`)
   - One bullet per significant change, written from the user's perspective ("added X", "fixed Y"), not from the code's ("refactored function Z")
   - Skip trivial changes (formatting, typos)

3. **Verify claims**: every technical claim in README must be backed by code that exists in this commit. If you claim "Pydantic-validated tools" — there must be Pydantic models. If you claim "test coverage" — there must be tests. No aspirational language.

4. **Forbidden words in README**: "production-ready", "enterprise-grade", "scalable", "innovative", "cutting-edge", "revolutionary". Also avoid SOLID/DDD/Clean Architecture unless the code clearly demonstrates them.

5. **Tone**: technical, factual, honest. This is a learning project — the README should sound like an engineer describing their work, not a marketing page.

6. **Show the diff**: at the end of each iteration, briefly mention which README sections you changed and why.

## When adding a new tool

Every new tool requires three coordinated changes:

1. `tools/<name>.py` — the tool itself, decorated with `@tool(...)`.
2. `import tools.<name>  # noqa: F401` in `app/agent.py`. Without this, the `@tool` decorator never runs and the tool is invisible to `TOOL_REGISTRY` even though the file exists.
3. Any new third-party dependencies pinned explicitly in `pyproject.toml`. Never rely on transitive deps coming in through another package — that's how PR #10 shipped with a working local install but a broken clean install.

After the change, verify with a smoke check that the tool actually ends up in `TOOL_REGISTRY`:

```bash
python -c "
from app.agent import SmartAgent
from app.registry import TOOL_REGISTRY
assert '<your_tool_name>' in TOOL_REGISTRY, 'tool not registered'
print('OK')
"
```

This is the check that would have caught PR #10's incomplete merge before review.

## Other rules

- Don't expand scope. If the iteration prompt says "do X, Y, Z" — do exactly X, Y, Z, no bonus features.
- Always run `python -c "from app.agent import SmartAgent"` after import-affecting changes.
- Don't reformat files you didn't touch logically. No drive-by reformatting.
- Commit messages: imperative mood ("add Pydantic schemas", not "added" or "adds"). Conventional Commits format welcome but not required.
