TEAM_EXTRACTION_PROMPT = """Given this HTML from a team/leadership page, extract every team member visible on the page.

For each person return:
- name: Full name
- title: Job title/role
- photo_url: URL of their photo/headshot (absolute URL preferred, or relative path)
- profile_url: URL to their individual profile page (absolute URL preferred, or relative path)
- bio: If the page shows biography text for this person (inline, in an accordion, or in a
  modal), return it in full, verbatim. Many leadership pages carry the whole bio here and
  have no separate profile page — that text is the only evidence the dossier will ever get,
  so do not summarise it and do not skip it. Use null only when the page truly has none.

Extract the OPERATING TEAM ONLY. Skip the board of directors, advisory boards, investors
and trustees entirely — they do not run the company day to day, and a dossier about the
people who do gets diluted the moment they are mixed in. A founder-CEO who also sits on the
board is part of the operating team; a director who holds no executive role is not. The one
exception is a page that lists nothing but a board — then the board is the team.

Identify any team groupings visible in the HTML (sections, tabs, categories, departments).
If there are no clear groupings, put everyone in a single group called "Team".

Return ONLY valid JSON in this exact format:
{
  "company": "Company Name (infer from page content/title/meta)",
  "groups": [
    {
      "name": "Group Name",
      "members": [
        {
          "name": "Person Name",
          "title": "Their Title",
          "photo_url": "https://...",
          "profile_url": "https://...",
          "bio": "Full biography text if the page shows one, else null"
        }
      ]
    }
  ]
}

Important:
- Extract ALL team members, not just a sample
- Never write a bio from your own knowledge of the person. Copy what the page says or return null
- If photo or profile URLs are relative, keep them as-is (the caller will resolve them)
- If no photo or profile URL exists, use null
- Infer the company name from the page content, meta tags, or title"""

PROFILE_EXTRACTION_PROMPT = """Extract structured information from this person's profile page HTML.

Person: {name} — {title}

Return ONLY valid JSON in this exact format:
{{
  "bio": "Full biography text as a single string",
  "education": [
    {{
      "school": "University Name",
      "degree": "Degree type and field",
      "honors": "Any honors, distinctions, or notable details (null if none)"
    }}
  ],
  "career": [
    {{
      "company": "Company Name",
      "role": "Role/Position",
      "details": "Any additional details (null if none)"
    }}
  ],
  "personal": ["Interest or personal detail 1", "Interest or personal detail 2"]
}}

Important:
- Extract the full bio text, not a summary
- List education in chronological order if possible
- career: EVERY organisation the text names this person as having worked for, including the
  current one. Prior employers are often a single clause buried inside a paragraph about
  their current job ("She started her career in the strategy group at McKinsey & Company") —
  read the whole bio for them rather than only the sentences that announce a job change. A
  bio that names past employers must never come back with an empty career list.
- List career history in reverse chronological order where the text makes the order clear
- personal: anything about them as a human rather than an employee — hobbies, sports,
  bands, books written, patents, volunteering, unusual hometowns, languages, side projects,
  quirks, awards outside their job. Capture ALL of them, in the bio's own words where you
  can. These details are the most memorable part of the finished dossier and nothing
  downstream can recover one you leave out.
- If a section has no data, use an empty array []"""

ANALYSIS_PROMPT = """You are writing a dossier on the {team_count} people who run {company}. Find what a reader would not get by skimming the same page themselves.

Here is the structured data for every person. It is scraped from the company's own pages and is the ONLY evidence you have:

{team_data}

## Ground rules — these override every instruction below

1. **Every claim must trace to a line in the data above.** If you cannot point to the words
   that support a sentence, do not write the sentence.
2. **You may recognise some of these people. Ignore what you know.** Anything you recall
   about where someone worked, studied, or what they founded is not evidence — this dossier
   is about what their employer publishes, and your memory is frequently wrong about which
   person of that name did what. A title is not a career history.
3. **Never name a company, school, degree, fund, or achievement that does not appear in the
   data.** A fabricated alma mater reads exactly as confidently as a real one, and the
   reader has no way to tell them apart.
4. **Counts must be countable from the data.** If two bios mention Stanford, the count is
   two — not an estimate of how many probably went there.
5. **Absence of evidence is not evidence of absence.** If no bio mentions an MBA, the pages
   don't say — the team does not "lack MBAs". You may point at what the pages leave out, as
   long as you say that is what you are doing.

These constrain your facts, not your judgment. Opinions are wanted. Hedging every sentence
is its own failure.

## Who this is for

Two readers, and the same dossier has to work for both: someone walking into a meeting with
this company, and the company itself. Write something this team would find genuinely
interesting about their own bench.

## What counts as a finding

**A shared employer is not a hidden pattern.** Three people who worked at Google is a fact
the reader can see for themselves in ten seconds. It clears the bar only when something
about it is surprising — they overlapped on the same small team, they all left in the same
year, or the company has nothing to do with this one.

Test every paragraph: *does the reader learn something they could not have got by reading
the source page?* If not, cut it. A shorter dossier that earns every paragraph beats a
complete one that doesn't.

Two shapes reliably clear the bar. The first is **an argument about the group** — named
evidence, then a judgment:

> Hayden Brown is the one clear case of internal ascension: she joined in 2011 as a product
> manager and worked up through the marketplace business, chief product officer and chief
> marketing officer before becoming CEO in 2020. Every other executive arrived from outside,
> several via acquisition rather than hire. That makes her start date the longest tenure on
> the page by a wide margin, and the only evidence of a pipeline growing its own CEO.

The second is **a person who does not fit the group at all** — the improbable pivot, the
Emmy on the chip designer's bio, the credential nobody else has.

## Say it once

A fact belongs to exactly one paragraph in the entire dossier. If someone's PayPal history
carries a finding in the first section, it does not reappear in the third. Repetition is the
single biggest thing that made earlier versions of this dossier tedious.

## Voice

Dry, observational, faintly amused. You are **pointing things out, not handing down
verdicts** — the difference is the whole register:

> Two law degrees sit on this team and only one of them is doing law.  ← pointing it out
> This reflects a deliberate strategy of embedding legal rigour in the operating core.  ← judging

Point at the incongruity and leave it there. The reader is clever and can decide what it
means. Never tell them what to conclude, never close a section with what it all means for
the business, and never explain why something is funny.

The humour comes from the observation itself, never from the writing. No puns, no clever
inversions, no aphorisms, no dramatic one-line fragments for effect. If a sentence looks
like it was built to be quoted, delete it. This is a raised eyebrow, not a comedy set.

Short declarative sentences. Name the thing. Never open a section by announcing what the
section is about, and never write a sentence whose only job is to introduce the next one.

**Never drop a zany fact.** The marathon swimmer, the patent holder, the professional
oboist, the cookbook, the improbable pivot. These are the most memorable things in the whole
dossier and a dry draft loses them first. If a bio says something surprising about a person
as a human being, it goes in.

## The sections

Two sections, plus a third only on a large team. Each is a JSON object with "title" and
"content" (markdown), and each finding inside gets a bold sub-heading.

1. **The DNA of This Team**
   Everything true across the group rather than about one person: what connects them, how
   the bench was assembled, what it is heavy on and thin on, whether the company grows its
   leaders or buys them. **At most four findings.** Apply the bar above — a shared employer
   only counts when something about it is surprising.

   This section comes first, so the reader meets these names before they know who anyone is.
   Give each person a few words of identification the first time they appear — "**Erica
   Gessert**, the CFO" — and never more than that; the full story is the next section's job.

   **State the pattern; do not spend the specifics.** This is the difference between a
   dossier that reads once and one that repeats itself. "Every award on this page belongs to
   the two founders" makes the point completely — naming the Emmy and the Hall of Fame
   induction here burns the material the next section needs, and the reader then meets both
   facts twice. Make the group-level observation with the fewest particulars that carry it,
   and leave the good detail where it lands hardest.

   Do not close on what it all means for the company's prospects. That is the reader's job
   and they did not ask you.

2. **What's Unusual**
   The things worth remembering about particular people — the improbable pivot, the degree
   in something nobody expected, the patent, the Emmy, the person who arrived by a route
   nobody else took.

   **This is not a roll-call.** Do not work through the team giving everyone a paragraph.
   Someone whose bio holds nothing unusual is simply not mentioned here, and that is the
   correct outcome, not a gap to fill. A ten-person team might yield two entries; a
   six-person team might yield five. Let the material decide.

   The bar is the same as everywhere else: would the reader be mildly surprised? A senior
   person having held a senior job before is not unusual. Being acquired rather than hired
   is. Running the P&L with a law degree is. A master's in the exact discipline you now
   practise is. If a bio is a clean, conventional record of good jobs, say nothing about it
   — that person is already covered by the DNA section.

   **Coverage is deliberately lopsided.** If one person's bio holds four surprising things —
   an acquisition, a patent count, an unexpected degree, an award from another field — give
   them all four. If the person in the next seat is chalk, a conventional record of sensible
   jobs, give them nothing. Never even it out to be fair; evening it out is how a section of
   real oddities turns back into a roster.

   Skip the surname-only recap of a career the first section already used as evidence.

3. **The Numbers** — **only when there are more than 15 people. Below that, omit it entirely
   and return two sections.** On a small team the reader has just met everyone by name, and
   a tally hands their own reading back to them.

   When it does apply: bullets only, no paragraphs, no analysis, nothing repeated from
   above. Counts worth checking — team size, gender split, arrival dates where stated,
   repeated employers, education clusters, and any dimension this group actually varies on.

   Never include a tally of "stated experience" built from bio boilerplate — every executive
   page says "more than 20 years", so counting who said it measures nothing. Never include
   company-level figures as a tally — revenue, headcount, countries served — since this is a
   dossier about people and those numbers belong to the company's investor deck.

   A company fact is different from a company figure, and the difference is worth knowing: a
   number that reveals how these people actually work is fair game anywhere in the dossier.
   "Roughly 2,000 employees and about 75% of them are freelancers hired through the company's
   own marketplace" is not a vanity metric — it is the most revealing sentence on the page.
   Do not discard those while stripping out the revenue line.

Return the sections under a "sections" key:
{{
  "sections": [
    {{
      "title": "Section Title",
      "content": "**A finding**\\n\\nMarkdown with **bold names**, exact numbers..."
    }}
  ]
}}"""


GROUNDING_CHECK_PROMPT = """You are auditing a team dossier for fabricated facts.

Below are the SOURCE bios the dossier was built from, then the ANALYSIS written about them.

List every organisation, school, degree, award and job title that the ANALYSIS attributes to
a named person. For each one, quote the words from SOURCE that support it.

- `quote` must be copied verbatim from SOURCE — character for character, not paraphrased,
  and one contiguous span rather than fragments stitched together with an ellipsis. It is
  checked against SOURCE by string match, so an approximate quote counts as a failure.
- Keep the quote SHORT: the fewest words that prove the claim, at most about twelve. A long
  quote is not a stronger one, and the check only needs the span that carries the fact.
- If nothing in SOURCE supports the claim, set `quote` to null. That is the finding this
  audit exists to produce, so do not go looking for a loose match to make one fit.
- List each distinct claim ONCE, even when several sections repeat it.
- A claim the analysis states as absent ("no bio names Bain") is not an attribution. Skip it.
- Do not use your own knowledge of these people. A claim you happen to know is true is still
  unsupported if SOURCE does not say it.

SOURCE:
{source}"""


GROUNDING_CHECK_ANALYSIS = """ANALYSIS:
{analysis}"""
