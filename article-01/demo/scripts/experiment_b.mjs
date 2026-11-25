// Experiment B: the same extraction task on the same spec in three formats.
//
// For each format, the spec file is copied ALONE into a fresh empty directory, and a
// Claude agent (Claude Agent SDK, Claude Code system prompt and tools, no CLAUDE.md)
// answers six questions as JSON. Answers are scored against spec/order_spec.json.
// Recorded per run: input/output tokens, turns, tool calls, duration, cost, accuracy.
//
// Uses the current Claude Code login (no API key). Run from the repository root:
//   node article-01/demo/scripts/experiment_b.mjs <workdir> [runs] [model]
import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

// Logged tool inputs must not contain the local user's home path.
const HOME = homedir();
const anonymize = (s) =>
  [JSON.stringify(HOME).slice(1, -1), HOME, HOME.replaceAll('\\', '/')].reduce(
    (acc, h) => acc.split(h).join('~'),
    s,
  );
import { query } from '@anthropic-ai/claude-agent-sdk';

const WORK = process.argv[2];
const RUNS = Number(process.argv[3] ?? 3);
const MODEL = process.argv[4] ?? 'haiku';
const TOTAL_CAP_USD = 0.9;
if (!WORK)
  throw new Error('usage: experiment_b.mjs <empty work dir outside the repo> [runs] [model]');
const DEMO = new URL('../', import.meta.url);
const RESEARCH = new URL('../../research/', import.meta.url);
const SPEC = JSON.parse(readFileSync(new URL('spec/order_spec.json', DEMO), 'utf8'));
const FORMATS = ['xlsx', 'md', 'html'];

const PROMPT = (
  file,
) => `The current directory contains exactly one screen design specification file: ${file}
Use only that file. Do not look at any other directory.
Answer the questions below and reply with ONLY one JSON object (no Markdown fence, no prose):
{
  "business_rule_ids": [every business rule ID defined in the spec, e.g. "BR-001"],
  "always_required_input_items": [IDs of the items marked as always required],
  "conditionally_required_items": [IDs of the items marked as conditionally required],
  "quantity_validation": {"min": number, "max": number, "integer_only": boolean, "message_id": "the error message ID for an out-of-range quantity"},
  "approval": {"threshold_yen": number, "tax_included": boolean, "status_after_registration": "status text in the spec's language"},
  "suspended_customer_code": "the customer code in the test data whose status prevents registering an order"
}`;

// ---- Ground truth, derived from the JSON source
const TRUTH = {
  business_rule_ids: SPEC.businessRules.map((b) => b.id),
  always_required_input_items: SPEC.items.filter((i) => i.required === '○').map((i) => i.id),
  conditionally_required_items: SPEC.items.filter((i) => i.required === '△').map((i) => i.id),
  quantity_validation: { min: 1, max: 9999, integer_only: true, message_id: 'MSG-E006' },
  approval: { threshold_yen: 1000000, tax_included: true, status_after_registration: '承認待ち' },
  suspended_customer_code: SPEC.testData.customers.find((c) => c.status === '取引停止').code,
};
const sameSet = (a, b) =>
  Array.isArray(a) && a.length === b.length && [...a].sort().join() === [...b].sort().join();
function score(ans) {
  if (!ans) return { total: 0, detail: {} };
  const q = ans.quantity_validation ?? {};
  const ap = ans.approval ?? {};
  const t = TRUTH;
  const detail = {
    Q1_business_rules: sameSet(ans.business_rule_ids, t.business_rule_ids),
    Q2_required: sameSet(ans.always_required_input_items, t.always_required_input_items),
    Q3_conditional: sameSet(ans.conditionally_required_items, t.conditionally_required_items),
    Q4_quantity:
      q.min === 1 && q.max === 9999 && q.integer_only === true && q.message_id === 'MSG-E006',
    Q5_approval:
      ap.threshold_yen === 1000000 &&
      ap.tax_included === true &&
      String(ap.status_after_registration).includes('承認待ち'),
    Q6_suspended: ans.suspended_customer_code === t.suspended_customer_code,
  };
  return { total: Object.values(detail).filter(Boolean).length, detail };
}
function parseAnswer(text) {
  const m = text?.match(/\{[\s\S]*\}/);
  try {
    return m ? JSON.parse(m[0]) : null;
  } catch {
    return null;
  }
}

async function run(format, n) {
  const dir = join(WORK, `${format}-${n}`);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const file = `order_design.${format}`;
  copyFileSync(new URL(file, DEMO), join(dir, file));
  const tools = [];
  let result;
  const started = Date.now();
  for await (const m of query({
    prompt: PROMPT(file),
    options: {
      model: MODEL,
      cwd: dir,
      systemPrompt: { type: 'preset', preset: 'claude_code' },
      tools: ['Read', 'Glob', 'Grep', 'Bash'],
      allowedTools: ['Read', 'Glob', 'Grep', 'Bash'],
      settingSources: [],
      maxTurns: 20,
      maxBudgetUsd: 0.15,
      persistSession: false,
    },
  })) {
    if (m.type === 'assistant') {
      for (const c of m.message.content) {
        if (c.type === 'tool_use') {
          const input = anonymize(
            JSON.stringify(c.input)
              .split(JSON.stringify(dir).slice(1, -1))
              .join('.')
              .split(dir.replaceAll('\\', '/'))
              .join('.'),
          );
          tools.push(`${c.name}: ${input.slice(0, 400)}`);
        }
      }
    }
    if (m.type === 'result') result = m;
  }
  const usage = Object.values(result.modelUsage ?? {}).reduce(
    (a, u) => ({
      input: a.input + u.inputTokens + u.cacheReadInputTokens + u.cacheCreationInputTokens,
      cacheRead: a.cacheRead + u.cacheReadInputTokens,
      output: a.output + u.outputTokens,
    }),
    { input: 0, cacheRead: 0, output: 0 },
  );
  const answer = parseAnswer(result.result);
  const s = score(answer);
  return {
    format,
    run: n,
    model: Object.keys(result.modelUsage ?? {}).join(', '),
    subtype: result.subtype,
    inputTokensTotal: usage.input,
    cacheReadTokens: usage.cacheRead,
    outputTokens: usage.output,
    turns: result.num_turns,
    toolCalls: tools.length,
    tools,
    durationMs: result.duration_ms ?? Date.now() - started,
    costUsd: result.total_cost_usd,
    score: s.total,
    scoreDetail: s.detail,
    answer,
  };
}

const runs = [];
let spent = 0;
for (let n = 1; n <= RUNS; n++) {
  for (const format of FORMATS) {
    if (spent > TOTAL_CAP_USD) {
      console.warn(`budget cap reached ($${spent.toFixed(3)}); stopping`);
      break;
    }
    const r = await run(format, n);
    spent += r.costUsd;
    runs.push(r);
    console.log(
      `${format.padEnd(4)} run ${n}: score ${r.score}/6, in ${r.inputTokensTotal}, out ${r.outputTokens}, turns ${r.turns}, tools ${r.toolCalls}, ${(r.durationMs / 1000).toFixed(1)}s, $${r.costUsd.toFixed(4)}`,
    );
  }
}
const meta = {
  model: MODEL,
  sdk: '@anthropic-ai/claude-agent-sdk',
  measuredAt: new Date().toISOString(),
  totalCostUsd: Number(spent.toFixed(4)),
  truth: TRUTH,
};
writeFileSync(
  new URL('experiment-b-runs.json', RESEARCH),
  JSON.stringify({ meta, runs }, null, 2) + '\n',
);
const head =
  'format,run,model,score_of_6,input_tokens_total,cache_read_tokens,output_tokens,turns,tool_calls,duration_s,cost_usd';
const lines = runs.map((r) =>
  [
    r.format,
    r.run,
    r.model,
    r.score,
    r.inputTokensTotal,
    r.cacheReadTokens,
    r.outputTokens,
    r.turns,
    r.toolCalls,
    (r.durationMs / 1000).toFixed(1),
    r.costUsd.toFixed(4),
  ].join(','),
);
writeFileSync(new URL('experiment-b-results.csv', RESEARCH), [head, ...lines].join('\n') + '\n');
console.log(`total cost $${spent.toFixed(4)}`);
