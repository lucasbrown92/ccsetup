// Package witness provides test helpers for claude-witness integration in Go.
//
// This package captures test execution data and writes it to
// .claude/witness/<run_id>.json in the same format as the Python pytest plugin,
// making the data queryable via the claude-witness MCP server.
//
// SETUP
// -----
// In your TestMain:
//
//	func TestMain(m *testing.M) {
//	    w := witness.NewRun()
//	    code := m.Run()
//	    w.Flush()
//	    os.Exit(code)
//	}
//
// For per-test capture:
//
//	func TestPayment(t *testing.T) {
//	    tw := witness.ForTest(t)
//	    result := tw.Trace("payments.processPayment", func() any {
//	        return processPayment(Payment{Amount: 100})
//	    })
//	    _ = result
//	}
//
// ENVIRONMENT VARIABLES
// ---------------------
//   CLAUDE_WITNESS_DIR   Store directory (default: .claude/witness)
//   WITNESS_MAX_CALLS    Max calls per run (default: 5000)
//
// INSTALLATION
// ------------
// Copy this file into your project or import as a module:
//
//	import "github.com/your-org/claude-witness/go_hook"
//
// Or copy directly — this file has no external dependencies.
package witness

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

func storeDir() string {
	if d := os.Getenv("CLAUDE_WITNESS_DIR"); d != "" {
		return d
	}
	return ".claude/witness"
}

func maxCalls() int {
	if v := os.Getenv("WITNESS_MAX_CALLS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return 5000
}

// ---------------------------------------------------------------------------
// Data types (match the Python store format)
// ---------------------------------------------------------------------------

type callRecord struct {
	ID        string         `json:"id"`
	Test      string         `json:"test"`
	Fn        string         `json:"fn"`
	File      string         `json:"file"`
	Line      int            `json:"line"`
	Depth     int            `json:"depth"`
	Args      map[string]any `json:"args"`
	Return    any            `json:"return"`
	Exception *string        `json:"exception"`
}

type exceptionRecord struct {
	Test    string         `json:"test"`
	Type    string         `json:"type"`
	Message string         `json:"message"`
	File    string         `json:"file"`
	Line    int            `json:"line"`
	Locals  map[string]any `json:"locals"`
}

type testRecord struct {
	Name     string  `json:"name"`
	Status   string  `json:"status"`
	Duration float64 `json:"duration"`
}

type runData struct {
	RunID      string            `json:"run_id"`
	Timestamp  string            `json:"timestamp"`
	Status     string            `json:"status"`
	ProjectRoot string           `json:"project_root"`
	Runtime    string            `json:"runtime"`
	CallCount  int               `json:"call_count"`
	Tests      []testRecord      `json:"tests"`
	Calls      []callRecord      `json:"calls"`
	Exceptions []exceptionRecord `json:"exceptions"`
	Coverage   map[string][]int  `json:"coverage"`
}

// ---------------------------------------------------------------------------
// Run — the top-level capture state for one test binary execution
// ---------------------------------------------------------------------------

// Run captures the entire test binary execution.
// Create one per TestMain with NewRun(), then call Flush() when tests complete.
type Run struct {
	mu         sync.Mutex
	data       runData
	maxCalls   int
	projectRoot string
}

// NewRun creates a new witness Run. Call this at the start of TestMain.
func NewRun() *Run {
	ts := time.Now().UTC()
	runID := fmt.Sprintf("%s_%06x",
		ts.Format("20060102_150405"),
		ts.Nanosecond()%0xFFFFFF,
	)

	root, _ := os.Getwd()

	return &Run{
		maxCalls:    maxCalls(),
		projectRoot: root,
		data: runData{
			RunID:       runID,
			Timestamp:   ts.Format(time.RFC3339),
			Status:      "pass",
			ProjectRoot: root,
			Runtime:     "go",
			Tests:       []testRecord{},
			Calls:       []callRecord{},
			Exceptions:  []exceptionRecord{},
			Coverage:    map[string][]int{},
		},
	}
}

// Flush writes the captured run data to .claude/witness/<run_id>.json.
// Call this after m.Run() in TestMain.
func (r *Run) Flush() {
	r.mu.Lock()
	defer r.mu.Unlock()

	r.data.CallCount = len(r.data.Calls)

	dir := storeDir()
	if err := os.MkdirAll(dir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "claude-witness: failed to create store dir: %v\n", err)
		return
	}

	outPath := filepath.Join(dir, r.data.RunID+".json")
	b, err := json.MarshalIndent(r.data, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "claude-witness: failed to marshal run data: %v\n", err)
		return
	}
	b = append(b, '\n')
	if err := os.WriteFile(outPath, b, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "claude-witness: failed to write run file: %v\n", err)
		return
	}

	fmt.Fprintf(os.Stderr, "\nclaude-witness: %d tests, %d calls, %d exceptions → %s\n",
		len(r.data.Tests), len(r.data.Calls), len(r.data.Exceptions), outPath)
}

func (r *Run) recordTest(name, status string, dur float64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.data.Tests = append(r.data.Tests, testRecord{Name: name, Status: status, Duration: dur})
	if status == "fail" {
		r.data.Status = "fail"
	}
}

func (r *Run) addCall(rec callRecord) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if len(r.data.Calls) >= r.maxCalls {
		return
	}
	rec.ID = fmt.Sprintf("c%05d", len(r.data.Calls))
	r.data.Calls = append(r.data.Calls, rec)
}

func (r *Run) addException(rec exceptionRecord) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.data.Exceptions = append(r.data.Exceptions, rec)
}

// ---------------------------------------------------------------------------
// TestWitness — per-test helper
// ---------------------------------------------------------------------------

// TestWitness is a per-test capture handle returned by ForTest.
type TestWitness struct {
	t    testing.TB
	run  *Run
	name string
}

// ForTest creates a TestWitness for the given test.
// Registers a t.Cleanup to record pass/fail automatically.
//
// Usage:
//
//	tw := witness.ForTest(t)
//	result := tw.Trace("myFunc", func() any { return myFunc(arg) })
func (r *Run) ForTest(t testing.TB) *TestWitness {
	tw := &TestWitness{t: t, run: r, name: t.Name()}
	start := time.Now()

	t.Cleanup(func() {
		dur := time.Since(start).Seconds()
		status := "pass"
		if t.Failed() {
			status = "fail"
		} else if t.Skipped() {
			status = "skip"
		}
		r.recordTest(tw.name, status, dur)
	})

	return tw
}

// Trace records a function call. The fn parameter is called immediately;
// its return value is captured. Panics are caught, recorded as exceptions,
// and re-panicked.
//
// Usage:
//
//	result := tw.Trace("payments.processPayment", func() any {
//	    return processPayment(Payment{Amount: 100})
//	})
func (tw *TestWitness) Trace(fnName string, fn func() any, args ...map[string]any) (result any) {
	// Capture caller location
	_, file, line, _ := runtime.Caller(1)
	relFile := relPath(file, tw.run.projectRoot)

	argMap := map[string]any{}
	if len(args) > 0 {
		argMap = args[0]
	}

	defer func() {
		if p := recover(); p != nil {
			excType := fmt.Sprintf("%T", p)
			excMsg := fmt.Sprintf("%v", p)
			tw.run.addException(exceptionRecord{
				Test:    tw.name,
				Type:    excType,
				Message: truncate(excMsg, 500),
				File:    relFile,
				Line:    line,
				Locals:  map[string]any{},
			})
			tw.run.addCall(callRecord{
				Test:      tw.name,
				Fn:        fnName,
				File:      relFile,
				Line:      line,
				Depth:     1,
				Args:      argMap,
				Return:    nil,
				Exception: &excType,
			})
			panic(p) // re-panic so the test still fails correctly
		}
	}()

	result = fn()

	tw.run.addCall(callRecord{
		Test:   tw.name,
		Fn:     fnName,
		File:   relFile,
		Line:   line,
		Depth:  1,
		Args:   argMap,
		Return: safeSerializeGo(result),
	})
	return result
}

// TraceArgs is a convenience version of Trace that accepts explicit arg names.
//
// Usage:
//
//	tw.TraceArgs("payments.processPayment",
//	    witness.Args{"amount": 100, "currency": "USD"},
//	    func() any { return processPayment(100, "USD") },
//	)
type Args = map[string]any

func (tw *TestWitness) TraceArgs(fnName string, args Args, fn func() any) any {
	return tw.Trace(fnName, fn, args)
}

// ---------------------------------------------------------------------------
// Standalone helpers (no Run required) — for quick single-test use
// ---------------------------------------------------------------------------

var _defaultRun *Run
var _defaultRunOnce sync.Once

// DefaultRun returns a module-level singleton Run.
// Useful when you don't control TestMain.
// Must call DefaultFlush() in a TestMain or defer.
func DefaultRun() *Run {
	_defaultRunOnce.Do(func() { _defaultRun = NewRun() })
	return _defaultRun
}

// DefaultFlush flushes the default singleton run to disk.
func DefaultFlush() {
	if _defaultRun != nil {
		_defaultRun.Flush()
	}
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

func relPath(abs, root string) string {
	rel, err := filepath.Rel(root, abs)
	if err != nil {
		return abs
	}
	return filepath.ToSlash(rel)
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "...<truncated>"
}

func safeSerializeGo(v any) any {
	if v == nil {
		return nil
	}
	// Attempt JSON round-trip for serializability check
	b, err := json.Marshal(v)
	if err != nil {
		return fmt.Sprintf("<unserializable:%T>", v)
	}
	if len(b) > 500 {
		return string(b[:500]) + "...<truncated>"
	}
	var out any
	if err := json.Unmarshal(b, &out); err != nil {
		return string(b)
	}
	return out
}

// callerPackage returns the package path of the caller at depth skip.
func callerPackage(skip int) string {
	pc, _, _, ok := runtime.Caller(skip + 1)
	if !ok {
		return ""
	}
	fn := runtime.FuncForPC(pc)
	if fn == nil {
		return ""
	}
	name := fn.Name()
	// Strip method name to get package
	if idx := strings.LastIndex(name, "."); idx >= 0 {
		return name[:idx]
	}
	return name
}
