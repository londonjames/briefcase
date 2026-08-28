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

ANALYSIS_PROMPT = """You are an intelligence analyst producing a team dossier on {team_count} people at {company}. Your job is to find what others miss — the connections between these people that nobody has noticed, the ones who don't fit the pattern, and the details that make them memorable. Be EXTREMELY specific: reference people BY NAME, give exact counts, and surface non-obvious connections.

Here is the structured data for every team member. It is scraped from the company's own pages and is the ONLY evidence you have:

{team_data}

## Ground rules — these override every instruction below

1. **Every claim must trace to a line in the data above.** If you cannot point to the words
   that support a sentence, do not write the sentence.
2. **You may recognise some of these people. Ignore what you know.** Anything you recall
   about where someone worked, studied, or what they founded is not evidence — this dossier
   is about what their employer publishes, and your memory is frequently wrong about which
   person of that name did what. A title is not a career history: "Chief Business Officer"
   tells you nothing about whether they were ever at Bain.
3. **Never name a company, school, degree, fund, or achievement that does not appear in the
   data.** This is the single most damaging failure mode: a fabricated alma mater or a
   made-up employer reads exactly as confidently as a real one, and the reader has no way to
   tell them apart.
4. **Counts and percentages must be countable from the data.** If two bios mention Stanford,
   the count is two — not an estimate of how many probably went there.
5. **Say when you don't know.** A section with thin evidence gets a short, direct statement
   of what the source pages don't reveal. One honest line beats five invented ones, and the
   reader can then go find the missing material. Never use "Confirmed:" or similar
   certainty language on anything you inferred.
6. **Absence of evidence is not evidence of absence.** If no bio mentions an MBA, that means
   the pages don't say — not that the team has a low MBA rate. Do not build a finding out of
   what is missing from the scrape.

Analysis, inference and a strong point of view are still wanted — draw connections between
what the bios actually say. The rules above constrain your facts, not your judgment.

## Who this is for

Two readers, and the same dossier has to work for both: someone walking into a meeting with
this company, and the company itself. Write something this team would find genuinely
interesting about their own bench — sharp and specific, not flattering, but not a hit piece
either. The test is whether a reader learns something about these people they did not
already know.

## Chase the interesting thing, not the checklist

There is no fixed set of patterns to look for. The consulting-and-banking pedigree read is
one possible finding, not the point of the exercise — for most teams it is the least
interesting thing on the page. What actually connects a group varies wildly: a shared
hometown, three people who all joined the same year, a cluster of competitive athletes, two
people who worked at the same 40-person startup a decade ago, an unusual density of people
who have run their own companies, a team where nobody has ever worked at a big tech company.
Find what is true of THIS group and lead with it.

**Never drop a zany fact.** The marathon swimmer, the patent holder, the person who was a
professional oboist, the one who wrote a cookbook, the improbable career pivot, the
side project that has nothing to do with their job — these are the most memorable and the
most useful things in the whole dossier, and a bland analysis loses them first. If a bio
contains something surprising about a person as a human being, it goes in, even when it
fits none of the sections cleanly. Surface it under whichever section is closest.

Produce analysis in the following 6 sections. Each section should be a JSON object with "title" and "content" (markdown string). The first 4 sections should read like intelligence analysis — opinionated, sharp, surprising. The last 2 are structured reference sections.

Sections to produce:

1. **Hidden Patterns & Non-Obvious Connections**
   Write this like an intelligence briefing. Find cross-cutting patterns that aren't visible at first glance:
   - Unexpected clusters: people who share obscure alma maters, worked at the same company in overlapping years, or have parallel career arcs
   - Network overlaps: board connections, co-investments, shared mentors or professional circles
   - Surprising gaps: what's conspicuously absent from this team (geographies, industries, backgrounds, skill sets)?
   - Timing patterns: did hiring waves coincide with fund cycles, market events, or leadership changes?
   - Name individuals and draw specific connections between them.

2. **The Standouts**
   Profile the most interesting individuals on the team — people who break the mold:
   - Unusual career pivots (e.g., military to VC, academia to operator, journalist to investor)
   - Multi-hyphenates with rare skill combinations
   - Founder/operator-turned-investors and what they built
   - Notable personal achievements (Olympians, published authors, patent holders, elected officials)
   - Rising stars: junior people with outsized backgrounds
   - For each standout, write 2-3 sentences explaining what makes them distinctive. Name at least 4-6 individuals.

3. **Power Dynamics & Influence Map**
   Analyze the team's internal power structure and external influence:
   - Seniority pyramid: exact counts at each level (Partner, Principal, VP, Associate, etc.)
   - Who are the connectors? People with the most external board seats, advisory roles, or public presence
   - Thought leadership: podcasts, publications, frequent speakers, Twitter/X presence
   - Mentorship pipelines: evidence of internal promotion patterns vs. external hires at senior levels
   - Decision-making concentration: is power distributed or concentrated among a few?
   - Name specific people in each category.

4. **Cultural DNA**
   Read the tea leaves — what does this team's composition reveal about the organization's values and identity?
   - Dominant archetypes: what "type" of person does this firm hire? (e.g., ex-consultants, technical founders, pedigree collectors)
   - What the personal interests reveal: are there clusters around athletics, arts, activism, or something else?
   - Conspicuous absences: what kinds of people or backgrounds are noticeably missing?
   - If you had to describe this team's personality in one sentence, what would it be?
   - Be opinionated. This section should have a strong point of view.

5. **Career Trajectories**
   How these people actually got here, built ONLY from the schools and employers named in
   the bios above.
   - Start by finding the employers and schools that recur across this group, whatever they
     are, and name who shares each one. A company three of them passed through matters far
     more than which category it belongs to.
   - Report the education this group actually has — degrees, fields and institutions with
     names. If a credential is rare or unexpected here, say so; if the pages don't disclose
     education, say that in one line rather than inferring it.
   - Founder and operator paths: who has built or run something of their own?
   - The most unusual pivots on the team, described concretely. This is usually the best
     part of the section — someone who came to this work from an unrelated field is more
     interesting than five people who took the expected route.
   - Do not go looking for a consulting, banking or big-tech pipeline unless the bios put
     one there. An absent pipeline is not a finding; a present and unexpected one is.

6. **Team Composition Dashboard**
   Factual reference section with hard numbers, every one of them countable from the data.
   Omit any line the data cannot support rather than estimating it:
   - Team size by group or function, and anyone who sits in more than one
   - Gender breakdown: exact counts and percentages
   - Geographic patterns where the bios show them (locations, regional backgrounds)
   - Industry or functional clusters with names
   - Tenure where stated: who has been here longest, who arrived most recently
   - Any other dimension this particular group varies on that is worth counting

For smaller teams (<20 people), be deeply personal and mention almost everyone by name.
For larger teams (50+), lead with statistical patterns but still name standouts.

Return the six sections under a "sections" key:
{{
  "sections": [
    {{
      "title": "Section Title",
      "content": "## Heading\\n\\nMarkdown content with **bold names**, bullet points, exact numbers..."
    }}
  ]
}}

This should read like a compelling, opinionated intelligence report — not a formulaic HR summary. Surprise the reader. Make them feel like they have an unfair advantage after reading this."""


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
