#!/usr/bin/env node
/**
 * Terminal → web bridge for Briefcase.
 *
 * The scraping, extraction and analysis all happen inside Claude Code, on the
 * subscription, costing no API tokens — the skill reads `backend/prompts.py` and does the
 * work itself rather than waking the Railway backend. This script is the only part that
 * touches the network: it writes the finished dossier into the same `briefcase:<slug>` key
 * the React app reads, so it is live at briefcase.jamesraybould.me/<company>/<date>.
 *
 * Credentials come from Profiler's .env.local — Briefcase has no local env file and
 * deliberately shares Profiler's Upstash instance, namespaced by the `briefcase:` prefix.
 *
 * Usage:
 *   node publish.mjs --file <dossier.json>   → writes it, prints the URL
 *   node publish.mjs --show <company>/<date> → print a stored dossier
 *   node publish.mjs --list                  → recent dossiers
 */

import fs from "fs";
import path from "path";

const SITE = "https://briefcase.jamesraybould.me";
const ENV_FILE = "/Users/jamesraybould/pro/.env.local";

if (!fs.existsSync(ENV_FILE)) {
  console.error(`Missing ${ENV_FILE} — run: cd ~/pro && npx vercel env pull .env.local --environment production`);
  process.exit(1);
}
for (const line of fs.readFileSync(ENV_FILE, "utf8").split("\n")) {
  const m = line.match(/^([A-Z_]+)="?([^"]*)"?$/);
  if (m) process.env[m[1]] ??= m[2];
}

const URL_ = process.env.KV_REST_API_URL;
const TOKEN = process.env.KV_REST_API_TOKEN;
if (!URL_ || !TOKEN) {
  console.error("No Upstash credentials found.");
  process.exit(1);
}

async function redis(args) {
  const res = await fetch(URL_, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(args.map(String)),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`redis ${res.status}: ${await res.text()}`);
  const { result, error } = await res.json();
  if (error) throw new Error(`redis: ${error}`);
  return result;
}

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

const args = process.argv.slice(2);

if (args[0] === "--show") {
  const raw = await redis(["GET", `briefcase:${args[1]}`]);
  if (!raw) {
    console.error("No dossier at that slug.");
    process.exit(1);
  }
  console.log(JSON.stringify(typeof raw === "string" ? JSON.parse(raw) : raw, null, 2));
  process.exit(0);
}

if (args[0] === "--list") {
  // The private archive. Reading it needs this machine and the Upstash
  // credentials, so the listing itself is the access control.
  const keys = (await redis(["KEYS", "briefcase:*"])) ?? [];
  const rows = [];
  for (const k of keys) {
    const slug = k.replace("briefcase:", "");
    let d = {};
    try {
      const raw = await redis(["GET", k]);
      d = typeof raw === "string" ? JSON.parse(raw) : raw ?? {};
    } catch {
      // a corrupted entry still deserves its slug listed
    }
    const members = (d.groups ?? []).flatMap((g) => g.members ?? []);
    const [, dateSlug] = slug.split("/");
    const m = /^(\d{1,2})([A-Za-z]+)(\d{4})$/.exec(dateSlug ?? "");
    const when = m ? new Date(`${m[2]} ${m[1]}, ${m[3]}`) : new Date(0);
    rows.push({
      slug,
      when,
      date: m ? `${m[1]} ${m[2].slice(0, 3)} ${m[3]}` : dateSlug ?? "?",
      company: d.company ?? slug.split("/")[0],
      people: members.length,
      bios: members.filter((x) => x.bio && x.bio.length > 40).length,
      sections: (d.insights ?? []).length,
    });
  }

  rows.sort((a, b) => b.when - a.when);
  console.log(`${rows.length} dossiers, newest first\n`);
  for (const r of rows) {
    const evidence = r.people ? `${r.bios}/${r.people} bios` : "no people";
    const flag = r.people === 0 ? "  [EMPTY]" : r.bios < r.people ? "  [thin]" : "";
    console.log(
      `  ${r.date.padEnd(12)} ${String(r.company).slice(0, 26).padEnd(28)} ` +
        `${String(r.people).padStart(3)} people  ${evidence.padEnd(14)} ` +
        `${r.sections} sections${flag}`
    );
    console.log(`  ${" ".repeat(12)} ${SITE}/${r.slug}`);
  }
  process.exit(0);
}

if (args[0] !== "--file" || !args[1]) {
  console.error("Usage: publish.mjs --file <dossier.json> | --show <slug> | --list");
  process.exit(1);
}

let dossier;
try {
  dossier = JSON.parse(fs.readFileSync(args[1], "utf8"));
} catch (err) {
  console.error(`Could not read dossier JSON: ${err.message}`);
  process.exit(1);
}

// A dossier that reaches a public URL half-built is worse than one that failed loudly.
if (!dossier.company) {
  console.error("Dossier must include company.");
  process.exit(1);
}
if (!Array.isArray(dossier.groups) || !dossier.groups.length) {
  console.error("Dossier must include groups: [{ name, members: [...] }].");
  process.exit(1);
}
if (!Array.isArray(dossier.insights) || dossier.insights.length < 2) {
  console.error(`Dossier needs at least 2 insight sections (found ${dossier.insights?.length ?? 0}).`);
  process.exit(1);
}
for (const s of dossier.insights) {
  if (!s.title || !s.content) {
    console.error("Each insight section needs { title, content }.");
    process.exit(1);
  }
}

const members = dossier.groups.flatMap((g) => g.members ?? []);
if (!members.length) {
  console.error("No members in any group.");
  process.exit(1);
}
dossier.team_count ??= members.length;
dossier.dossier_id ??= `cli-${Date.now().toString(36)}`;

// Same slug derivation as backend/app.py, so terminal and web never disagree.
const now = new Date();
const companySlug = dossier.company.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const dateSlug = `${now.getDate()}${MONTHS[now.getMonth()]}${now.getFullYear()}`;
const slug = dossier.slug ?? `${companySlug}/${dateSlug}`;
dossier.slug = slug;

await redis(["SET", `briefcase:${slug}`, JSON.stringify(dossier)]);

console.log(slug);
console.log(`${SITE}/${slug}`);
console.log(`${dossier.team_count} people · ${dossier.groups.length} group(s) · ${dossier.insights.length} sections`);
