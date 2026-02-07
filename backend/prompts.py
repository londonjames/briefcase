TEAM_EXTRACTION_PROMPT = """Given this HTML from a team/leadership page, extract every team member visible on the page.

For each person return:
- name: Full name
- title: Job title/role
- photo_url: URL of their photo/headshot (absolute URL preferred, or relative path)
- profile_url: URL to their individual profile page (absolute URL preferred, or relative path)

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
          "profile_url": "https://..."
        }
      ]
    }
  ]
}

Important:
- Extract ALL team members, not just a sample
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

Here is the structured data for every team member:

{team_data}

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
   Structured breakdown of how these people got here:
   - Education: MBA programs school-by-school with names (e.g., "Harvard Business School (8): Kent Bennett, Sarah Smith..."). What percentage have MBAs? Undergraduate institutions with names. Advanced degrees (PhDs, JDs, MDs) with names.
   - Consulting pipeline: McKinsey, BCG, Bain alumni with names and counts
   - Banking pipeline: Goldman, Morgan Stanley, etc. with names and counts
   - Tech company alumni: Google, Meta, etc. with names and counts
   - Founder/operator paths: who built companies before joining?
   - Most unusual career pivots with brief descriptions

6. **Team Composition Dashboard**
   Factual reference section with hard numbers:
   - Gender breakdown: exact counts and percentages, broken down by seniority level
   - Geographic patterns if detectable (office locations, regional backgrounds)
   - Industry specialization clusters with names
   - Tenure patterns if detectable (long-timers vs. recent hires)
   - Team size by group/function

For smaller teams (<20 people), be deeply personal and mention almost everyone by name.
For larger teams (50+), lead with statistical patterns but still name standouts.

Return ONLY valid JSON as an array of objects:
[
  {{
    "title": "Section Title",
    "content": "## Heading\\n\\nMarkdown content with **bold names**, bullet points, exact numbers..."
  }}
]

This should read like a compelling, opinionated intelligence report — not a formulaic HR summary. Surprise the reader. Make them feel like they have an unfair advantage after reading this."""
