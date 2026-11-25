// Experiment A, Claude column: count Claude input tokens for each representation.
//
// Method: send each representation inside a fixed wrapper to a Claude model with no tools
// and one turn, read the reported input tokens (input + cache read + cache creation), and
// subtract the same number for the wrapper with an empty document (baseline, run twice).
// The difference is the token count of the representation itself.
//
// Runs through the Claude Agent SDK with the current Claude Code login (no API key).
// Run from the repository root:
//   node article-01/demo/scripts/claude_token_count.mjs [model]
import { readFileSync, writeFileSync } from 'node:fs';
import { query } from '@anthropic-ai/claude-agent-sdk';

// The package does not export ./package.json; read it from the resolved entry's folder.
const SDK_VERSION = JSON.parse(
  readFileSync(
    new URL('package.json', import.meta.resolve('@anthropic-ai/claude-agent-sdk')),
    'utf8',
  ),
).version;
const MODEL = process.argv[2] ?? 'haiku';
const DEMO = new URL('../', import.meta.url);
const RESEARCH = new URL('../../research/', import.meta.url);
const IDS = [
  'xlsx_structured',
  'xlsx_markitdown',
  'md_raw',
  'html_raw',
  'html_no_css_js',
  'html_spec_only',
  'html_spec_nolinks',
  'html_markitdown',
  'html_css_only',
  'html_js_only',
  'html_preview_only',
  'json_source',
];
const wrap = (doc) =>
  `計測用の入力です。返答は「OK」の2文字だけにしてください。\n<document>\n${doc}\n</document>`;

async function count(doc) {
  let result;
  for await (const m of query({
    prompt: wrap(doc),
    options: {
      model: MODEL,
      tools: [],
      maxTurns: 1,
      maxBudgetUsd: 0.1,
      systemPrompt: 'You are a measurement endpoint.',
      settingSources: [],
      persistSession: false,
    },
  })) {
    if (m.type === 'result') result = m;
  }
  const u = result.usage;
  return {
    input: u.input_tokens + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0),
    cost: result.total_cost_usd,
    models: Object.keys(result.modelUsage ?? {}),
  };
}

const b1 = await count('');
const b2 = await count('');
if (b1.input !== b2.input) console.warn(`baseline differs: ${b1.input} vs ${b2.input}`);
const counts = {};
const raw = {};
let cost = b1.cost + b2.cost;
const models = new Set([...b1.models, ...b2.models]);
for (const id of IDS) {
  const text = readFileSync(new URL(`representations/${id}.txt`, DEMO), 'utf8');
  const r = await count(text);
  raw[id] = r.input;
  counts[id] = r.input - b1.input;
  cost += r.cost;
  r.models.forEach((x) => models.add(x));
  console.log(`${id.padEnd(18)} ${String(counts[id]).padStart(7)}`);
}
const out = {
  model: [...models].join(', '),
  requestedModel: MODEL,
  sdk: `@anthropic-ai/claude-agent-sdk ${SDK_VERSION}`,
  measuredAt: new Date().toISOString(),
  method:
    'input tokens (incl. cache read/creation) of wrapper+document minus wrapper with empty document',
  baseline: [b1.input, b2.input],
  rawInputTokens: raw,
  counts,
  totalCostUsd: Number(cost.toFixed(4)),
};
writeFileSync(new URL('claude-token-counts.json', RESEARCH), JSON.stringify(out, null, 2) + '\n');
console.log(`model ${out.model}, baseline ${out.baseline}, cost $${out.totalCostUsd}`);
