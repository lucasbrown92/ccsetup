/**
 * claude-witness Vitest plugin
 *
 * Captures test-level results automatically via the Vitest reporter API,
 * and provides witnessWrap() for explicit function-level call capture.
 * Writes .claude/witness/<run_id>.json in the same format as the pytest plugin.
 *
 * SETUP
 * -----
 * // vitest.config.js
 * import { WitnessReporter } from './claude-witness/vitest_plugin.js'
 * export default defineConfig({
 *   test: { reporters: ['default', new WitnessReporter()] }
 * })
 *
 * FUNCTION CAPTURE (opt-in)
 * -------------------------
 * import { witnessWrap } from './claude-witness/vitest_plugin.js'
 * const tracedProcess = witnessWrap(processPayment, 'processPayment')
 * // calls to tracedProcess are recorded in the witness store
 *
 * ENVIRONMENT VARIABLES
 * ---------------------
 * CLAUDE_WITNESS_DIR   Store directory (default: .claude/witness)
 * WITNESS_MAX_CALLS    Max function calls per run (default: 5000)
 */

import { writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { randomBytes } from 'node:crypto'

const STORE_DIR = process.env.CLAUDE_WITNESS_DIR ?? '.claude/witness'
const MAX_CALLS = parseInt(process.env.WITNESS_MAX_CALLS ?? '5000', 10)
const PROJECT_ROOT = resolve(process.cwd())

// ---------------------------------------------------------------------------
// Shared run state (module-level singleton for this process)
// ---------------------------------------------------------------------------
const _run = {
  id: null,
  timestamp: null,
  status: 'pass',
  tests: [],
  calls: [],
  exceptions: [],
  coverage: {},   // file -> Set<lineNo> — populated if V8 coverage available
  callCount: 0,
}

let _currentTest = ''

function _initRun() {
  const ts = new Date().toISOString()
  const short = randomBytes(3).toString('hex')
  const datePart = ts.slice(0, 19).replace(/[-T:]/g, '').slice(0, 15)
  _run.id = `${datePart}_${short}`
  _run.timestamp = ts
}

// ---------------------------------------------------------------------------
// Safe serialization (mirrors Python serializer logic)
// ---------------------------------------------------------------------------
function safeSerialize(value, depth = 0) {
  if (depth > 3) return '<max-depth>'
  if (value === null || value === undefined) return value
  const t = typeof value
  if (t === 'boolean' || t === 'number') return value
  if (t === 'string') return value.length <= 500 ? value : value.slice(0, 500) + '...<truncated>'
  if (t === 'function') return `<function:${value.name || 'anonymous'}>`
  if (t === 'symbol') return `<symbol:${String(value)}>`
  if (t === 'bigint') return value.toString()
  if (value instanceof Error) return `<${value.constructor.name}:${value.message}>`
  if (value instanceof Date) return value.toISOString()
  if (value instanceof RegExp) return String(value)
  if (Array.isArray(value)) {
    const items = value.slice(0, 20).map(v => safeSerialize(v, depth + 1))
    if (value.length > 20) items.push(`...<array length=${value.length}>`)
    return items
  }
  // Generator / iterator
  if (value[Symbol.iterator] && t === 'object' && !Array.isArray(value)) {
    const proto = Object.getPrototypeOf(value)
    if (proto && proto.constructor && proto.constructor.name !== 'Object') {
      return `<${proto.constructor.name}>`
    }
  }
  if (t === 'object') {
    try {
      const keys = Object.keys(value).slice(0, 20)
      const result = {}
      for (const k of keys) {
        try { result[k] = safeSerialize(value[k], depth + 1) } catch { result[k] = '<error>' }
      }
      if (Object.keys(value).length > 20) result['...'] = `<+${Object.keys(value).length - 20} more>`
      return result
    } catch {
      return `<object:${value.constructor?.name ?? 'unknown'}>`
    }
  }
  return String(value)
}

function getCallerFile() {
  try {
    const stack = new Error().stack?.split('\n') ?? []
    // Skip first 3 frames (Error, getCallerFile, witnessWrap wrapper)
    for (let i = 3; i < stack.length; i++) {
      const line = stack[i]
      const match = line.match(/\((.+?):\d+:\d+\)/) ?? line.match(/at (.+?):\d+:\d+/)
      if (match) {
        const file = match[1]
        if (!file.includes('node_modules') && !file.includes('vitest_plugin')) {
          try { return relative(PROJECT_ROOT, file) } catch { return file }
        }
      }
    }
  } catch { /* ignore */ }
  return '<unknown>'
}

// ---------------------------------------------------------------------------
// witnessWrap — explicit function-level capture
// ---------------------------------------------------------------------------

/**
 * Wrap a function to record all calls in the witness store.
 *
 * @param {Function} fn - The function to wrap
 * @param {string} [name] - Display name (defaults to fn.name)
 * @returns {Function} - Wrapped function with identical signature
 *
 * @example
 * import { witnessWrap } from './claude-witness/vitest_plugin.js'
 * const traced = witnessWrap(processPayment, 'payments.processPayment')
 * // All calls to traced() are recorded automatically
 */
export function witnessWrap(fn, name) {
  const qualifiedName = name ?? fn?.name ?? '<anonymous>'
  return function _witnessWrapped(...args) {
    if (_run.callCount >= MAX_CALLS) return fn.apply(this, args)

    const callId = `c${String(_run.callCount++).padStart(5, '0')}`
    const file = getCallerFile()

    // Serialize args using parameter names if available
    const serializedArgs = {}
    const paramStr = fn.toString().match(/\(([^)]*)\)/)?.[1] ?? ''
    const paramNames = paramStr.split(',').map(p => p.trim().replace(/[=\s].*/, '')).filter(Boolean)
    args.forEach((arg, i) => {
      const key = paramNames[i] || `arg${i}`
      serializedArgs[key] = safeSerialize(arg)
    })

    const record = {
      id: callId,
      test: _currentTest,
      fn: qualifiedName,
      file,
      line: 0,
      depth: 1,
      args: serializedArgs,
      return: null,
      exception: null,
    }
    _run.calls.push(record)

    try {
      const result = fn.apply(this, args)
      // Handle promises
      if (result && typeof result.then === 'function') {
        return result.then(
          res => { record.return = safeSerialize(res); return res },
          err => {
            record.exception = err?.constructor?.name ?? 'Error'
            _run.exceptions.push({
              test: _currentTest,
              type: err?.constructor?.name ?? 'Error',
              message: safeSerialize(err?.message ?? String(err)),
              file,
              line: 0,
              locals: {},
            })
            throw err
          }
        )
      }
      record.return = safeSerialize(result)
      return result
    } catch (err) {
      record.exception = err?.constructor?.name ?? 'Error'
      _run.exceptions.push({
        test: _currentTest,
        type: err?.constructor?.name ?? 'Error',
        message: safeSerialize(err?.message ?? String(err)),
        file,
        line: 0,
        locals: {},
      })
      throw err
    }
  }
}

// ---------------------------------------------------------------------------
// writeRunFile — flush captured data to disk
// ---------------------------------------------------------------------------
function writeRunFile() {
  if (!_run.id) return
  try {
    if (!existsSync(STORE_DIR)) mkdirSync(STORE_DIR, { recursive: true })
    const outPath = join(STORE_DIR, `${_run.id}.json`)
    const payload = {
      run_id: _run.id,
      timestamp: _run.timestamp,
      status: _run.status,
      project_root: PROJECT_ROOT,
      runtime: 'node',
      call_count: _run.calls.length,
      tests: _run.tests,
      calls: _run.calls,
      exceptions: _run.exceptions,
      coverage: Object.fromEntries(
        Object.entries(_run.coverage).map(([k, v]) => [k, [...v].sort((a, b) => a - b)])
      ),
    }
    writeFileSync(outPath, JSON.stringify(payload, null, 2) + '\n', 'utf8')
    const n = _run.tests.length
    const c = _run.calls.length
    const e = _run.exceptions.length
    process.stderr.write(`\nclaude-witness: ${n} tests, ${c} calls, ${e} exceptions → ${outPath}\n`)
  } catch (err) {
    process.stderr.write(`\nclaude-witness: failed to write run file: ${err.message}\n`)
  }
}

// ---------------------------------------------------------------------------
// WitnessReporter — implements Vitest's Reporter interface
// ---------------------------------------------------------------------------

/**
 * Vitest custom reporter for claude-witness.
 *
 * Records test results and writes .claude/witness/<run_id>.json on completion.
 *
 * Usage in vitest.config.js:
 *   import { WitnessReporter } from './claude-witness/vitest_plugin.js'
 *   export default defineConfig({
 *     test: { reporters: ['verbose', new WitnessReporter()] }
 *   })
 */
export class WitnessReporter {
  constructor(options = {}) {
    this.options = options
    _initRun()
  }

  // Called as individual tasks (tests) update their state
  onTaskUpdate(packs) {
    for (const [id, result] of packs) {
      if (!result) continue
      // result.state: 'pass' | 'fail' | 'skip' | 'todo' | 'run'
      if (result.state === 'run') {
        _currentTest = id
      }
      if (result.state === 'pass' || result.state === 'fail' || result.state === 'skip') {
        const testName = result.name ?? id
        const duration = result.duration ?? 0
        const status = result.state === 'pass' ? 'pass' : result.state === 'fail' ? 'fail' : 'skip'
        // Avoid duplicate entries
        if (!_run.tests.find(t => t.name === testName)) {
          _run.tests.push({ name: testName, status, duration: Math.round(duration) / 1000 })
        }
        if (status === 'fail') _run.status = 'fail'
      }
    }
  }

  // Called with final file results
  onFinished(files, errors) {
    // Supplement test list from files if onTaskUpdate was sparse
    if (files) {
      for (const file of files) {
        for (const task of (file.tasks ?? [])) {
          this._collectTasks(task)
        }
      }
    }
    writeRunFile()
  }

  _collectTasks(task) {
    if (task.type === 'test') {
      const status = task.result?.state === 'pass' ? 'pass'
        : task.result?.state === 'fail' ? 'fail' : 'skip'
      const name = task.name ?? task.id
      if (!_run.tests.find(t => t.name === name)) {
        _run.tests.push({
          name,
          status,
          duration: Math.round(task.result?.duration ?? 0) / 1000,
        })
        if (status === 'fail') _run.status = 'fail'
      }
    }
    for (const child of (task.tasks ?? [])) {
      this._collectTasks(child)
    }
  }
}

// ---------------------------------------------------------------------------
// Default export — Vitest plugin factory (alternative config style)
// ---------------------------------------------------------------------------

/**
 * Alternative: use as a Vitest plugin in plugins[] array.
 * This registers WitnessReporter automatically.
 *
 * @example
 * import witnessPlugin from './claude-witness/vitest_plugin.js'
 * export default defineConfig({ plugins: [witnessPlugin()] })
 */
export default function witnessPlugin(options = {}) {
  return {
    name: 'claude-witness',
    configureVitest(vitest) {
      vitest.config.reporters = [
        ...(vitest.config.reporters ?? ['default']),
        new WitnessReporter(options),
      ]
    },
  }
}
