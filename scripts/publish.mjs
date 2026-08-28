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
  const keys = (await redis(["KEYS", "briefcase:*"])) ?? [];
  console.log(`${keys.length} stored:`);
  for (const k of keys.slice(0, 40)) console.log(`  ${SITE}/${k.replace("briefcase:", "")}`);
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
if (!Array.isArray(dossier.insights) || dossier.insights.length < 3) {
  console.error(`Dossier needs at least 3 insight sections (found ${dossier.insights?.length ?? 0}).`);
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
