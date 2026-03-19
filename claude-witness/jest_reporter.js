/**
 * claude-witness Jest reporter
 *
 * Captures test-level results via Jest's custom reporter interface,
 * and exports witnessWrap() for explicit function-level call capture.
 * Writes .claude/witness/<run_id>.json in the same format as the pytest plugin.
 *
 * SETUP
 * -----
 * // jest.config.js
 * module.exports = {
 *   reporters: [
 *     'default',
 *     ['<rootDir>/claude-witness/jest_reporter.js', {}]
 *   ]
 * }
 *
 * // In tests — for function-level capture:
 * const { witnessWrap } = require('./claude-witness/jest_reporter.js')
 * const traced = witnessWrap(processPayment, 'payments.processPayment')
 *
 * ENVIRONMENT VARIABLES
 * ---------------------
 * CLAUDE_WITNESS_DIR   Store directory (default: .claude/witness)
 * WITNESS_MAX_CALLS    Max calls to capture per run (default: 5000)
 */

'use strict'

const { writeFileSync, mkdirSync, existsSync } = require('node:fs')
const { join, relative, resolve } = require('node:path')
const { randomBytes } = require('node:crypto')

const STORE_DIR = process.env.CLAUDE_WITNESS_DIR ?? '.claude/witness'
const MAX_CALLS = parseInt(process.env.WITNESS_MAX_CALLS ?? '5000', 10)
const PROJECT_ROOT = resolve(process.cwd())

// ---------------------------------------------------------------------------
// Shared run state
// ---------------------------------------------------------------------------
const _run = {
  id: null,
  timestamp: null,
  status: 'pass',
  tests: [],
  calls: [],
  exceptions: [],
  coverage: {},
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
// Safe serialization
// ---------------------------------------------------------------------------
function safeSerialize(value, depth) {
  if (depth === undefined) depth = 0
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
  if (Array.isArray(value)) {
    const items = value.slice(0, 20).map(v => safeSerialize(v, depth + 1))
    if (value.length > 20) items.push(`...<array length=${value.length}>`)
    return items
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
      return `<object:${value.constructor ? value.constructor.name : 'unknown'}>`
    }
  }
  return String(value)
}

function getCallerFile() {
  try {
    const stack = new Error().stack.split('\n')
    for (let i = 3; i < stack.length; i++) {
      const line = stack[i]
      const match = line.match(/\((.+?):\d+:\d+\)/) || line.match(/at (.+?):\d+:\d+/)
      if (match) {
        const file = match[1]
        if (!file.includes('node_modules') && !file.includes('jest_reporter')) {
          try { return relative(PROJECT_ROOT, file) } catch (e) { return file }
        }
      }
    }
  } catch (e) { /* ignore */ }
  return '<unknown>'
}

// ---------------------------------------------------------------------------
// witnessWrap — explicit function-level capture (same API as vitest_plugin.js)
// ---------------------------------------------------------------------------

/**
 * Wrap a function to record all calls in the witness store.
 * Must be called before the Jest run starts to be most effective,
 * but works at any point within a test file.
 */
function witnessWrap(fn, name) {
  const qualifiedName = name || fn.name || '<anonymous>'
  return function _witnessWrapped() {
    const args = Array.from(arguments)
    if (_run.callCount >= MAX_CALLS) return fn.apply(this, args)

    const callId = `c${String(_run.callCount++).padStart(5, '0')}`
    const file = getCallerFile()

    const paramStr = fn.toString().match(/\(([^)]*)\)/)?.[1] || ''
    const paramNames = paramStr.split(',').map(p => p.trim().replace(/[=\s].*/, '')).filter(Boolean)
    const serializedArgs = {}
    args.forEach(function (arg, i) {
      serializedArgs[paramNames[i] || ('arg' + i)] = safeSerialize(arg)
    })

    const record = {
      id: callId,
      test: _currentTest,
      fn: qualifiedName,
      file: file,
      line: 0,
      depth: 1,
      args: serializedArgs,
      return: null,
      exception: null,
    }
    _run.calls.push(record)

    try {
      const result = fn.apply(this, args)
      if (result && typeof result.then === 'function') {
        return result.then(
          function (res) { record.return = safeSerialize(res); return res },
          function (err) {
            record.exception = (err && err.constructor) ? err.constructor.name : 'Error'
            _run.exceptions.push({
              test: _currentTest,
              type: (err && err.constructor) ? err.constructor.name : 'Error',
              message: safeSerialize(err ? (err.message || String(err)) : ''),
              file: file, line: 0, locals: {},
            })
            throw err
          }
        )
      }
      record.return = safeSerialize(result)
      return result
    } catch (err) {
      record.exception = (err && err.constructor) ? err.constructor.name : 'Error'
      _run.exceptions.push({
        test: _currentTest,
        type: (err && err.constructor) ? err.constructor.name : 'Error',
        message: safeSerialize(err ? (err.message || String(err)) : ''),
        file: file, line: 0, locals: {},
      })
      throw err
    }
  }
}

// ---------------------------------------------------------------------------
// writeRunFile
// ---------------------------------------------------------------------------
function writeRunFile() {
  if (!_run.id) return
  try {
    if (!existsSync(STORE_DIR)) mkdirSync(STORE_DIR, { recursive: true })
    const outPath = join(STORE_DIR, _run.id + '.json')
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
      coverage: {},
    }
    writeFileSync(outPath, JSON.stringify(payload, null, 2) + '\n', 'utf8')
    const n = _run.tests.length
    const c = _run.calls.length
    const e = _run.exceptions.length
    process.stderr.write('\nclaude-witness: ' + n + ' tests, ' + c + ' calls, ' + e + ' exceptions → ' + outPath + '\n')
  } catch (err) {
    process.stderr.write('\nclaude-witness: failed to write run file: ' + err.message + '\n')
  }
}

// ---------------------------------------------------------------------------
// Failure message parsing
// ---------------------------------------------------------------------------

function _extractExcType(msg) {
  // Try common patterns: "TypeError: ...", "Error: ...", "expect(received)..."
  const typeMatch = msg.match(/^(\w+Error):/m)
  if (typeMatch) return typeMatch[1]
  if (msg.includes('expect(')) return 'AssertionError'
  return 'Error'
}

function _extractLine(msg) {
  // Try to find line number from stack trace
  const lineMatch = msg.match(/:(\d+):\d+\)/)
  if (lineMatch) return parseInt(lineMatch[1], 10)
  return 0
}

// ---------------------------------------------------------------------------
// WitnessReporter — Jest custom reporter class
// ---------------------------------------------------------------------------

/**
 * Jest custom reporter for claude-witness.
 *
 * Implements the Jest Reporter interface:
 * https://jestjs.io/docs/configuration#reporters-arraymodulename--modulename-options
 */
class WitnessReporter {
  constructor(globalConfig, reporterOptions) {
    this._globalConfig = globalConfig
    this._options = reporterOptions || {}
    _initRun()
  }

  // Called before any test suite runs
  onRunStart(results, options) {
    // nothing needed — _initRun() already called in constructor
  }

  // Called after each test suite (file) completes
  onTestFileResult(test, testResult, aggregatedResult) {
    const testFile = test.path ? relative(PROJECT_ROOT, test.path) : '<unknown>'
    for (const result of testResult.testResults) {
      const status = result.status === 'passed' ? 'pass'
        : result.status === 'failed' ? 'fail' : 'skip'
      _run.tests.push({
        name: result.fullName,
        status,
        duration: (result.duration || 0) / 1000,
      })
      if (status === 'fail') {
        _run.status = 'fail'
        // Extract exception details from failureMessages
        if (result.failureMessages && result.failureMessages.length > 0) {
          for (const msg of result.failureMessages) {
            const excType = _extractExcType(msg)
            _run.exceptions.push({
              test: result.fullName,
              type: excType,
              message: safeSerialize(msg.split('\n')[0] || ''),
              file: testFile,
              line: _extractLine(msg),
              locals: {},
            })
          }
        }
      }
    }
  }

  // Called after all test suites complete
  onRunComplete(contexts, results) {
    writeRunFile()
  }

  // Required by Jest reporter interface
  getLastError() {
    // Return undefined unless we want to fail the run
  }
}

module.exports = WitnessReporter
module.exports.witnessWrap = witnessWrap
module.exports.WitnessReporter = WitnessReporter
