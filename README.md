# AI駆動開発を実践する — demos

Demos for the article series 「AI駆動開発を実践する — AI-Driven Development in Practice」.
All specifications, data and business rules here are fictional and exist only for the articles.

| Article | Demo | Source |
|---|---|---|
| 01 — Excel 設計書を HTML にしてみた | [HTML screen specification](https://tavandinh.github.io/ai-driven-dev-demos/article-01/demo/order_design.html) | [`article-01/demo`](article-01/demo) |

- `article-01/demo/`: the spec (`spec/order_spec.json`), the generator, the generated Excel / Markdown / HTML files, the embed page and the Playwright tests. See its README.
- `article-01/research/`: raw measurement data cited in the article (token counts, agent runs, Git diff demo).

## Run the tests

```bash
npm install
npx playwright install chromium
npm test
```

The demos were built with the help of Claude Code and checked by the author.
