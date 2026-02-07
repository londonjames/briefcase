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
{
  "bio": "Full biography text as a single string",
  "education": [
    {
      "school": "University Name",
      "degree": "Degree type and field",
      "honors": "Any honors, distinctions, or notable details (null if none)"
    }
  ],
  "career": [
    {
      "company": "Company Name",
      "role": "Role/Position",
      "details": "Any additional details (null if none)"
    }
  ],
  "personal": ["Interest or personal detail 1", "Interest or personal detail 2"]
}

Important:
- Extract the full bio text, not a summary
- List education in chronological order if possible
- List career history (prior to current role) in reverse chronological order
- Personal details include hobbies, interests, side projects, quirks mentioned in the bio
- If a section has no data, use an empty array []"""

ANALYSIS_PROMPT = """You are analyzing a team of {team_count} people at {company}. Your job is to produce an extremely specific, opinionated, name-dropping team dossier.

Here is the structured data for every team member:

{team_data}

Produce analysis in the following sections. Each section should be a JSON object with "title" and "content" (markdown string). Be EXTREMELY specific — reference individuals BY NAME, give exact counts, percentages, and specific details. Do NOT be generic. Find non-obvious patterns.

Sections to produce:

1. **Academic Backgrounds**
   - MBA programs: school-by-school breakdown with names (e.g., "Harvard Business School (8): Kent Bennett, Sarah Smith...")
   - Undergraduate institutions: school-by-school with names
   - Advanced degrees (PhDs, JDs, MDs) with names
   - Notable academic achievements, scholarships, honors
   - What percentage have MBAs? From which tier of schools?

2. **Prior Employers & Career Paths**
   - Most common prior employers with exact counts and names
   - Consulting pipeline (McKinsey, BCG, Bain alumni with names)
   - Banking pipeline (Goldman, Morgan Stanley, etc.)
   - Tech company alumni (Google, Meta, etc.)
   - Founder/operator-turned-investor paths
   - Most unusual career pivots

3. **Deeper Insights**
   - Gender distribution: exact counts at each seniority level (Partner, Principal, VP, etc.)
   - Geographic patterns if detectable
   - Industry specialization clusters
   - Non-obvious career path patterns
   - Content creators / thought leaders (publications, podcasts, boards)
   - Founders who became investors

4. **Nuances & Quirks**
   - Personal interests that stand out (athletes, musicians, unusual hobbies)
   - Unexpected clusters (e.g., "3 people who ran marathons")
   - Multi-hyphenates (people with unusual skill combinations)
   - Published researchers or authors
   - Cultural patterns, community involvement

For smaller teams (<20 people), be more personal and mention almost everyone by name.
For larger teams (50+), focus on statistical patterns but still name standouts.

Return ONLY valid JSON as an array of objects:
[
  {{
    "title": "Section Title",
    "content": "## Heading\\n\\nMarkdown content with **bold names**, bullet points, exact numbers..."
  }}
]

Make the content rich, detailed, and genuinely insightful. This should read like a well-researched analyst report, not a generic summary."""
