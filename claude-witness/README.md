# claude-witness

> **v1.0.1**

Execution memory for Python, JS/TS, and Go projects — standalone MCP server + language plugins.

Captures what actually ran: function calls, arguments, return values, exceptions, and line coverage. Queryable across sessions. The evidence channel that doesn't exist anywhere else in the Claude tool stack.

## The Problem It Solves

Claude infers from source code what *should* happen. Decorators, monkey-patching, DI containers, async behavior, and runtime config mean what *actually* happens may differ entirely. `claude-witness` gives you empirical execution data from real test runs.

## Architecture

```
pytest --witness               Python capture (pytest_plugin.py via sys.settrace)
vitest + WitnessReporter       JS/TS capture (vitest_plugin.js)
jest + WitnessReporter         JS/TS capture (jest_reporter.js)
witness.NewRun() + Flush()     Go capture (go_hook.go)
    ↓
.claude/witness/               one JSON file per run (same format, all runtimes)
    ↓
server.py (MCP)                query layer — never a firehose
```

## Tools

| Tool | Description |
|------|-------------|
| `witness_runs(limit?)` | List recent runs with pass/fail status — first call in any debugging session |
| `witness_hotspots(limit?, run_count?)` | Functions with the most exceptions across recent runs — call before `witness_traces` |
| `witness_traces(fn_name, run_id?, status?)` | All calls to a function — args, return values, depth |
| `witness_exception(exc_type, run_id?)` | Exception frames with local variable state at crash site |
| `witness_coverage_gaps(file)` | Lines in a file never executed across recent runs |
| `witness_diff(run_a, run_b)` | Delta between two runs: tests, functions, exceptions |
| `witness_check_charter(run_id?)` | Cross-check run against charter invariants/constraints — uses shared tokenizer |

## JS/TS Capture — Vitest

```js
// vitest.config.js
import { WitnessReporter } from './claude-witness/vitest_plugin.js'
export default defineConfig({
  test: { reporters: ['verbose', new WitnessReporter()] }
})
```

For function-level capture (opt-in — mirrors Python's automatic settrace):

```js
import { witnessWrap } from './claude-witness/vitest_plugin.js'

test('payment flow', async () => {
  const traced = witnessWrap(processPayment, 'payments.processPayment')
  expect(await traced({ amount: 100 })).toBe(true)
  // All calls to traced() are recorded in .claude/witness/
})
```

## JS/TS Capture — Jest

```js
// jest.config.js
module.exports = {
  reporters: ['default', ['<rootDir>/claude-witness/jest_reporter.js', {}]]
}
```

```js
// In tests:
const { witnessWrap } = require('./claude-witness/jest_reporter.js')
const traced = witnessWrap(processPayment, 'payments.processPayment')
```

## Go Capture

```go
// In TestMain (required for Flush):
func TestMain(m *testing.M) {
    w := witness.NewRun()
    code := m.Run()
    w.Flush()
    os.Exit(code)
}

// Per-test — for function-level capture:
func TestPayment(t *testing.T) {
    tw := w.ForTest(t)   // w is the *witness.Run from TestMain
    result := tw.Trace("payments.processPayment", func() any {
        return processPayment(Payment{Amount: 100})
    })
    // result captured and recorded in .claude/witness/
}
```

Copy `go_hook.go` into your project as `package witness` or import it as a module.

## Auto-Trigger from Claude Code Sessions

To automatically run `pytest --witness` whenever tests are run in a Claude Code session, add a hook to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'pytest' && ! echo \"$CLAUDE_TOOL_INPUT\" | grep -q '\\-\\-witness'; then echo 'Tip: add --witness to capture execution evidence for claude-witness'; fi"
      }]
    }]
  }
}
```

For fully automatic capture (opt-in globally):

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "# Replace pytest invocations with pytest --witness automatically",
        "script": "python3 -c \"import sys,os; cmd=os.environ.get('CLAUDE_TOOL_INPUT',''); print(cmd.replace('pytest ', 'pytest --witness ', 1) if 'pytest' in cmd and '--witness' not in cmd else cmd)\""
      }]
    }]
  }
}
```

## Install

### 1. Add to `.mcp.json`

```json
{
  "mcpServers": {
    "claude-witness": {
      "command": "python3",
      "args": ["/path/to/claude-witness/server.py"],
      "env": {}
    }
  }
}
```

### 2. Add to project `conftest.py`

```python
# conftest.py — at your project root
import sys
sys.path.insert(0, "/path/to/claude-witness")
from pytest_plugin import *   # noqa
```

### 3. Run with `--witness`

```bash
pytest --witness                     # trace all tests
pytest --witness tests/test_auth.py  # trace specific file
pytest --witness --witness-depth 5   # deeper call tree (default: 3)
```

## Usage Pattern

```python
# 1. Run tests with witness
#    $ pytest --witness

# 2. Check what ran
witness_runs()
# → ✓ 20260317_143022_abc123  2026-03-17 14:30:22  47 tests  312 calls

# 3. Investigate a specific function
witness_traces("process_payment")
# → [c00042] payments.process_payment(amount=None, cart_id='cart-7')
#     file: payments/core.py:88  depth:2  test:tests/test_checkout.py::test_empty_cart
#     !! exception: ValueError

# 4. Get the exception frame
witness_exception("ValueError")
# → [ValueError] payments/core.py:92
#     test: tests/test_checkout.py::test_empty_cart
#     message: amount must be positive
#     locals: amount=None, cart_id='cart-7', user=<repr:User(id=99)>

# 5. Find untested paths
witness_coverage_gaps("payments/core.py")
# → Never-executed lines: 110-115, 130, 145-160

# 6. Compare before/after fix
witness_diff("20260317_143022_abc123", "20260317_151045_def456")
# → NEWLY PASSING: test_empty_cart
#   RESOLVED EXCEPTIONS: ValueError
```

## Design Principles

- **Opt-in per run** — `--witness` is never automatic. Tracing changes behavior; you decide when to accept that.
- **Project source only** — stdlib, site-packages, and the plugin itself are excluded from capture.
- **Safe serialization** — generators, ORM entities, circular refs, giant payloads never crash the test run.
- **Depth cap** — default 3 levels from test entry point. Configurable via `--witness-depth` or `WITNESS_MAX_DEPTH`.
- **Call cap** — default 5000 calls per run. Configurable via `--witness-max-calls` or `WITNESS_MAX_CALLS`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_WITNESS_DIR` | `.claude/witness` | Store directory |
| `WITNESS_MAX_DEPTH` | `3` | Max call depth from test entry |
| `WITNESS_MAX_CALLS` | `5000` | Max calls captured per run |

## Integration with mind + charter

```python
# Full trifecta workflow
mind_open("payment null amount bug")
mind_add("assumption", "amount=None only on empty cart")

# Run tests
# $ pytest --witness

witness_traces("process_payment", status="exception")
# Confirms: amount=None called from checkout in 2 tests

charter_check("add null guard in process_payment before db call")
# No conflicts

mind_update(assumption_id, "confirmed", notes="witness run confirms 2 paths")
mind_summary()  # full investigation state after compaction
```

## Stdlib Only

Zero external dependencies. Python 3.10+ (uses `str | None` type hints; easily backported to 3.8 by removing them).
