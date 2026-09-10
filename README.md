# Metro Staffing — Job Advertising Spend Analysis (Power BI)

A five-page Power BI report analysing one month (January 2019) of Metro Staffing's online job
advertising: **$47,543 of spend, 144,277 clicks, 12,885 applications, 2,391 requisitions** across
seven vendors, 19 job categories and 23 countries.

The brief: acting as an analyst at "Out-of-the-Box Analytics", find the KPIs that show whether the
client's advertising money is working, and recommend how to allocate next month's budget better.

**Workbook:** [`Metro Staffing Ad Spend Analysis.pbix`](Metro%20Staffing%20Ad%20Spend%20Analysis.pbix)
— the data model is embedded, so it opens and renders with no refresh and no dependency on the
source workbook.

> Udacity *Business Intelligence Analytics* — "Out of the Box Analytics" project.

---

## Headline findings

**1. One vendor bills a flat fee and it is the single biggest drain on hiring volume.**
`Job Inc` charges **~$470.90 every single day, all 31 days** — $14,599.78, or **30.7% of the budget
for 10.4% of the applications**, at **$10.94 per application** against `Awesome Jobs`' **$2.77**.
Its apparent $2.68 cost per click is an artifact of a fixed daily fee, not click pricing. Re-pointing
that budget at the benchmark buys roughly **5,273 applications instead of 1,335**.

**2. Spend was paced on the calendar, not on price.**
$32,804 (**69%**) went out in the first 16 days at $4.95 per application. Cost per click then stepped
down from ~$0.46 to ~$0.16 on **17 January** and stayed there. The cheapest week (week of 21 Jan,
$1.76 per application) received the *smallest* budget share, 11%. A single day — 31 January —
absorbed $4,832 (10.2%) at $6.88 per application.

**3. Category budgets are inverted against yield.**
Sales takes 35.1% of spend at $7.77 per application and a 6.5% apply rate. Operations converts at
**15.7% for $1.67** — the cheapest applications of the month — on 3.9% of spend.

**4. Location cost spread is 3.6×.**
Across the ten states funded above $1,000: New Jersey $1.93 and Georgia $2.11, versus Kentucky $6.24
and New York $6.99.

At the $2.77 benchmark, January's budget would have produced roughly **4,287 more applications** than
it did. The `Applications Forgone` measure computes that live under any slicer selection.

---

## Pages

| Tab | KPI combination | Visuals |
| --- | --- | --- |
| KPI 1 · Vendor Efficiency | Vendors × Spend × CPA | Bar, Donut, Table |
| KPI 2 · Category Yield | Category × Applications × Clicks | Column, Treemap, Table |
| KPI 3 · Spend Pacing | Date × CPC × Spend | Line, Waterfall, Table |
| KPI 4 · Location Efficiency *(bonus)* | State × City × CPA | Bar, Treemap, Table |
| Executive Summary | one visual carried from each of KPI 1–3 | Bar, Treemap, Line |

Each KPI tab carries a text summary (one sentence per visual plus a "why this matters to Metro
Staffing" paragraph) and a category or vendor **slicer**. No visual type is reused within a tab.

---

## Data-integrity decisions

These are the parts worth reading, because each one changes the numbers.

**1. 99 placeholder rows removed at the source.**
They carry `Title = "Unknown Jobs"` with `City` and `Category` = `_not_specified_`, and they hold
**3,578 applications against zero clicks and zero spend** — 21.7% of the month's applications, with
nothing to attribute them to. They are dropped in Power Query (the `Cleaned` step of the `Jobs`
query) rather than hidden per-visual, so they cannot leak into any visual, table or slicer.
Removing them moves total applications from 16,463 to **12,885** and blended CPA from $2.89 to
**$3.69**. Every figure in this repo is post-cleaning.

**2. The workbook's row-level `CPA` and `CPC` columns are discarded.**
They are per-row ratios; averaging them across rows understates cost, and the error grows with
aggregation. Both are re-derived as DAX measures — `DIVIDE(SUM(Spend), SUM(Applies))` and
`DIVIDE(SUM(Spend), SUM(Clicks))` — so they stay correct at every grain and under every filter.

**3. 50,766 trailing blank rows** sit inside the sheet's used range and are filtered out.

**4. The source sheet is named `Ouput`** (sic), not `Sheet1`, which is empty.

**5. KPI 4 is filtered to `Country = "US"`** (85% of spend), which also removes the 12 rows with a
blank country so no empty category appears on that page.

---

## Model

- `Jobs` (fact, 34,039 rows after cleaning) and a generated `Date` table with Monday-start weeks,
  marked as a date table. Related on `Jobs[Date] → Date[Date]`. Auto date/time is off.
- 16 measures in four display folders:
  - **1 Volume** — `Total Spend`, `Total Clicks`, `Total Applies`, `Jobs Advertised`
  - **2 Efficiency** — `CPC`, `CPA`, `Apply Rate`
  - **3 Allocation** — `Spend Share`, `Apply Share`, `Efficiency Gap`
  - **4 Reallocation Model** — `Benchmark CPA`, `Applies at Benchmark CPA`, `Applications Forgone`
- `Efficiency Gap` = apply share − spend share, in percentage points. Positive means a slice returns
  more applications than the budget it consumes; negative means it is over-funded. It is the one
  column that makes the `Job Inc` problem obvious at a glance (−20.3 pp).
- `Benchmark CPA` evaluates the best cost per application achieved by any vendor that actually
  charged for traffic, *within the current filter context*, so the reallocation upside re-computes
  as you slice.

---

## How this was built

The report is generated as code and finalised in Power BI Desktop.

```
tools/
  model.py      # emits the .SemanticModel  (TMDL: tables, columns, DAX measures, M queries)
  report.py     # emits the .Report         (PBIR JSON: pages, visuals, formatting, text boxes)
  build.py      # assembles the .pbip project
  validate.py   # validates every generated JSON against Microsoft's published PBIR schemas
```

```bash
python tools/build.py          # regenerate the .pbip project in place
python tools/validate.py .     # 37 JSON files vs. the official schemas
```

Then: open the `.pbip` in Power BI Desktop → **Refresh** (a fresh project carries no cached data) →
**File ▸ Save as ▸ Browse this device**, type **Power BI file (\*.pbix)**.

Every figure quoted above was computed independently in pandas first and then reconciled against
what Power BI actually rendered — they agree exactly ($47,542.90 spend, 12,885 applications,
$3.69 blended CPA).

A `.pbix` cannot be written by hand (its `DataModel` part is a binary VertiPaq blob), but a
[Power BI Project](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
can be, and Desktop converts it. The JSON shapes follow Microsoft's published
[PBIR schemas](https://github.com/microsoft/json-schemas/tree/main/fabric/item/report/definition).

To repoint the data source: open the `.pbip`, then **Transform data ▸ Manage parameters ▸ `SourceFile`**.

---

## Repository contents

| Path | What it is |
| --- | --- |
| `Metro Staffing Ad Spend Analysis.pbix` | The report, data embedded. Open this. |
| `Metro Staffing Ad Spend Analysis.pbip` + `.Report/` + `.SemanticModel/` | Editable project source — TMDL model and PBIR report JSON, diffable in git. |
| `tools/` | The generator and schema validator described above. |
| `Data/` | Source workbook (see attribution below). |

`.pbi/localSettings.json` and `.pbi/cache.abf` are git-ignored: per-user state and a local data
cache, not part of the definition.

## Data attribution

`Data/job-cloud-output-jan-2019.xlsx` is course material supplied by Udacity for this project and is
included so the project is reproducible. It is
[publicly downloadable from Udacity](https://video.udacity-data.com/topher/2022/October/6351a208_job-cloud-output-jan-2019/job-cloud-output-jan-2019.xlsx).
"Metro Staffing", the vendor names and the employer are fictional; all rights to the dataset remain
with Udacity. The analysis, model, report and generator are my own work.
