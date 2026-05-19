# Vocabulary quiz

A 10-question, 7-seconds-per-question vocabulary quiz. Picks random questions from a pool of 5000 IELTS-style items spanning English levels 1-6.

## Local preview

Any static server works. The simplest:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

Or with Node:

```bash
npx serve .
```

Don't open `index.html` directly with `file://` — the page fetches `questions.json` at load and most browsers block `fetch` on `file://`.

## Publish to GitHub

```bash
cd vocab-quiz
git init
git add .
git commit -m "Initial commit"
gh repo create vocab-quiz --public --source=. --push
```

If you don't have the `gh` CLI: create the repo on github.com, then:

```bash
git remote add origin https://github.com/<your-username>/vocab-quiz.git
git branch -M main
git push -u origin main
```

## Deploy to Vercel

Two paths:

**Option A — dashboard (easiest, auto-deploys on every push):**

1. Go to https://vercel.com/new
2. Import the `vocab-quiz` repo
3. Framework preset: **Other** (it's just static files)
4. Click Deploy

**Option B — CLI:**

```bash
npm i -g vercel
vercel --prod
```

Either way, no build step is needed — `vercel.json` handles caching and clean URLs.

## Files

- `index.html` — the standalone game (loads `questions.json` via fetch)
- `questions.json` — 5000-question pool, minified (~650 KB)
- `vercel.json` — caching headers
