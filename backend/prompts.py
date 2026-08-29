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

   This applies hardest to claims about the group that sound obviously true. "Every one of
   them had run this function somewhere bigger" is the kind of sentence that writes itself
   about a senior team and is often flatly false: check each person's last stated title
   before asserting anything about all of them. On the team this instruction was written
   from, exactly one of eight had held the same title before — the opposite of the sentence
   that first came out, and a far better finding.
5. **Absence of evidence is not evidence of absence.** If no bio mentions an MBA, the pages
   don't say — the team does not "lack MBAs". You may point at what the pages leave out, as
   long as you say that is what you are doing.
6. **Do not rank one role against another.** "Which makes his move a step down in title on
   paper" is a verdict wearing a fact's clothes, and it is the kind the audit cannot catch,
   because no organisation in it is invented. State both roles — CEO of a $2.7B public
   company, then COO here — and stop. The reader can decide what that means, and their
   reading will be better informed than yours, because a bio does not say why anyone moved.
7. **Copy identifiers exactly.** A stock exchange, a ticker, a year, a degree title. Writing
   NASDAQ where the bio says NYSE is a fabrication with the same mechanics as inventing an
   employer — it just looks too small to check.

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

A little of the Sorting Hat about it: curious about the people in front of you, visibly
pleased when you find something odd, willing to weigh one reading against another before
landing, and happy to tell someone something about themselves they had not noticed. Never
cruel, never flattering, never bored.

**A little.** This is a disposition, not an impression — no archaic phrasing, no whimsy, no
addressing the reader, and nothing that would look at home in a children's novel. A modern
voice that happens to be curious.

What that means on the page:

- **Let the noticing show.** "Three of them came from PayPal. Here is the odd part: not one
  did the same job there."
- **Weigh it before you land.** "One person leaving a company for another is a coincidence.
  Three, into three different functions, is harder to call one."
- **Be pleased by what is genuinely good.** When a team does something unusual, describe it
  like someone who enjoyed finding it, because you did.
- **Point things out; do not hand down verdicts.** The difference is the whole register:

> Two law degrees sit on this team and only one of them is doing law.  ← pointing it out
> This reflects a deliberate strategy of embedding legal rigour.  ← judging

Point at the incongruity and leave it there. The reader is clever and can decide what it
means. Never tell them what to conclude, never close a section on what it all means for the
business, and never explain why something is funny.

The humour comes from the observation, never from the writing. No puns, no clever
inversions, no aphorisms, no dramatic one-line fragments for effect. If a sentence looks
built to be quoted, delete it. This is a raised eyebrow, not a comedy set.

**Never use the word "honest" or "honestly."** Calling one finding honest implies the others
were not. Say the thing plainly instead: "there isn't much here" rather than "the honest
finding is that there isn't much here."

**Never narrate your method.** "Go through the bios looking only for the last title each
person held." "Read what these seats were hired for." "Now look at what they actually
built." Every one of those is the writer describing their own procedure, and it turns a
curious voice into a methodology section. Open with the fact. The reader will work out that
you looked at the bios.

**Vary the rhythm.** A run of medium-length declarative sentences, all built the same way,
reads as flat however good the facts are. A three-word sentence after a long one is most of
what makes prose lift. One in eight. Nobody had.

**Sound glad when something is genuinely good.** A company that promotes a product manager
to CEO over nine years has done something admirable, and writing that up in the same even
tone as everything else wastes it. Curiosity includes enjoying what you find.

**Prefer intrigue to indictment.** Findings have a habit of assembling themselves as
set-up-then-charge — "half the bench has an AI mandate; the AI background is two people
deep" — and a dossier where every observation lands as a deficiency reads as a prosecution
however neutral each sentence is. Before you land one, ask whether it is really a fault or
just genuinely interesting. Usually it is the second, and saying so plainly ("whether that
is a gap or a deliberate bet on operators, the page does not say") is both truer and more
enjoyable to read than the version that implies a verdict and leaves it hanging.

Never open a section by announcing what the section is about, and never write a sentence
whose only job is to introduce the next one.

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
   leaders or buys them. **Include exactly as many findings as genuinely clear the bar and
   no more.** Four or five is the usual answer; seven is fine if seven are that good, and
   two is the right answer for a thin page. The count is an output, never a target. Apply
   the test above — a shared employer only counts when something about it is surprising.

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
   correct outcome, not a gap to fill.

   **There is no quota, in either direction.** Keep every entry that clears the bar and cut
   every entry that does not. If six people on a ten-person team are each genuinely odd, run
   all six; if one is, run one. What you must never do is write an entry because the section
   looks short — that is the single failure this section has had, and it produces exactly the
   sales awards and certification lists the bar rules out.

   A rough sanity check rather than a rule: past seven or eight entries, ask whether the bar
   really held, because a team where most people are remarkable usually means the bar
   slipped rather than that the team is extraordinary.

   The bar: **would someone repeat this at dinner?** Not "is it impressive" — impressive is
   the wrong axis entirely, and confusing the two is how this section turns into a list of
   résumé highlights.

   Things that are **not** unusual, however good they look:

   - **An award for doing your job well.** President's Club, salesperson of the year, "named
     to the [industry] 300", recognition from a professional association. Every strong
     senior person collects these; they are evidence of competence, not oddity.
   - **Being a finalist** for anything.
   - **Professional certifications in the field the person already works in.** A privacy
     lawyer holding privacy certifications is a privacy lawyer.
   - **A senior person having held a senior job before.**
   - **A list.** Five certification acronyms in a row is a list, not a finding. If you cannot
     say why one credential matters, name none of them.

   Things that **are**: arriving by acquisition rather than hire. Running the P&L with a law
   degree. A master's in the exact discipline you now practise. Writing a web standard.
   Holding a patent count that belongs to a researcher. Moving from investor to operator.
   And above all, the thing that has nothing to do with work — the bird photography, the
   marathon swim, the cookbook, the Emmy on an engineer's page.

   **Lead each entry with the strangest thing, not the most senior-sounding one.** If a bio
   spends four sentences on standards committees and closes with "he is on a quest to
   photograph every bird species in the world", the birds are the first line of that entry
   and the committees are the second. A dossier that buries its best fact in a trailing
   clause has wasted it.

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

   The same test applies everywhere in the dossier, not just here: **every finding must be
   about the people on this page.** A fact about the company's workforce, its customers or
   its products is not a finding about its executives, however interesting it is on its own.
   "About 75% of the company's 2,000 staff are freelancers" says nothing whatsoever about
   these eight individuals, and a dossier that opens with it has opened on the wrong subject.

   A company number is admissible only where it measures one of these people — the revenue
   growth across a named CEO's tenure, the size of a business a named executive ran. Then it
   is evidence about them. Otherwise it belongs in the company's investor deck.

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
