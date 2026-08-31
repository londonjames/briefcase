---
name: briefcase
description: Build a team dossier on a company — scrape their team page, profile every person, and produce a sharp intelligence-style analysis. Runs locally on the subscription (no API cost) and publishes to briefcase.jamesraybould.me. Use when James types /briefcase, gives a company team or leadership page URL, or asks for a dossier, team analysis or rundown on a company's people before a meeting.
---

<!-- portable copy: lives in this repo so cloud sessions get it -->
`$REPO` = this repository's root: the working directory in a cloud session, `/Users/jamesraybould/Documents/briefcase` locally.

# Briefcase, in the terminal

Same dossier as briefcase.jamesraybould.me. The difference is where the work happens: **you
do the extraction and analysis here**, on James's subscription, so it costs no API tokens
and never wakes the Railway backend. Only the publish step touches the network.

## Step 1 — Load the prompts

Read all three and follow them exactly:

```
$REPO/backend/prompts.py
```

- `TEAM_EXTRACTION_PROMPT` — how to pull people and groups off a team page
- `PROFILE_EXTRACTION_PROMPT` — how to structure one person's bio, education, career, personal
- `ANALYSIS_PROMPT` — the six sections, and the register they are written in

The analysis prompt is the product. It asks for an intelligence briefing: opinionated,
surprising, people named individually, exact counts and percentages, non-obvious
connections. A formulaic HR summary is the failure mode it exists to prevent.

## Step 2 — Get the team

James gives you a team or leadership page URL. Fetch it (WebFetch, or `curl -s` when you
need the raw HTML) and extract every person per `TEAM_EXTRACTION_PROMPT`: company name,
groups, and for each member `name`, `title`, `photo_url`, `profile_url`, `bio`.

**Capture the bio off the team page itself.** Leadership pages routinely carry a full bio
per person inline, in an accordion, or in a modal, and link to no separate profile page. If
you take only names and titles from a page like that, everything downstream has nothing to
stand on — and an analysis with nothing to stand on invents. Copy the bio text verbatim;
never write one from what you know about the person.

Photos matter — the site renders them through its image proxy — so capture `photo_url`
whenever the page exposes one, as an absolute URL.

**The operating team only.** Skip the board of directors, advisory boards and investors.
They don't run the company, and mixing them in dilutes everything — a paragraph about "who
this company puts in charge" that reaches for a director's CEO history is describing two
different populations at once. A founder-CEO who also sits on the board counts as
operating; a director with no executive role does not. Only when a page lists nothing but a
board is the board the team.

**Dedupe anyone listed twice.** One entry, in the group they appear in first, titles joined
(`President and CEO · Chief Product Officer`), bios concatenated, career and education
merged. Two cards for one person inflates every count they appear in.

## Step 3 — Profile each person

Where members have their own profile pages, fetch them and extract per
`PROFILE_EXTRACTION_PROMPT`: `bio` (full text, not a summary), `education[]`, `career[]`,
`personal[]`. Merge those fields into each member object.

Where they don't, structure the inline bio you captured in Step 2 the same way — that text
is the only evidence this dossier will ever have about them, so it gets the same treatment
as a profile page rather than being left as loose prose.

Two things are easy to lose here and both matter: prior employers named mid-paragraph
("she started her career in the strategy group at McKinsey & Company" sits inside a
sentence about her current job), and `personal[]` — the marathon, the patent, the band, the
cookbook. The personal details are the most memorable part of the finished dossier and
nothing downstream can recover one you drop.

Fetch in parallel batches rather than one at a time. On a large team, if fetching every
profile is impractical, do the senior people and anyone who looks unusual, and tell James
which ones you skipped — a silently partial dossier is worse than a stated one.

## Step 4 — Analyse

Produce the sections in `ANALYSIS_PROMPT`, in order:

1. **The DNA of This Team** — what is true across the group: connections, how the bench was
   assembled, what it is heavy and thin on. At most four findings. Because it comes first,
   give each person a few words of identification on first mention.
2. **What's Unusual** — the improbable pivots, the unexpected degrees, the patents and
   Emmys, the person who arrived by a route nobody else took. **Not a roll-call**, and no
   quota either way: keep every entry that clears the bar, cut every one that doesn't. Four
   or five is the usual answer, seven is fine if seven are that good, one is fine if only
   one is. Anyone whose bio is a clean conventional record of good jobs isn't mentioned. Lopsided is correct —
   four surprising things about one person, nothing about the chalk executive beside them.

   The bar is **would someone repeat this at dinner**, not "is it impressive". An award for
   doing your job well — President's Club, an industry recognition list, certifications in
   your own field, being a *finalist* for something — is competence, not oddity. And lead
   each entry with the strangest thing: if a bio closes on a quest to photograph every bird
   species in the world, that is the first line, not a trailing clause after the standards
   committees.
3. **The Numbers** — **only above 15 people.** On a smaller team the reader has just met
   everyone by name and a tally hands their own reading back to them. Two sections is the
   right answer for most teams.

Each is `{ "title": "…", "content": "markdown…" }`, with a bold sub-heading per finding.

**Every finding must be about the people on this page.** A fact about the company's
workforce, customers or products is not a finding about its executives, however good it is —
"75% of the company's 2,000 staff are freelancers" says nothing about the eight individuals
the dossier is on. A company number counts only where it measures one of these people, like
revenue growth across a named CEO's tenure.

**The DNA section states the pattern; it does not spend the specifics.** "Every award on
this page belongs to the two founders" makes the point — naming the Emmy there burns what
the second section needs, and the reader meets it twice. Nothing named in the first section
is named again in the second.

The two sections divide cleanly and that division is what keeps the dossier short: **a fact
about the group belongs in the DNA section; a fact about one person belongs in The People.**
Earlier versions split the group-level thinking across two sections and then repeated
themselves trying to fill both.

`ANALYSIS_PROMPT` asks for these under a `"sections"` key — that wrapper exists only so the
backend's JSON schema has an object at the root. Here there is no schema, so hand
`publish.mjs` the plain four-item array as `insights`.

Three things decide whether this is any good, and all are in the prompt: **a shared employer
is not a hidden pattern**, **every fact appears exactly once in the whole dossier**, and the
register has **a little of the Sorting Hat** in it — curious about these people, pleased to
find something odd, weighing a reading before landing on it. A disposition, not an
impression: no archaic phrasing, no whimsy, no costume. Two things kill it every time —
narrating your own method ("go through the bios and you'll see..."), and building every
finding as set-up-then-charge until the whole dossier reads as a prosecution. Open with the
fact, vary the sentence lengths, and sound glad when something is genuinely good. It points things out rather than handing down
verdicts, and the humour comes from the observation rather than the writing.
Three people who worked at Google is something the reader can see in ten seconds. It earns a
paragraph only when something about it is surprising. And a career restated in three
sections is what made earlier versions a chore to read.

## Step 4b — Audit your own analysis before publishing

Go back through the six sections and, for every organisation, school, degree and award you
attributed to a named person, find the words in the bios that support it. Not a memory that
it is true — the actual text.

Anything you cannot trace comes out. This is not a formality: the failure this whole
pipeline is shaped around is a dossier that read beautifully and put two executives at Bain
and a third at TripAdvisor, none of which appeared anywhere in the source. You will
recognise some of these people, and what you recall will be confidently wrong about which
person of that name did what.

Tell James what you removed, if anything.

## Step 5 — Publish

```bash
cat > /tmp/briefcase.json <<'JSON'
{
  "company": "…",
  "source_url": "…",
  "groups":   [{ "name": "…", "members": [ … ] }],
  "insights": [ …6 sections… ]
}
JSON
node $REPO/scripts/publish.mjs --file /tmp/briefcase.json
```

It fills in `team_count`, `dossier_id` and the slug (`<company>/<dDMonthYYYY>`, the same
derivation the Flask backend uses), then prints the URL. It refuses a dossier missing
groups, members, or any of the six sections rather than putting a half-built page on a
public address.

Give James the URL. The page has Team and Insights tabs and an Export to Notion button.

## Listing what has been run

When James asks what dossiers exist, what he has run before, or whether a company has one
already:

```bash
set -a && source ~/pro/.env.local 2>/dev/null; set +a   # local only; in a cloud session these are already env vars
node scripts/publish.mjs --list
```

Newest first, with the company, headcount, how many of those people actually have a bio,
the section count and the URL. This is the private archive — reading it needs this machine
and the Upstash credentials, which is the access control. There is no public index page,
and the dossier URLs themselves are unlisted rather than secret.

Two flags in that output are worth reading out to James rather than passing over:

- `[EMPTY]` — a dossier with no people at all. The scrape failed and the page is a shell.
- `[thin]` — people were found but most have no bio, which is the condition that produced
  fabricated careers before the grounding rules existed. Treat its analysis as suspect.

A dossier showing **6 sections** predates the current format and is worth regenerating; the
current shape is two, or three above fifteen people.

`--show <company>/<date>` prints one dossier as JSON, which is how to inspect or edit an
existing one before republishing it to the same slug.

## Notes

- Credentials come from `~/pro/.env.local` locally, or the cloud environment's variables in a cloud session — Briefcase shares Profiler's
  Upstash instance under a `briefcase:` prefix. If that file is missing:
  `cd ~/pro && npx vercel env pull .env.local --environment production`
- There is a separate `team-dossier` skill that targets **Notion**. This one targets the
  Briefcase web app. Different outputs — do not confuse them.

## What breaks this

- **Writing an HR summary.** The prompt asks for an intelligence briefing with a point of
  view. Blandness is the failure.
- **Vagueness.** "Several people have consulting backgrounds" is worthless. Name them and
  count them.
- **Inventing connections.** Every pattern must be traceable to something on the pages you
  actually read.
- **Reaching into your own memory for a career.** The most damaging failure this skill has
  had. A fabricated employer reads exactly as confidently as a real one and the reader
  cannot tell them apart. If the bio doesn't say it, it doesn't go in.
- **Losing the zany facts.** The oboist, the ultramarathoner, the patent. They are the most
  memorable thing in the dossier and blandness eats them first.
- **Two cards for one person.** Dedupe across groups, or every count is wrong.
- **Dropping `photo_url`.** The cards look broken without photos.
- **Silently skipping people.** Say who you skipped and why.
