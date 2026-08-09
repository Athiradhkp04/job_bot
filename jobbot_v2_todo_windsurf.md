# Job Bot v2 — Verified To-Do List for Windsurf

Everything below was checked against real, live sources this session —
nothing here is guessed. Where something is unconfirmed, it's labeled
"NOT VERIFIED" explicitly rather than assumed to work.

---

## PRIORITY 1 — Integrate FresherGo (biggest find, build this first)

`freshergo.com` is a real job board built specifically for entry-level
roles, confirmed scrapeable with plain HTTP requests — **no JavaScript
rendering needed**, no headless browser required. Verified by directly
fetching two different pages and getting clean structured content back
both times.

**What it is:** every listing is synced from official Greenhouse, Lever,
or Ashby company career pages — not a random aggregator. This directly
satisfies the "credible, known companies only" requirement, per the
platform's own stated policy, not just our assumption.

**Scale confirmed:** 2,223 verified roles from 1,097 companies, updated
daily, fresher/entry-level only (0-2 years experience), senior roles
explicitly filtered out by the platform itself.

**Real URLs confirmed working (fetch-tested):**
- `freshergo.com/jobs/role/{role-slug}` — e.g. `data-analyst`,
  `ai-engineer`, `backend-developer`, `frontend-developer`,
  `fullstack-developer`, `product-manager`
- `freshergo.com/jobs/city/{city-slug}` — confirmed: `bangalore`,
  `chennai`, `delhi-ncr`, `hyderabad`, `mumbai`. **Check if a Kerala/
  Kochi/Trivandrum city page exists — not yet checked.**
- `freshergo.com/internships`
- `freshergo.com/company/{company-slug}` — per-company pull
- `freshergo.com/search` — supports query params, e.g.
  `?experienceLevel=fresher`, `?page=N`
- `freshergo.com/remote-jobs` — **hit one 503 error during testing.**
  Could be transient (retry logic needed) or intermittent load issue —
  verify with a few retries before assuming it's broken.

**Pagination confirmed:** simple `?page=N` pattern, up to 9 pages seen
on one role alone.

**Per-listing fields available:** job title, company name + logo, tech/
skill tags, salary (often "Salary not disclosed" — handle like
Internshala's stipend field), posted-time ("X days ago" / "Yesterday" /
"Today" — same format family as Internshala, existing `parse_age_in_days`
logic in `filter.py` should mostly just work here too), and a link to
FresherGo's own `/jobs/{slug}-{id}` detail page.

**Not yet verified — do this first when building:** whether the
FresherGo job detail page (`/jobs/{slug}-{id}`) exposes the actual
company's Greenhouse/Lever/Ashby apply URL directly, or requires
following a redirect/second link. Fetch one real detail page and check
before assuming.

**Parsing approach:** learn from the Internshala lesson — don't hardcode
fragile CSS classes. FresherGo's URL structure (`/jobs/{slug}-{id}`) is
stable and routing-based, same pattern that worked well for Internshala's
`/internship/detail/` approach. Build the parser the same way.

---

## PRIORITY 2 — Keep the 4 already-verified free WFH APIs as secondary sources

Still valid, still free, still no scraping fragility (real JSON APIs,
no key needed): **RemoteOK** (`remoteok.com/api`), **Himalayas**
(`himalayas.app/jobs/api`), **Jobicy** (`jobicy.com/api/v2/remote-jobs`),
**Arbeitnow** (public API, Europe-focused). Use these for breadth
alongside FresherGo, not instead of it.

**Known overlap to handle:** several FresherGo listings show images
served from `cdn-images.himalayas.app`, meaning FresherGo partially
sources through Himalayas already. The same job could show up from both
sources with different link formats, producing two different hashes in
dedup (`job_model.py` hashes by link). Not a blocker, just a known minor
duplicate risk — worth a note in code, not worth solving in v1.

---

## PRIORITY 3 — Curated direct-company-API list (now secondary, not primary)

Given FresherGo already aggregates 1,097 companies with fresher-specific
filtering, **don't hand-build a large company list manually** — that's
solving a problem FresherGo already solves at scale. Keep only a small
confirmed set as a fallback/highlight list:

**Confirmed real, live public ATS boards (verified directly):**

| Company | ATS | Endpoint pattern |
|---|---|---|
| You.com | Greenhouse | boards-api.greenhouse.io/v1/boards/youcom/jobs |
| VRChat | Lever | api.lever.co/v0/postings/vrchat?mode=json |
| Cloudflare | Greenhouse | boards-api.greenhouse.io/v1/boards/cloudflare/jobs |
| Celonis | Greenhouse | boards-api.greenhouse.io/v1/boards/celonis/jobs |
| G-P (Globalization Partners) | Greenhouse | boards-api.greenhouse.io/v1/boards/globalizationpartners/jobs — had a live remote Business Intelligence Analyst role at time of testing |
| SimilarWeb | Greenhouse | boards-api.greenhouse.io/v1/boards/similarweb/jobs |

**From your original 48-company list — status:**

- **Confirmed has a public ATS presence** (found live on FresherGo,
  exact ATS not independently confirmed): Impiricus
- **Not verified this session** (ran out of efficient search budget —
  check via `freshergo.com/search?q={company}` first, it's faster than
  searching externally): Dropbox, Sezzle, Aura, Simply Wall St, CoinDCX,
  Actian, AffirmedRx, SullivanCotter, Mitsubishi Chemical Group, Kapitus,
  Enveritas, Sanas, OneStop ESG
- **No evidence of Greenhouse/Lever/Ashby presence found** — likely too
  small to use these platforms, or use something else entirely: Wowoo,
  Versich, Zdminds, Essentially AI, PrimrIQ, TechUp Labs, Brainnest,
  Optimspace, VCBay, Webkit24, App Zime Technologies, Ideally Square
  Global, SkillsCapital, dbLogic, ChatSpark, SkillDzire Technologies, Neo
  Skillz, TopDataWorks, Greenmentor, Prepisely, Future Interns, ArGo
  Intern, SkillzenLoop, Wake Up Whistle, Evoastra Ventures, Shopflo,
  Impactree Data Technologies, ReGeneva, Carbon Crunch, Netpeak.
  **Caution:** several of these names read like small intern-placement
  agencies rather than direct employers — worth a legitimacy check before
  trusting them as a "credible" source, separate from the ATS-presence
  question.

**Fast way to resolve the "not verified" list:** query
`freshergo.com/search?q={company_name}` for each one instead of external
search — if FresherGo has them indexed, that confirms both legitimacy
and scrapeability in one step.

---

## PRIORITY 4 — Technopark / Infopark

**Not tested this session — first task when building this:**
`requests.get()` against `technoparkjobs.com` and
`keralatechjobs.pages.dev` and check if the response HTML contains the
actual job listings (view-source style check) or an empty JS shell like
the official Technopark site. If either is static, build a scraper
following the same URL-pattern approach as Internshala/FresherGo. If
both are JS-rendered too, this drops to a Playwright-required task —
don't build that unless the static path fails.

---

## PRIORITY 5 — Explicitly out of scope (confirmed dead ends, don't revisit)

- **Indeed** — official API dead since 2023/2024, no free path exists
- **Naukri, Foundit/Monster** — same situation, anti-bot + paid-only
  scraping services
- **Kerala Gov source** — JS-rendered, no simpler alternative found,
  previously returned 0 jobs anyway; not worth the effort

---

## Build order summary

1. FresherGo integration (role pages + remote-jobs page, once 503 is
   confirmed transient) — highest value, already verified scrapeable
2. Add the 4 WFH aggregator APIs as `sources/` modules (same pattern as
   `internshala.py`)
3. Add the 6 confirmed direct-company sources as a small highlight list
4. Test Technopark/Infopark aggregator sites for static HTML
5. Use FresherGo's own search to resolve the "not verified" company list
   instead of external searching
