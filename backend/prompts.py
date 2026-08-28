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
- List career history (prior to current role) in reverse chronological order
- Personal details include hobbies, interests, side projects, quirks mentioned in the bio
- If a section has no data, use an empty array []"""

ANALYSIS_PROMPT = """You are an intelligence analyst producing a classified-feel team dossier on {team_count} people at {company}. Your job is to find what others miss — hidden patterns, power dynamics, cultural tells, and standout individuals. Be EXTREMELY specific: reference people BY NAME, give exact counts and percentages, and surface non-obvious connections.

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
   Structured breakdown of how these people got here, built ONLY from schools and employers
   named in the bios above. Every pipeline below is a filter over that data, not a prompt to
   recall who these people are — if no bio names a consultancy, the consulting pipeline
   section says the pages don't disclose prior employers, and that is the whole answer:
   - Education: MBA programs school-by-school with names (e.g., "Harvard Business School (8): Kent Bennett, Sarah Smith..."). What percentage have MBAs? Undergraduate institutions with names. Advanced degrees (PhDs, JDs, MDs) with names.
   - Consulting pipeline: McKinsey, BCG, Bain alumni with names and counts
   - Banking pipeline: Goldman, Morgan Stanley, etc. with names and counts
   - Tech company alumni: Google, Meta, etc. with names and counts
   - Founder/operator paths: who built companies before joining?
   - Most unusual career pivots with brief descriptions

6. **Team Composition Dashboard**
   Factual reference section with hard numbers, every one of them countable from the data.
   Omit any line the data cannot support rather than estimating it:
   - Gender breakdown: exact counts and percentages, broken down by seniority level
   - Geographic patterns if detectable (office locations, regional backgrounds)
   - Industry specialization clusters with names
   - Tenure patterns if detectable (long-timers vs. recent hires)
   - Team size by group/function

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
