"""Emit the .Report (PBIR) half of the Metro Staffing PBIP."""
import os, json, uuid

NS = uuid.UUID("6f1d0c2a-1f4b-4a8e-9c3d-77aa10b25e01")
def nm(s): return uuid.uuid5(NS, s).hex[:20]

SCH_VIS  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.8.0/schema.json"
SCH_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCH_PGS  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
SCH_RPT  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json"
BASE_THEME = "CY25SU11"
THEME_SRC  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", f"{BASE_THEME}.json")
SCH_VER  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"

# ----------------------------------------------------------------- palette
INK, MUTED       = "#16232E", "#5C6B7A"
PRIMARY, ALERT   = "#2C5F8D", "#C0483F"
GOOD, AMBER      = "#2E8B70", "#D98C2B"
TEAL, PLUM       = "#3E7C8C", "#7A5C87"
CARD, BORDER     = "#FFFFFF", "#DCE3EA"
PAGEBG, BANDBG   = "#EEF2F6", "#22405C"

W, H = 1280, 720
# header band / slicer / 2x2 content grid
HDR   = dict(x=0,    y=0,   width=W,   height=104)
# slicer sits fully inside the header band, right-aligned
SLC   = dict(x=996,  y=46,  width=268, height=44)
V1    = dict(x=16,   y=120, width=620, height=286)
V2    = dict(x=652,  y=120, width=612, height=286)
V3    = dict(x=16,   y=418, width=620, height=286)
TXT   = dict(x=652,  y=418, width=612, height=286)

# ----------------------------------------------------------------- helpers
def lit(v):
    if isinstance(v, bool):  s = "true" if v else "false"
    elif isinstance(v, int): s = f"{v}L"
    elif isinstance(v, float): s = f"{v}D"
    else: s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}

def col(hexv): return {"solid": {"color": lit(hexv)}}

def fld_col(entity, prop): return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
def fld_mea(entity, prop): return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}

def P(field, entity, prop, display=None, active=None):
    p = {"field": field, "queryRef": f"{entity}.{prop}", "nativeQueryRef": display or prop}
    if display: p["displayName"] = display
    if active is not None: p["active"] = active
    return p

def PC(entity, prop, display=None, active=None):
    return P(fld_col(entity, prop), entity, prop, display, active)

def PM(entity, prop, display=None):
    return P(fld_mea(entity, prop), entity, prop, display)

def sort_by(field, direction="Descending", default=True):
    return {"sort": [{"field": field, "direction": direction}], "isDefaultSort": default}


def card(title=None, size=12.5, tcolor=INK, shadow=True):
    """visualContainerObjects for a white 'card' with an optional bold title."""
    o = {}
    if title:
        o["title"] = [{"properties": {
            "show": lit(True), "text": lit(title), "fontSize": lit(size),
            "fontColor": col(tcolor), "bold": lit(True), "alignment": lit("left"),
            "titleWrap": lit(True)}}]
    else:
        o["title"] = [{"properties": {"show": lit(False)}}]
    o["subTitle"]   = [{"properties": {"show": lit(False)}}]
    o["background"] = [{"properties": {"show": lit(True), "color": col(CARD), "transparency": lit(0)}}]
    o["border"]     = [{"properties": {"show": lit(True), "color": col(BORDER), "radius": lit(6)}}]
    if shadow:
        o["dropShadow"] = [{"properties": {
            "show": lit(True), "preset": lit("BottomRight"),
            "color": col("#8C9BAA"), "transparency": lit(80)}}]
    o["padding"] = [{"properties": {"left": lit(10), "right": lit(10), "top": lit(6), "bottom": lit(6)}}]
    return o


def axes(cat_title=None, val_title=None, cat_size=9.0, val_size=9.0, val_units=None):
    ca = {"showAxisTitle": lit(bool(cat_title)), "fontSize": lit(cat_size),
          "labelColor": col(MUTED), "titleColor": col(MUTED)}
    if cat_title: ca["titleText"] = lit(cat_title)
    va = {"showAxisTitle": lit(bool(val_title)), "fontSize": lit(val_size),
          "labelColor": col(MUTED), "titleColor": col(MUTED),
          "gridlineColor": col("#EAEFF3")}
    if val_title: va["titleText"] = lit(val_title)
    if val_units is not None: va["labelDisplayUnits"] = lit(float(val_units))
    return {"categoryAxis": [{"properties": ca}], "valueAxis": [{"properties": va}]}


def fill(hexv): return {"dataPoint": [{"properties": {"fill": col(hexv)}}]}

def labels(on=True, size=9.0, color_=INK, precision=None, units=None):
    p = {"show": lit(on), "fontSize": lit(size), "color": col(color_)}
    if precision is not None: p["labelPrecision"] = lit(precision)
    if units is not None: p["labelDisplayUnits"] = lit(float(units))
    return {"labels": [{"properties": p}]}

def legend(on=False, pos="Top", size=9.0):
    return {"legend": [{"properties": {
        "show": lit(on), "position": lit(pos), "showTitle": lit(False),
        "fontSize": lit(size), "labelColor": col(MUTED)}}]}


def visual(name, vtype, pos, query=None, objects=None, vco=None, zi=0, tab=None):
    v = {"visualType": vtype}
    if query:   v["query"] = query
    if objects: v["objects"] = objects
    if vco:     v["visualContainerObjects"] = vco
    v["drillFilterOtherVisuals"] = True
    p = dict(pos); p["z"] = zi
    p["tabOrder"] = tab if tab is not None else zi
    return {"$schema": SCH_VIS, "name": name, "position": p, "visual": v}


# ----------------------------------------------------------------- textbox
def run(text, size="9.5pt", bold=False, color_=INK, italic=False):
    st = {"fontSize": size, "color": color_}
    if bold: st["fontWeight"] = "bold"
    if italic: st["fontStyle"] = "italic"
    return {"value": text, "textStyle": st}

def para(runs, align="left", spacing=None):
    p = {"textRuns": runs, "horizontalTextAlignment": align}
    return p

def textbox(name, pos, paragraphs, vco=None, zi=1000):
    v = {"visualType": "textbox",
         "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
         "drillFilterOtherVisuals": True}
    v["visualContainerObjects"] = vco or {
        "title": [{"properties": {"show": lit(False)}}],
        "background": [{"properties": {"show": lit(False)}}],
        "border": [{"properties": {"show": lit(False)}}]}
    p = dict(pos); p["z"] = zi; p["tabOrder"] = zi
    return {"$schema": SCH_VIS, "name": name, "position": p, "visual": v}


def header(page_key, kicker, title, subtitle):
    """Dark banner across the top of a page."""
    paras = [
        para([run(kicker, "9pt", True, "#8FB6D8")]),
        para([run(title, "17pt", True, "#FFFFFF")]),
        para([run(subtitle, "9.5pt", False, "#C9D8E5")]),
    ]
    vco = {
        "title": [{"properties": {"show": lit(False)}}],
        "background": [{"properties": {"show": lit(True), "color": col(BANDBG), "transparency": lit(0)}}],
        "border": [{"properties": {"show": lit(False)}}],
        "padding": [{"properties": {"left": lit(18), "top": lit(6), "right": lit(14), "bottom": lit(4)}}],
    }
    return textbox(nm(page_key + ":hdr"), HDR, paras, vco, zi=0)


def summary(page_key, heading, bullets, footer_label, footer_text, size=9.5):
    body, head = f"{size}pt", f"{size + 1.5}pt"
    paras = [para([run(heading, head, True, PRIMARY)])]
    for b in bullets:
        paras.append(para([run("▪  ", body, True, PRIMARY), run(b, body)]))
    paras.append(para([run(" ", "6pt")]))
    paras.append(para([run(footer_label, body, True, ALERT), run(footer_text, body)]))
    vco = card(None, shadow=True)
    vco["padding"] = [{"properties": {"left": lit(14), "right": lit(14), "top": lit(12), "bottom": lit(10)}}]
    return textbox(nm(page_key + ":sum"), TXT, paras, vco, zi=900)


def slicer(page_key, entity, prop, header_text):
    q = {"queryState": {"Values": {"projections": [PC(entity, prop, active=True)]}}}
    objs = {
        "data": [{"properties": {"mode": lit("Dropdown")}}],
        "header": [{"properties": {"show": lit(True), "text": lit(header_text),
                                   "textSize": lit(9.5), "fontColor": col(INK),
                                   "background": col(CARD), "bold": lit(True)}}],
        "items": [{"properties": {"textSize": lit(9.0), "fontColor": col(INK)}}],
    }
    vco = card(None, shadow=False)
    del vco["padding"]
    return visual(nm(page_key + ":slc"), "slicer", SLC, q, objs, vco, zi=800)


# ----------------------------------------------------------------- page
def page(key, display, visuals, page_filter=None):
    p = {"$schema": SCH_PAGE, "name": nm("pg:" + key), "displayName": display,
         "displayOption": "FitToPage", "height": H, "width": W,
         "objects": {"background": [{"properties": {"color": col(PAGEBG), "transparency": lit(0)}}],
                     "outspace":   [{"properties": {"color": col("#DFE6ED")}}]}}
    if page_filter: p["filterConfig"] = page_filter
    return p, visuals


def filter_in(entity, prop, values, fname):
    src = entity[0].lower()
    return {"filters": [{
        "name": nm(fname),
        "field": fld_col(entity, prop),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": src, "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": prop}}],
                "Values": [[lit(v)["expr"]] for v in values]}}}],
        },
        "howCreated": "User",
    }]}


# ================================================================= BUILD
J = "Jobs"
D = "Date"

def build(root, name):
    rp  = os.path.join(root, f"{name}.Report")
    dfn = os.path.join(rp, "definition")
    os.makedirs(os.path.join(dfn, "pages"), exist_ok=True)
    w = lambda p, o: open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, indent=2, ensure_ascii=False) + "\n")

    bt = os.path.join(rp, "StaticResources", "SharedResources", "BaseThemes")
    os.makedirs(bt, exist_ok=True)
    import shutil
    shutil.copy2(THEME_SRC, os.path.join(bt, f"{BASE_THEME}.json"))

    w(os.path.join(rp, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": name},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NS, "rpt"))}})

    w(os.path.join(rp, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}})

    w(os.path.join(dfn, "version.json"), {"$schema": SCH_VER, "version": "2.0.0"})

    w(os.path.join(dfn, "report.json"), {
        "$schema": SCH_RPT,
        "themeCollection": {"baseTheme": {
            "name": BASE_THEME, "type": "SharedResources",
            "reportVersionAtImport": {"visual": "2.8.0", "report": "3.2.0", "page": "2.1.0"}}},
        "resourcePackages": [{
            "name": "SharedResources", "type": "SharedResources",
            "items": [{"name": BASE_THEME,
                       "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]}],
        "objects": {
            "outspacePane": [{"properties": {"expanded": lit(False), "visible": lit(True)}}],
        },
        "settings": {"useStylableVisualContainerHeader": True,
                     "defaultFilterActionIsDataFilter": True},
        "annotations": [{"name": "author", "value": "Out-of-the-Box Analytics Inc."}]})

    pages = []

    # ============================================================ KPI 1
    k = "kpi1"
    vis = [
        header(k, "KPI 1  ·  VENDORS × SPEND × COST PER APPLICATION",
               "Vendor Efficiency: 96% of the budget sits with two vendors",
               "January 2019  ·  $47,543 spend  ·  144,277 clicks  ·  12,885 applications  ·  2,391 requisitions"),
        slicer(k, J, "Category", "Filter by job category"),

        visual(nm(k + ":v1"), "clusteredBarChart", V1,
               {"queryState": {
                   "Category": {"projections": [PC(J, "Vendors", active=True)]},
                   "Y": {"projections": [PM(J, "Total Spend")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Spend"))},
               {**fill(PRIMARY), **axes(val_units=0),
                **labels(True, 9.0, INK, precision=0, units=1), **legend(False)},
               card("Where the money went — ad spend by vendor"), zi=1),

        visual(nm(k + ":v2"), "donutChart", V2,
               {"queryState": {
                   "Category": {"projections": [PC(J, "Vendors", active=True)]},
                   "Y": {"projections": [PM(J, "Total Applies")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Applies"))},
               {**labels(True, 9.0, INK, precision=0, units=1), **legend(True, "Right", 9.0)},
               card("What the money returned — share of applications by vendor"), zi=2),

        visual(nm(k + ":v3"), "tableEx", V3,
               {"queryState": {"Values": {"projections": [
                   PC(J, "Vendors"), PM(J, "Total Spend"), PM(J, "Total Applies"),
                   PM(J, "CPC"), PM(J, "CPA"), PM(J, "Efficiency Gap")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Spend"))},
               {"grid": [{"properties": {"gridVertical": lit(False),
                                         "outlineColor": col(BORDER), "textSize": lit(9.0)}}],
                "columnHeaders": [{"properties": {"fontColor": col("#FFFFFF"),
                                                  "backColor": col(PRIMARY),
                                                  "bold": lit(True), "fontSize": lit(9.0)}}],
                "values": [{"properties": {"fontSize": lit(9.0), "fontColor": col(INK)}}]},
               card("Vendor scorecard — price of a click, price of a hire"), zi=3),

        summary(k, "What these three visuals say", [
            "Ad spend by vendor: Metro Staffing put 96.5% of January's $47,543 through two vendors — "
            "Awesome Jobs at $31,255 (65.7%) and Job Inc at $14,600 (30.7%).",
            "Share of applications by vendor: the return does not follow the money. Awesome Jobs produced "
            "87.6% of the 12,885 applications; Job Inc produced 10.4% — a 20-point efficiency gap.",
            "Vendor scorecard: Job Inc costs $10.94 per application against Awesome Jobs' $2.77, and its "
            "$2.68 cost per click is 11x higher because it bills a flat ~$471 every single day of the month "
            "instead of charging per click.",
        ], "Why this matters to Metro Staffing:  ",
           "vendor choice, not budget size, is the largest single lever on hiring volume. Re-pointing "
           "Job Inc's $14,600 at performance-priced inventory at the $2.77 benchmark buys roughly 5,273 "
           "applications rather than 1,335 — about 3,938 more applications for identical spend."),
    ]
    pages.append(page(k, "KPI 1 · Vendor Efficiency", vis))

    # ============================================================ KPI 2
    k = "kpi2"
    vis = [
        header(k, "KPI 2  ·  CATEGORY × APPLICATIONS × CLICKS",
               "Category Yield: the cheapest applications get the smallest budget",
               "94% of spend is concentrated in four of the 19 job categories Metro Staffing advertised"),
        slicer(k, J, "Vendors", "Filter by vendor"),

        visual(nm(k + ":v1"), "clusteredColumnChart", V1,
               {"queryState": {
                   "Category": {"projections": [PC(J, "Category", active=True)]},
                   "Y": {"projections": [PM(J, "Total Applies")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Applies"))},
               {**fill(GOOD), **axes(val_units=0), **labels(False), **legend(False)},
               card("Applications delivered by job category"), zi=1),

        visual(nm(k + ":v2"), "treemap", V2,
               {"queryState": {
                   "Group": {"projections": [PC(J, "Category", active=True)]},
                   "Values": {"projections": [PM(J, "Total Spend")]}}},
               {**labels(True, 9.0, "#FFFFFF", precision=0, units=1), **legend(False)},
               card("Ad spend concentration by category"), zi=2),

        visual(nm(k + ":v3"), "tableEx", V3,
               {"queryState": {"Values": {"projections": [
                   PC(J, "Category"), PM(J, "Total Spend"), PM(J, "Total Applies"),
                   PM(J, "Apply Rate"), PM(J, "CPA"), PM(J, "Efficiency Gap")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Spend"))},
               {"grid": [{"properties": {"gridVertical": lit(False),
                                         "outlineColor": col(BORDER), "textSize": lit(9.0)}}],
                "columnHeaders": [{"properties": {"fontColor": col("#FFFFFF"),
                                                  "backColor": col(GOOD),
                                                  "bold": lit(True), "fontSize": lit(9.0)}}],
                "values": [{"properties": {"fontSize": lit(9.0), "fontColor": col(INK)}}]},
               card("Category scorecard — conversion rate against cost"), zi=3),

        summary(k, "What these three visuals say", [
            "Applications by category: Client Service delivered the most volume — 4,535 applications, "
            "35.2% of the total — while consuming only 28.3% of the budget.",
            "Ad spend concentration: 94% of spend sits in just four categories, with Sales alone absorbing "
            "$16,707 (35.1%) of the month.",
            "Category scorecard: Sales costs $7.77 per application at a 6.5% apply rate, while Operations "
            "converts at 15.7% for $1.67 — the cheapest applications Metro Staffing bought all month, on "
            "3.9% of the budget.",
        ], "Why this matters to Metro Staffing:  ",
           "the same dollar buys four to five times more applications in Operations and Client Service than "
           "in Sales, so category-level bid caps rather than one account-wide budget would lift total "
           "applications without adding a dollar of spend."),
    ]
    pages.append(page(k, "KPI 2 · Category Yield", vis))

    # ============================================================ KPI 3
    k = "kpi3"
    vis = [
        header(k, "KPI 3  ·  DATE × COST PER CLICK × SPEND",
               "Spend Pacing: the budget was spent on the calendar, not on price",
               "69% of the month's spend landed in the first 16 days, when clicks were three times more expensive"),
        slicer(k, J, "Vendors", "Filter by vendor"),

        visual(nm(k + ":v1"), "lineChart", V1,
               {"queryState": {
                   "Category": {"projections": [PC(D, "Date", active=True)]},
                   "Y": {"projections": [PM(J, "CPC")]}}},
               {"lineStyles": [{"properties": {"strokeWidth": lit(2), "lineColor": col(ALERT),
                                               "showMarker": lit(False), "areaShow": lit(False)}}],
                **axes(val_title="Cost per click", val_size=9.0),
                **labels(False), **legend(False)},
               card("Cost per click by day — a step change on 17 January"), zi=1),

        visual(nm(k + ":v2"), "waterfallChart", V2,
               {"queryState": {
                   "Category": {"projections": [PC(D, "Week", active=True)]},
                   "Y": {"projections": [PM(J, "Total Spend")]}}},
               {**axes(val_units=0), **labels(True, 8.5, INK, precision=0, units=1),
                **legend(False),
                "sentimentColors": [{"properties": {
                    "increaseFill": col(PRIMARY), "decreaseFill": col(TEAL),
                    "totalFill": col(INK)}}]},
               card("Weekly spend pacing — front-loaded, then a month-end spike"), zi=2),

        visual(nm(k + ":v3"), "tableEx", V3,
               {"queryState": {"Values": {"projections": [
                   PC(D, "Week"), PM(J, "Total Spend"), PM(J, "Total Clicks"),
                   PM(J, "Total Applies"), PM(J, "CPC"), PM(J, "CPA")]}},
                "sortDefinition": sort_by(fld_col(D, "Week"), "Ascending")},
               {"grid": [{"properties": {"gridVertical": lit(False),
                                         "outlineColor": col(BORDER), "textSize": lit(9.0)}}],
                "columnHeaders": [{"properties": {"fontColor": col("#FFFFFF"),
                                                  "backColor": col(ALERT),
                                                  "bold": lit(True), "fontSize": lit(9.0)}}],
                "values": [{"properties": {"fontSize": lit(9.0), "fontColor": col(INK)}}]},
               card("Weekly scorecard — the cheapest week got the least money"), zi=3),

        summary(k, "What these three visuals say", [
            "Cost per click by day: a step change on 17 January — CPC averaged $0.46 across 1–16 January "
            "and $0.16 for the remainder of the month.",
            "Weekly spend pacing: the budget was front-loaded. $32,804 (69%) went out in the first 16 days "
            "at $4.95 per application, and a single day — 31 January — absorbed $4,832 (10.2%) at $6.88.",
            "Weekly scorecard: the cheapest week (week of 21 January, $1.76 per application) received the "
            "smallest share of budget at 11%, while the two most expensive weeks took 55% between them.",
        ], "Why this matters to Metro Staffing:  ",
           "pacing was driven by the calendar rather than by price. Holding budget back for low-CPC windows "
           "and capping any single day's share would have bought materially more applications from the "
           "identical $47,543 — no new money, only better timing."),
    ]
    pages.append(page(k, "KPI 3 · Spend Pacing", vis))

    # ============================================================ KPI 4 (bonus)
    k = "kpi4"
    vis = [
        header(k, "KPI 4  ·  STATE × CITY × COST PER APPLICATION   (bonus analysis)",
               "Location Efficiency: a 3.6x cost spread across funded states",
               "Filtered to the United States, which carries 85% of Metro Staffing's January spend"),
        slicer(k, J, "Category", "Filter by job category"),

        visual(nm(k + ":v1"), "clusteredBarChart", V1,
               {"queryState": {
                   "Category": {"projections": [PC(J, "State", active=True)]},
                   "Y": {"projections": [PM(J, "Total Spend")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Spend"))},
               {**fill(PLUM), **axes(val_units=0),
                **labels(True, 8.5, INK, precision=0, units=1), **legend(False)},
               card("Ad spend by state"), zi=1),

        visual(nm(k + ":v2"), "treemap", V2,
               {"queryState": {
                   "Group": {"projections": [PC(J, "City", active=True)]},
                   "Values": {"projections": [PM(J, "Total Applies")]}}},
               {**labels(True, 9.0, "#FFFFFF", precision=0, units=1), **legend(False)},
               card("Where the applications actually came from — by city"), zi=2),

        visual(nm(k + ":v3"), "tableEx", V3,
               {"queryState": {"Values": {"projections": [
                   PC(J, "State"), PM(J, "Jobs Advertised"), PM(J, "Total Spend"),
                   PM(J, "Total Applies"), PM(J, "Apply Rate"), PM(J, "CPA")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Spend"))},
               {"grid": [{"properties": {"gridVertical": lit(False),
                                         "outlineColor": col(BORDER), "textSize": lit(9.0)}}],
                "columnHeaders": [{"properties": {"fontColor": col("#FFFFFF"),
                                                  "backColor": col(PLUM),
                                                  "bold": lit(True), "fontSize": lit(9.0)}}],
                "values": [{"properties": {"fontSize": lit(9.0), "fontColor": col(INK)}}]},
               card("State scorecard — biggest budgets first, with what each application cost"), zi=3),

        summary(k, "What these three visuals say", [
            "Ad spend by state: California absorbed the most budget at $5,376, ahead of Georgia ($4,690) "
            "and Florida ($4,673).",
            "Applications by city: the volume came from a different set of places — Alpharetta GA (1,187), "
            "Maitland FL (1,165) and Augusta GA (950) led the month.",
            "State scorecard: across the ten states funded above $1,000, cost per application runs from "
            "$1.93 in New Jersey and $2.11 in Georgia up to $6.24 in Kentucky and $6.99 in New York — a "
            "3.6x spread.",
        ], "Why this matters to Metro Staffing:  ",
           "California and New York together took $8,373 and returned 1,448 applications, while Georgia and "
           "New Jersey took $7,637 and returned 3,748. Shifting budget toward the low-cost metros — where "
           "requisitions allow — is the third reallocation lever alongside vendor and timing."),
    ]
    pages.append(page(k, "KPI 4 · Location Efficiency", vis,
                      filter_in(J, "Country", ["US"], "kpi4:usfilter")))

    # ============================================================ EXEC SUMMARY
    k = "exec"
    vis = [
        header(k, "EXECUTIVE SUMMARY  ·  OUT-OF-THE-BOX ANALYTICS INC.",
               "Metro Staffing spent $47,543 in January and left ~4,287 applications on the table",
               "One visual carried forward from each KPI analysis  ·  benchmark cost per application $2.77 (Awesome Jobs)"),

        visual(nm(k + ":v1"), "clusteredBarChart", V1,
               {"queryState": {
                   "Category": {"projections": [PC(J, "Vendors", active=True)]},
                   "Y": {"projections": [PM(J, "Total Spend")]}},
                "sortDefinition": sort_by(fld_mea(J, "Total Spend"))},
               {**fill(PRIMARY), **axes(val_units=0),
                **labels(True, 9.0, INK, precision=0, units=1), **legend(False)},
               card("From KPI 1 — ad spend by vendor (the allocation problem)"), zi=1),

        visual(nm(k + ":v2"), "treemap", V2,
               {"queryState": {
                   "Group": {"projections": [PC(J, "Category", active=True)]},
                   "Values": {"projections": [PM(J, "Total Spend")]}}},
               {**labels(True, 9.0, "#FFFFFF", precision=0, units=1), **legend(False)},
               card("From KPI 2 — spend concentration by category (where to apply bid caps)"), zi=2),

        visual(nm(k + ":v3"), "lineChart", V3,
               {"queryState": {
                   "Category": {"projections": [PC(D, "Date", active=True)]},
                   "Y": {"projections": [PM(J, "CPC")]}}},
               {"lineStyles": [{"properties": {"strokeWidth": lit(2), "lineColor": col(ALERT),
                                               "showMarker": lit(False), "areaShow": lit(False)}}],
                **axes(val_title="Cost per click"), **labels(False), **legend(False)},
               card("From KPI 3 — cost per click by day (the price signal to bid against)"), zi=3),

        summary(k, "Recommended next step: spend-response modelling with constrained optimisation", [
            "Fit a diminishing-returns curve per vendor from the daily spend → clicks → applications "
            "observations in this export, then feed those curves to an optimiser that reallocates the "
            "budget to minimise blended cost per application subject to each vendor's volume ceiling.",
            "The data supports it: every row carries date, vendor, category, location, spend, clicks and "
            "applications — 31 daily observations per vendor, enough to find where returns flatten rather "
            "than assuming the $2.77 benchmark holds at four times the volume.",
            "Each visual here feeds one input: vendor spend sets the decision variables, category "
            "concentration sets the constraints, daily cost per click supplies the price curve.",
        ], "Data-integrity note:  ",
           "3,578 applications (21.7% of the January total) arrived on placeholder \"Unknown Jobs\" rows "
           "with zero clicks and zero spend, and are excluded from every visual in this workbook. "
           "Repairing that tracking template is the prerequisite second step.", size=9.0),
    ]
    pages.append(page(k, "Executive Summary", vis))

    # ============================================================ write pages
    order = []
    for pj, vlist in pages:
        pdir = os.path.join(dfn, "pages", pj["name"])
        os.makedirs(os.path.join(pdir, "visuals"), exist_ok=True)
        w(os.path.join(pdir, "page.json"), pj)
        for v in vlist:
            vdir = os.path.join(pdir, "visuals", v["name"])
            os.makedirs(vdir, exist_ok=True)
            w(os.path.join(vdir, "visual.json"), v)
        order.append(pj["name"])

    w(os.path.join(dfn, "pages", "pages.json"),
      {"$schema": SCH_PGS, "pageOrder": order, "activePageName": order[0]})

    return rp, sum(len(v) for _, v in pages), len(pages)
