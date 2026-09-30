"""Vensim Scenario Viewer (Streamlit)

Upload a Vensim .mdl file -> parse variables / SFD views -> run the base model with
pysd -> pick a view -> edit equations/values in that view -> run as a new scenario
-> compare scenarios against each other (and delete the ones you don't want)
-> export everything to a local Excel file.

Run:  streamlit run app.py
"""
import datetime as dt
import io
import re
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

OUTPUT_DIR = Path("outputs")
SEP = "*" * 56  # Vensim section separator
NUM_RE = re.compile(r"^[-+]?\d+(\.\d+)?([eE][-+]?\d+)?$")
ILLEGAL_XLSX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
ILLEGAL_SHEET = re.compile(r"[\[\]:*?/\\]")  # characters Excel forbids in sheet names
ALL_VIEWS = "(All variables)"
S = st.session_state


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------
def classify(value: str) -> str:
    v = value.strip()
    if NUM_RE.match(v):
        return "constant"
    if v.upper().startswith("INTEG"):
        return "stock"
    return "auxiliary"


def parse_variables(text: str) -> pd.DataFrame:
    """One row per variable: name, equation, units, comment, kind, has_eq."""
    head = text.split(SEP)[0].replace("{UTF-8}", " ")
    head = head.replace("\\\n", " ").replace("\\", "")
    head = re.sub(r"\s+", " ", head)

    rows = []
    for chunk in head.split("|")[:-1]:
        parts = chunk.split("~")
        eq = parts[0].strip()
        if not eq:
            continue
        has_eq = "=" in eq
        if has_eq:
            name, _, value = eq.partition("=")
        else:  # lookups / subscript definitions have no '='
            name, value = eq.split("(")[0], eq
        name = name.strip().strip('"')
        value = value.strip()
        rows.append(
            {
                "name": name,
                "equation": value,
                "units": parts[1].strip() if len(parts) > 1 else "",
                "comment": parts[2].strip() if len(parts) > 2 else "",
                "kind": classify(value),
                "has_eq": has_eq,
            }
        )
    return pd.DataFrame(rows, columns=["name", "equation", "units", "comment", "kind", "has_eq"])


def parse_sfd(text: str) -> pd.DataFrame:
    """(sfd_name, variable) pairs from the sketch section."""
    if SEP not in text:
        return pd.DataFrame(columns=["sfd_name", "variable"])
    blocks = text.split(SEP)[-1].split("*")
    blocks[-1] = blocks[-1].split("///---\\\n")[0]

    rows = []
    for block in blocks:
        lines = block.split("\n")
        sfd_name = lines[0].strip()
        if not sfd_name or sfd_name.startswith("~"):
            continue
        for line in lines:
            if not line.startswith("10,"):
                continue
            fields = line.split(",")
            if len(fields) < 3:
                continue
            var = fields[2].strip().strip('"')
            if var and var[0].isalpha():
                rows.append({"sfd_name": sfd_name, "variable": var})
    return pd.DataFrame(rows, columns=["sfd_name", "variable"]).drop_duplicates()


def apply_overrides(text: str, overrides: dict) -> str:
    """Return a copy of the .mdl text with the given {variable: new equation} applied."""
    if not overrides:
        return text
    idx = text.find(SEP)
    head, tail = (text[:idx], text[idx:]) if idx >= 0 else (text, "")
    chunks = head.split("|")
    out = []
    for i, chunk in enumerate(chunks):
        if i < len(chunks) - 1:
            parts = chunk.split("~")
            raw_head = parts[0].replace("{UTF-8}", "")
            if "=" in raw_head:
                # exact name as written in the file (spacing untouched, so other
                # equations that reference it still match)
                raw_name = raw_head.partition("=")[0].strip()
                key = re.sub(r"\s+", " ", raw_name.replace("\\\n", " ")).strip().strip('"')
                if key in overrides:
                    units = parts[1].strip() if len(parts) > 1 else ""
                    comment = "~".join(parts[2:]).strip() if len(parts) > 2 else ""
                    # same layout as Vensim writes / model-export.py produces
                    block = f"\n\n{raw_name}=\n\t{overrides[key]}\n\t~\t{units}\n\t~\t{comment}\t"
                    chunk = ("{UTF-8}" + block[1:]) if "{UTF-8}" in parts[0] else block
        out.append(chunk)
    result = "|".join(out) + tail
    if "\r\n" in text:  # keep the original line-ending style
        result = result.replace("\r\n", "\n").replace("\n", "\r\n")
    return result


def validate_mdl(orig: str, new: str, overrides: dict):
    """Raise ValueError if the rewritten model isn't structurally the same model + edits."""
    before, after = parse_variables(orig), parse_variables(new)
    if before["name"].tolist() != after["name"].tolist():
        raise ValueError("variable list changed while rewriting the model")
    got = dict(zip(after["name"], after["equation"]))
    for k, v in overrides.items():
        if re.sub(r"\s+", " ", v).strip() != got.get(k):
            raise ValueError(f"edit for '{k}' was not written correctly")
        if v.count("(") != v.count(")"):
            raise ValueError(f"unbalanced parentheses in the equation for '{k}'")


def view_variables(model: dict, view: str) -> pd.DataFrame:
    variables, sfd = model["variables"], model["sfd_vars"]
    if view == ALL_VIEWS:
        return variables
    members = set(sfd.loc[sfd["sfd_name"] == view, "variable"].str.lower())
    return variables[variables["name"].str.lower().isin(members)]


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------
def _try(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def run_model(text: str):
    """Translate + run the model with pysd. Returns (results_df, meta_dict)."""
    import pysd  # lazy import so the UI loads even if pysd is missing

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.mdl"
        path.write_text(text, encoding="utf-8")
        model = pysd.read_vensim(str(path))
        res = model.run()
        meta = {
            "initial_time": _try(lambda: model.components.initial_time(), res.index.min()),
            "final_time": _try(lambda: model.components.final_time(), res.index.max()),
            "time_step": _try(lambda: model.components.time_step()),
        }
    res = res.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    res.index.name = "Node Point"
    return res, meta


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    s = results.agg(["min", "max", "mean", "std"]).T
    s["first"] = results.iloc[0]
    s["last"] = results.iloc[-1]
    s.index.name = "variable"
    return s.reset_index()


# --------------------------------------------------------------------------
# Scenario state
# --------------------------------------------------------------------------
def add_scenario(name: str, overrides: dict, results, meta):
    taken = {s["name"] for s in S["scenarios"]}
    final, n = name, 2
    while final in taken:
        final, n = f"{name} ({n})", n + 1
    S["scenarios"].append(
        {
            "id": S["next_id"],
            "name": final,
            "overrides": dict(overrides),
            "results": results,
            "meta": meta,
            "created": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    S["next_id"] += 1


def init_model(uploaded, name: str):
    raw = uploaded.getvalue()
    for encoding in ("utf-8", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        encoding, text = "utf-8", raw.decode("utf-8", errors="replace")
    variables, sfd_vars = parse_variables(text), parse_sfd(text)
    results, meta = run_model(text)
    S["model"] = {
        "name": name or Path(uploaded.name).stem,
        "text": text,
        "encoding": encoding,
        "variables": variables,
        "sfd_vars": sfd_vars,
        "source_eq": dict(zip(variables["name"], variables["equation"])),
    }
    S.update(scenarios=[], draft={}, next_id=0, ver=0, seed_sig=None)
    add_scenario("Base", {}, results, meta)


def delete_scenario(sid: int):
    S["scenarios"] = [s for s in S["scenarios"] if s["id"] != sid]


def load_into_editor(sid: int):
    sc = next(s for s in S["scenarios"] if s["id"] == sid)
    S["draft"] = dict(sc["overrides"])
    S["ver"] += 1


def clear_draft():
    S["draft"] = {}
    S["ver"] += 1


def on_edit():
    """data_editor callback: fold the edits of the visible rows into the draft."""
    seed, src = S["seed_df"], S["model"]["source_eq"]
    edited = S[S["ekey"]].get("edited_rows", {})
    for pos, name in enumerate(seed["name"]):
        new = str(edited.get(pos, {}).get("equation", seed.iloc[pos]["equation"])).strip()
        if not new or new == src[name]:
            S["draft"].pop(name, None)
        else:
            S["draft"][name] = new


def run_scenario(scen_name: str):
    overrides = dict(S["draft"])
    if not overrides:
        st.warning("No edits yet - change at least one equation/value first.")
        return
    bad = [k for k, v in overrides.items() if "|" in v or "~" in v]
    if bad:
        st.error(f"Equations cannot contain '|' or '~' (check: {', '.join(bad)}).")
        return
    try:
        with st.spinner("Running scenario with pysd..."):
            text = apply_overrides(S["model"]["text"], overrides)
            results, meta = run_model(text)
        add_scenario(scen_name.strip() or "Scenario", overrides, results, meta)
        st.success("Scenario finished - see the 'Charts & compare' tab.")
    except Exception as e:  # noqa: BLE001
        st.error(f"Simulation failed (your edit may not be a valid Vensim equation): {e}")


# --------------------------------------------------------------------------
# Excel export
# --------------------------------------------------------------------------
def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).map(lambda s: ILLEGAL_XLSX.sub("", s)[:32000])
    return df


def export_excel():
    m = S["model"]
    OUTPUT_DIR.mkdir(exist_ok=True)
    safe = re.sub(r"[^\w\-]+", "_", m["name"]) or "model"
    path = OUTPUT_DIR / f"{safe}_{dt.datetime.now():%Y%m%d_%H%M%S}.xlsx"

    meta_df = pd.DataFrame(
        [
            {
                "scenario": s["name"],
                "created": s["created"],
                "n_edits": len(s["overrides"]),
                "initial_time": s["meta"]["initial_time"],
                "final_time": s["meta"]["final_time"],
                "time_step": s["meta"]["time_step"],
                "n_steps": len(s["results"]),
            }
            for s in S["scenarios"]
        ]
    ).astype(str)
    edits_df = pd.DataFrame(
        [
            {"scenario": s["name"], "variable": k, "original": m["source_eq"].get(k, ""), "new": v}
            for s in S["scenarios"]
            for k, v in s["overrides"].items()
        ],
        columns=["scenario", "variable", "original", "new"],
    )

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        meta_df.to_excel(xw, sheet_name="scenarios", index=False)
        edits_df.to_excel(xw, sheet_name="edits", index=False)
        _clean(m["variables"]).to_excel(xw, sheet_name="variables", index=False)
        _clean(m["sfd_vars"]).to_excel(xw, sheet_name="sfd_variable", index=False)
        for i, s in enumerate(S["scenarios"]):
            safe_name = ILLEGAL_SHEET.sub("_", s["name"])
            sheet = f"{i}_{safe_name}"[:31]
            s["results"].reset_index().to_excel(xw, sheet_name=sheet, index=False)
    data = buf.getvalue()
    path.write_bytes(data)
    return path, data


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
def tab_edit(view_vars: pd.DataFrame, view: str):
    st.markdown(
        "Edit the **equation / value** column for any variable in this view, then run. "
        "Edits are remembered when you switch views, so you can change several views "
        "before running one scenario."
    )
    f1, f2 = st.columns([2, 3])
    kinds = f1.multiselect("Type", ["constant", "stock", "auxiliary"], default=["constant", "stock", "auxiliary"])
    query = f2.text_input("Search name or equation")

    editable = view_vars[view_vars["has_eq"] & view_vars["kind"].isin(kinds)]
    if query:
        q = query.lower()
        editable = editable[
            editable["name"].str.lower().str.contains(q, regex=False)
            | editable["equation"].str.lower().str.contains(q, regex=False)
        ]

    sig = (view, tuple(kinds), query, S["ver"])
    if S.get("seed_sig") != sig:  # (re)build the table, overlaying pending edits
        seed = editable[["name", "kind", "units", "equation"]].copy().reset_index(drop=True)
        seed["equation"] = [S["draft"].get(n, e) for n, e in zip(seed["name"], seed["equation"])]
        S["seed_df"], S["seed_sig"], S["ekey"] = seed, sig, f"editor_{abs(hash(sig))}"

    if S["seed_df"].empty:
        st.info("No editable variables match in this view.")
    else:
        st.data_editor(
            S["seed_df"],
            key=S["ekey"],
            on_change=on_edit,
            hide_index=True,
            use_container_width=True,
            disabled=["name", "kind", "units"],
            column_config={"equation": st.column_config.TextColumn("equation / value (editable)", width="large")},
        )

    st.subheader("Pending edits")
    src = S["model"]["source_eq"]
    if S["draft"]:
        st.dataframe(
            pd.DataFrame([{"variable": k, "original": src.get(k, ""), "new": v} for k, v in S["draft"].items()]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("None yet.")

    c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="bottom")
    scen_name = c1.text_input("Scenario name", value=f"Scenario {len(S['scenarios'])}")
    if c2.button("Run scenario", type="primary", disabled=not S["draft"], use_container_width=True):
        run_scenario(scen_name)
    c3.button("Clear edits", on_click=clear_draft, disabled=not S["draft"], use_container_width=True)


def tab_charts(view_vars: pd.DataFrame, view: str):
    scenarios = S["scenarios"]
    names = [s["name"] for s in scenarios]
    chosen_names = st.multiselect("Scenarios to show", names, default=names)
    chosen = [s for s in scenarios if s["name"] in chosen_names]
    base = scenarios[0]

    cols = base["results"].columns
    avail = [c for c in cols if view == ALL_VIEWS or c in set(view_vars["name"])]
    if not avail:
        st.info("None of this view's variables have simulation output.")
        return
    varying = [c for c in avail if base["results"][c].std() > 0]
    selected = st.multiselect("Variable(s)", avail, default=(varying or avail)[:1])
    if not selected or not chosen:
        st.info("Pick at least one variable and one scenario.")
        return

    for var in selected:
        data = pd.concat({s["name"]: s["results"][var] for s in chosen if var in s["results"].columns}, axis=1)
        st.markdown(f"**{var}**")
        st.line_chart(data)

    st.subheader("Difference vs Base (last time step)")
    rows = []
    for var in selected:
        b = base["results"][var].iloc[-1] if var in base["results"].columns else None
        for s in chosen:
            if s["id"] == base["id"] or var not in s["results"].columns or b is None:
                continue
            v = s["results"][var].iloc[-1]
            rows.append(
                {
                    "variable": var,
                    "scenario": s["name"],
                    "base": b,
                    "scenario value": v,
                    "delta": v - b,
                    "delta %": (v - b) / abs(b) * 100 if b else None,
                }
            )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("Run at least one scenario to see differences.")


def tab_scenarios():
    src = S["model"]["source_eq"]
    for s in S["scenarios"]:
        is_base = s["id"] == S["scenarios"][0]["id"]
        with st.expander(f"{s['name']}  ·  {len(s['overrides'])} edit(s)  ·  {s['created']}", expanded=False):
            if s["overrides"]:
                st.dataframe(
                    pd.DataFrame(
                        [{"variable": k, "original": src.get(k, ""), "new": v} for k, v in s["overrides"].items()]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("Original model, no edits.")
            b1, b2, _ = st.columns([1, 1, 4])
            b1.button("Load edits", key=f"load_{s['id']}", on_click=load_into_editor, args=(s["id"],),
                      help="Copy this scenario's edits into the editor as a starting point")
            b2.button("Delete", key=f"del_{s['id']}", on_click=delete_scenario, args=(s["id"],),
                      disabled=is_base, help="The Base scenario can't be deleted" if is_base else None)


def tab_stats(view_vars: pd.DataFrame, view: str):
    names = [s["name"] for s in S["scenarios"]]
    pick = st.selectbox("Scenario", names)
    res = next(s for s in S["scenarios"] if s["name"] == pick)["results"]
    if view != ALL_VIEWS:
        res = res[[c for c in res.columns if c in set(view_vars["name"])]]
    st.dataframe(summarize(res), use_container_width=True, hide_index=True)


def scenario_mdl(s: dict) -> bytes:
    """The original .mdl with this scenario's edits applied (Base = unchanged)."""
    m = S["model"]
    new = apply_overrides(m["text"], s["overrides"])
    if s["overrides"]:
        validate_mdl(m["text"], new, s["overrides"])
    return new.encode(m.get("encoding", "utf-8"), errors="replace")


def _file_stem(*parts: str) -> str:
    return re.sub(r"[^\w\-]+", "_", "_".join(parts)).strip("_") or "model"


def tab_export():
    m = S["model"]

    st.subheader("Export data (Excel)")
    st.caption("Sheets: scenarios, edits, variables, sfd_variable + one sheet of results per scenario.")
    if st.button("Save all scenarios to Excel"):
        path, data = export_excel()
        S["export"] = (str(path), data)
    if "export" in S:
        path, data = S["export"]
        st.success(f"Saved to `{path}`")
        st.download_button(
            "Download Excel",
            data=data,
            file_name=Path(path).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.divider()
    st.subheader("Export model (.mdl)")
    st.caption(
        "Downloads the Vensim model with the scenario's edited equations applied, "
        "so you can open and run it directly in Vensim."
    )
    built = {}
    for s in S["scenarios"]:
        try:
            built[s["id"]] = scenario_mdl(s)
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not build .mdl for '{s['name']}': {e}")
    ok = [s for s in S["scenarios"] if s["id"] in built]
    if not ok:
        return

    pick = st.selectbox("Scenario", [s["name"] for s in ok], key="mdl_pick")
    sc = next(s for s in ok if s["name"] == pick)
    st.download_button(
        "Download .mdl",
        data=built[sc["id"]],
        file_name=f"{_file_stem(m['name'], sc['name'])}.mdl",
        mime="application/octet-stream",
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for s in ok:
            zf.writestr(f"{_file_stem(m['name'], s['name'])}.mdl", built[s["id"]])
    st.download_button(
        f"Download all {len(ok)} scenario(s) as .zip",
        data=buf.getvalue(),
        file_name=f"{_file_stem(m['name'])}_scenarios.zip",
        mime="application/zip",
    )


def render():
    m = S["model"]
    views = sorted(m["sfd_vars"]["sfd_name"].unique()) if not m["sfd_vars"].empty else []
    view = st.selectbox("Active view", [ALL_VIEWS] + views, help="Pick the SFD view you want to work on")
    view_vars = view_variables(m, view)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Variables in view", len(view_vars))
    c2.metric("Editable", int(view_vars["has_eq"].sum()))
    c3.metric("Scenarios", len(S["scenarios"]))
    c4.metric("Pending edits", len(S["draft"]))

    t_edit, t_chart, t_scen, t_stats, t_export = st.tabs(
        ["Edit & run", "Charts & compare", "Scenarios", "Summary stats", "Export"]
    )
    with t_edit:
        tab_edit(view_vars, view)
    with t_chart:
        tab_charts(view_vars, view)
    with t_scen:
        tab_scenarios()
    with t_stats:
        tab_stats(view_vars, view)
    with t_export:
        tab_export()


def main():
    st.set_page_config(page_title="Vensim Scenario Viewer", layout="wide")
    st.title("Scenario Model")
    st.caption("Upload a Vensim .mdl file, edit variables per view, run scenarios and compare them.")

    with st.sidebar:
        uploaded = st.file_uploader("Vensim model (.mdl)", type=["mdl"])
        model_name = st.text_input("Model name", value=Path(uploaded.name).stem if uploaded else "")
        run = st.button("Parse & run base model", type="primary", disabled=uploaded is None)
        if "model" in S:
            st.caption("Re-running resets all scenarios and pending edits.")

    if run and uploaded is not None:
        try:
            with st.spinner("Parsing and running base model..."):
                init_model(uploaded, model_name)
        except Exception as e:  # noqa: BLE001
            S.pop("model", None)
            st.error(f"Failed to process model: {e}")

    if "model" in S:
        render()
    else:
        st.info("Upload a .mdl file in the sidebar and click **Parse & run base model**.")


main()