"""Emit the .SemanticModel (TMDL) half of the Metro Staffing PBIP."""
import os, uuid, textwrap

NS = uuid.UUID("6f1d0c2a-1f4b-4a8e-9c3d-77aa10b25e01")
def lt(s): return str(uuid.uuid5(NS, s))

def tabify(src, tabs):
    """Indent a block of text with `tabs` tab characters per line."""
    pad = "\t" * tabs
    return "\n".join(pad + ln if ln.strip() else "" for ln in src.strip("\n").split("\n"))

# ----------------------------------------------------------------- Jobs (M)
JOBS_M = r'''
let
    Source = Excel.Workbook(File.Contents(SourceFile), null, true),
    Sheet  = Source{[Item = "Ouput", Kind = "Sheet"]}[Data],
    Headers = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),

    // Drop the workbook's row-level CPA / CPC columns. They are per-row ratios and
    // averaging them across rows understates cost; CPA and CPC are re-derived as
    // DAX measures (total spend / total applies) so they stay correct at every grain.
    DropRatios = Table.RemoveColumns(Headers, {"CPA", "CPC"}),

    // Trailing blank rows in the sheet's used range.
    DropBlanks = Table.SelectRows(DropRatios, each [Req Num] <> null and [Date] <> null),

    Typed = Table.TransformColumnTypes(
        DropBlanks,
        {
            {"Date", type date}, {"Title", type text}, {"City", type text},
            {"State", type text}, {"Country", type text}, {"Employer", type text},
            {"Category", type text}, {"Req Num", type text}, {"Vendors", type text},
            {"Clicks", Int64.Type}, {"Applies", Int64.Type}, {"Spend", type number}
        }
    ),

    // DATA INTEGRITY: 99 placeholder rows carry Title = "Unknown Jobs" with
    // City and Category = "_not_specified_". They hold 3,578 applications against
    // zero clicks and zero spend, so they are unattributable and are removed here
    // rather than filtered per-visual. This keeps every visual free of them.
    Cleaned = Table.SelectRows(
        Typed,
        each [Category] <> "_not_specified_"
            and [City] <> "_not_specified_"
            and [Title] <> "Unknown Jobs"
    )
in
    Cleaned
'''

DATE_M = r'''
let
    First   = List.Min(Jobs[Date]),
    Last    = List.Max(Jobs[Date]),
    // Pad out to whole Monday-start weeks so weekly buckets are never partial.
    WeekOne = Date.StartOfWeek(First, Day.Monday),
    WeekEnd = Date.EndOfWeek(Last, Day.Monday),
    Days    = List.Dates(WeekOne, Duration.Days(WeekEnd - WeekOne) + 1, #duration(1, 0, 0, 0)),
    Base    = Table.FromList(Days, Splitter.SplitByNothing(), {"Date"}),
    Typed   = Table.TransformColumnTypes(Base, {{"Date", type date}}),

    AddDay      = Table.AddColumn(Typed, "Day", each Date.Day([Date]), Int64.Type),
    AddLabel    = Table.AddColumn(AddDay, "Day Label", each Date.ToText([Date], [Format = "MMM dd", Culture = "en-US"]), type text),
    AddDowNum   = Table.AddColumn(AddLabel, "Weekday Number", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),
    AddDow      = Table.AddColumn(AddDowNum, "Weekday", each Date.ToText([Date], [Format = "ddd", Culture = "en-US"]), type text),
    AddType     = Table.AddColumn(AddDow, "Day Type", each if [Weekday Number] >= 6 then "Weekend" else "Weekday", type text),
    AddWkStart  = Table.AddColumn(AddType, "Week Start", each Date.StartOfWeek([Date], Day.Monday), type date),
    AddWkIndex  = Table.AddColumn(AddWkStart, "Week Number",
                      each Duration.Days([Week Start] - WeekOne) / 7 + 1, Int64.Type),
    AddWkLabel  = Table.AddColumn(AddWkIndex, "Week",
                      each "Week " & Text.From([Week Number]) & " ("
                           & Date.ToText([Week Start], [Format = "MMM dd", Culture = "en-US"]) & ")", type text)
in
    AddWkLabel
'''

# ----------------------------------------------------------------- measures
# (name, dax, formatString, displayFolder, description)
MEASURES = [
    ("Total Spend", "SUM ( Jobs[Spend] )", '"$"#,0.00', "1 Volume",
     "Total advertising dollars spent."),
    ("Total Clicks", "SUM ( Jobs[Clicks] )", "#,0", "1 Volume",
     "Total clicks delivered against Metro Staffing job adverts."),
    ("Total Applies", "SUM ( Jobs[Applies] )", "#,0", "1 Volume",
     "Total completed applications."),
    ("Jobs Advertised", "DISTINCTCOUNT ( Jobs[Req Num] )", "#,0", "1 Volume",
     "Distinct requisitions advertised."),

    ("CPC", "DIVIDE ( [Total Spend], [Total Clicks] )", '"$"#,0.000', "2 Efficiency",
     "Blended cost per click: total spend divided by total clicks. Correct at every grain, "
     "unlike averaging the workbook's row-level CPC."),
    ("CPA", "DIVIDE ( [Total Spend], [Total Applies] )", '"$"#,0.00', "2 Efficiency",
     "Blended cost per application: total spend divided by total applications."),
    ("Apply Rate", "DIVIDE ( [Total Applies], [Total Clicks] )", "0.0%", "2 Efficiency",
     "Share of clicks that convert into a completed application."),

    ("Spend Share", "DIVIDE ( [Total Spend], CALCULATE ( [Total Spend], ALLSELECTED () ) )",
     "0.0%", "3 Allocation", "This slice's share of the spend visible in the visual."),
    ("Apply Share", "DIVIDE ( [Total Applies], CALCULATE ( [Total Applies], ALLSELECTED () ) )",
     "0.0%", "3 Allocation", "This slice's share of the applications visible in the visual."),
    ("Efficiency Gap", "[Apply Share] - [Spend Share]", "+0.0%;-0.0%;0.0%", "3 Allocation",
     "Apply share minus spend share, in percentage points. Positive means the slice returns "
     "more applications than the budget it consumes; negative means it is over-funded."),
]

BENCHMARK_CPA = '''
VAR _ByVendor =
    ADDCOLUMNS (
        CALCULATETABLE ( VALUES ( Jobs[Vendors] ), REMOVEFILTERS ( Jobs[Vendors] ) ),
        "@Spend", CALCULATE ( SUM ( Jobs[Spend] ) ),
        "@Applies", CALCULATE ( SUM ( Jobs[Applies] ) )
    )
VAR _Paid =
    FILTER ( _ByVendor, [@Spend] > 0 && [@Applies] > 0 )
RETURN
    MINX ( _Paid, DIVIDE ( [@Spend], [@Applies] ) )
'''

MEASURES_MULTILINE = [
    ("Benchmark CPA", BENCHMARK_CPA, '"$"#,0.00', "4 Reallocation Model",
     "The lowest cost per application achieved by any vendor that actually charged for "
     "traffic, evaluated inside the current slicer context. Used as the reallocation target."),
    ("Applies at Benchmark CPA",
     "DIVIDE ( [Total Spend], [Benchmark CPA] )", "#,0", "4 Reallocation Model",
     "Applications the same budget would buy at the benchmark cost per application."),
    ("Applications Forgone",
     "MAX ( 0, [Applies at Benchmark CPA] - [Total Applies] )", "#,0", "4 Reallocation Model",
     "Applications lost by buying at the current cost per application instead of the "
     "benchmark. This is the size of the reallocation prize."),
]


def measure_block(name, dax, fmt, folder, desc, multiline):
    out = []
    if desc:
        for ln in textwrap.wrap(desc, 96):
            out.append(f"\t/// {ln}")
    if multiline:
        out.append(f"\tmeasure '{name}' =")
        out.append(tabify(dax, 3))
    else:
        out.append(f"\tmeasure '{name}' = {dax}")
    out.append(f"\t\tformatString: {fmt}")
    out.append(f"\t\tdisplayFolder: {folder}")
    out.append(f"\t\tlineageTag: {lt('m:' + name)}")
    out.append("")
    return "\n".join(out)


JOBS_COLUMNS = [
    # (name, dataType, summarizeBy, extra lines)
    # No isKey here: many rows share a date. isKey belongs only on the Date dimension,
    # where it (with dataCategory: Time) is what marks the table as a date table.
    ("Date", "dateTime", "none", ['\t\tformatString: yyyy-mm-dd']),
    ("Title", "string", "none", []),
    ("City", "string", "none", []),
    ("State", "string", "none", []),
    ("Country", "string", "none", []),
    ("Employer", "string", "none", []),
    ("Category", "string", "none", []),
    ("Req Num", "string", "none", []),
    ("Vendors", "string", "none", []),
    ("Clicks", "int64", "sum", ['\t\tformatString: #,0']),
    ("Applies", "int64", "sum", ['\t\tformatString: #,0']),
    ("Spend", "double", "sum", ['\t\tformatString: "$"#,0.00']),
]

DATE_COLUMNS = [
    ("Date", "dateTime", "none", ['\t\tformatString: yyyy-mm-dd', '\t\tisKey']),
    ("Day", "int64", "none", []),
    ("Day Label", "string", "none", ["\t\tsortByColumn: Date"]),
    ("Weekday Number", "int64", "none", ["\t\tisHidden"]),
    ("Weekday", "string", "none", ["\t\tsortByColumn: 'Weekday Number'"]),
    ("Day Type", "string", "none", []),
    ("Week Start", "dateTime", "none", ['\t\tformatString: yyyy-mm-dd']),
    ("Week Number", "int64", "none", ["\t\tisHidden"]),
    ("Week", "string", "none", ["\t\tsortByColumn: 'Week Number'"]),
]


def column_block(table, name, dtype, summarize, extra):
    q = f"'{name}'" if " " in name else name
    out = [f"\tcolumn {q}", f"\t\tdataType: {dtype}"]
    out += extra
    out.append(f"\t\tlineageTag: {lt(f'c:{table}:{name}')}")
    out.append(f"\t\tsummarizeBy: {summarize}")
    out.append(f"\t\tsourceColumn: {name}")
    out.append("")
    out.append("\t\tannotation SummarizationSetBy = Automatic")
    if dtype == "dateTime":
        out.append("")
        out.append('\t\tannotation UnderlyingDateTimeDataType = Date')
    out.append("")
    return "\n".join(out)


def build(root, name, excel_rel):
    sm = os.path.join(root, f"{name}.SemanticModel")
    dfn = os.path.join(sm, "definition")
    os.makedirs(os.path.join(dfn, "tables"), exist_ok=True)

    w = lambda p, s: open(p, "w", encoding="utf-8", newline="\n").write(s)

    w(os.path.join(sm, ".platform"),
      '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/'
      'platformProperties/2.0.0/schema.json",\n  "metadata": {\n    "type": "SemanticModel",\n'
      f'    "displayName": "{name}"\n  }},\n  "config": {{\n    "version": "2.0",\n'
      f'    "logicalId": "{lt("sm")}"\n  }}\n}}\n')

    w(os.path.join(sm, "definition.pbism"),
      '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/'
      'definitionProperties/1.0.0/schema.json",\n  "version": "4.2",\n  "settings": {}\n}\n')

    w(os.path.join(dfn, "database.tmdl"), "database\n\tcompatibilityLevel: 1567\n")

    # ---- model.tmdl
    model = f"""model Model
\tculture: en-US
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tsourceQueryCulture: en-US
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

queryGroup Parameters

\tannotation PBI_QueryGroupOrder = 0

queryGroup Data

\tannotation PBI_QueryGroupOrder = 1

annotation __PBI_TimeIntelligenceEnabled = 0

annotation PBI_QueryOrder = ["SourceFile","Jobs","Date"]

ref table Jobs
ref table 'Date'
"""
    w(os.path.join(dfn, "model.tmdl"), model)

    # ---- expressions.tmdl (source-path parameter)
    expr = f'''expression SourceFile = "{excel_rel}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {lt("p:SourceFile")}
\tqueryGroup: Parameters

\tannotation PBI_ResultType = Text
'''
    w(os.path.join(dfn, "expressions.tmdl"), expr)

    # ---- relationships.tmdl
    rel = f"""relationship {lt("r:jobs-date")}
\tfromColumn: Jobs.Date
\ttoColumn: 'Date'.Date
"""
    w(os.path.join(dfn, "relationships.tmdl"), rel)

    # ---- Jobs table
    parts = [f"table Jobs\n\tlineageTag: {lt('t:Jobs')}\n"]
    for m in MEASURES:
        parts.append(measure_block(*m, multiline=False))
    for m in MEASURES_MULTILINE:
        parts.append(measure_block(*m, multiline=True))
    for c in JOBS_COLUMNS:
        parts.append(column_block("Jobs", *c))
    parts.append("\tpartition Jobs = m\n\t\tmode: import\n\t\tqueryGroup: Data\n\t\tsource =\n"
                 + tabify(JOBS_M, 4) + "\n")
    parts.append("\tannotation PBI_ResultType = Table\n")
    w(os.path.join(dfn, "tables", "Jobs.tmdl"), "\n".join(parts))

    # ---- Date table
    parts = [f"table 'Date'\n\tlineageTag: {lt('t:Date')}\n\tdataCategory: Time\n"]
    for c in DATE_COLUMNS:
        parts.append(column_block("Date", *c))
    parts.append("\tpartition 'Date' = m\n\t\tmode: import\n\t\tqueryGroup: Data\n\t\tsource =\n"
                 + tabify(DATE_M, 4) + "\n")
    parts.append("\tannotation PBI_ResultType = Table\n")
    w(os.path.join(dfn, "tables", "Date.tmdl"), "\n".join(parts))

    return sm
