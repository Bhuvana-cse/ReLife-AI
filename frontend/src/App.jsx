import { Component, lazy, Suspense, useEffect, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, BookOpenCheck, Boxes,
  Check, ChevronDown, CircleHelp, ClipboardList, Clock3, Compass, Cpu,
  FileChartColumn, Globe, HeartHandshake, Leaf, LogOut, Mail, MapPin, Menu, PackageCheck,
  Phone, Recycle, Search, Settings2, ShieldCheck, Sparkles, Wrench, X,
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { api } from "./services/api";
import { EmptyState, ErrorState, Loading, Logo, PageHeading, QuickAction, StatCard, capitalize } from "./components/UI.jsx";
import AuthPage from "./pages/AuthPage.jsx";

const RecoveryChart = lazy(() => import("./components/Charts.jsx").then((module) => ({ default: module.RecoveryChart })));
const ActivityChart = lazy(() => import("./components/Charts.jsx").then((module) => ({ default: module.ActivityChart })));
const ScenarioCostChart = lazy(() => import("./components/Charts.jsx").then((module) => ({ default: module.ScenarioCostChart })));

const sections = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3, group: "OVERVIEW" },
  { id: "analyze", label: "Analyze product", icon: Sparkles, group: "YOUR WORKSPACE" },
  { id: "history", label: "My history", icon: Clock3, group: "YOUR WORKSPACE" },
  { id: "centers", label: "Recovery centers", icon: Compass, group: "YOUR WORKSPACE" },
  { id: "passport", label: "Afterlife passport", icon: BookOpenCheck, group: "CIRCULAR TOOLS" },
  { id: "matching", label: "Need matching", icon: HeartHandshake, group: "CIRCULAR TOOLS" },
  { id: "salvage", label: "Salvage intelligence", icon: Boxes, group: "CIRCULAR TOOLS" },
  { id: "simulator", label: "Future-life simulator", icon: Activity, group: "CIRCULAR TOOLS" },
  { id: "rescue", label: "Rescue chain", icon: PackageCheck, group: "CIRCULAR TOOLS" },
  { id: "impact", label: "Impact report", icon: FileChartColumn, group: "ACCOUNT" },
  { id: "profile", label: "Profile", icon: Settings2, group: "ACCOUNT" },
];

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(localStorage.getItem("relife-token")));
  const [page, setPage] = useState("dashboard");
  const [notice, setNotice] = useState("");
  const [passportProductId, setPassportProductId] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("relife-token")) return;
    api.me().then(setUser).catch(() => localStorage.removeItem("relife-token")).finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    const publicId = new URLSearchParams(window.location.search).get("passport");
    if (!user || !publicId) return;
    api.passportByPublicId(publicId).then((passport) => {
      setPassportProductId(String(passport.product_id));
      setPage("passport");
    }).catch((error) => setNotice(error.message));
  }, [user]);

  function signOut() {
    localStorage.removeItem("relife-token");
    setUser(null);
    setPage("dashboard");
  }

  if (booting) return <div className="screen-loader"><div className="spinner" />Restoring your workspace…</div>;
  if (!user) return <AuthPage onSuccess={(result) => { localStorage.setItem("relife-token", result.token); setUser(result.user); }} />;

  return (
    <div className="app-shell">
      <Sidebar page={page} setPage={setPage} user={user} onLogout={signOut} />
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><ArrowRight size={14} /><strong>{sections.find((item) => item.id === page)?.label}</strong></div>
          <div className="top-actions"><span className="status-pill"><span /> Circular living, made practical</span><button className="avatar" onClick={() => setPage("profile")} aria-label="Open profile">{user.name?.slice(0, 1).toUpperCase()}</button></div>
        </header>
        {notice && <div className="toast"><Check size={16} />{notice}<button onClick={() => setNotice("")} aria-label="Dismiss"><X size={15} /></button></div>}
        <PageErrorBoundary key={page}><div className="page-wrap">
          {page === "dashboard" && <Dashboard setPage={setPage} />}
          {page === "analyze" && <Analyze setPage={setPage} setNotice={setNotice} />}
          {page === "history" && <HistoryPage setPage={setPage} />}
          {page === "centers" && <CentersPage />}
          {page === "passport" && <PassportPage setPage={setPage} initialProductId={passportProductId} />}
          {page === "matching" && <MatchingPage />}
          {page === "salvage" && <SalvagePage />}
          {page === "simulator" && <SimulatorPage />}
          {page === "rescue" && <RescuePage setNotice={setNotice} />}
          {page === "impact" && <ImpactPage />}
          {page === "profile" && <ProfilePage user={user} onLogout={signOut} />}
        </div></PageErrorBoundary>
      </main>
    </div>
  );
}

class PageErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("Page render failed:", error);
  }

  render() {
    if (this.state.hasError) {
      return <div className="page-wrap"><section className="panel render-error-panel" role="alert">
        <h2>This page could not display its results.</h2>
        <p>Your saved data is still in your account. Return to the form and try again, or reload this page.</p>
        <button className="button button-primary" onClick={() => window.location.reload()}>Reload ReLife</button>
      </section></div>;
    }
    return this.props.children;
  }
}

function Sidebar({ page, setPage, user, onLogout }) {
  const [open, setOpen] = useState(false);
  let group = "";
  return <>
    <button className="mobile-menu" onClick={() => setOpen(!open)} aria-label="Toggle menu"><Menu size={21} /></button>
    {open && <button className="mobile-scrim" onClick={() => setOpen(false)} aria-label="Close menu" />}
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
      <div className="sidebar-brand"><Logo /></div><div className="workspace-switch"><span className="workspace-dot">R</span><span><b>Student workspace</b><small>Personal account</small></span><ChevronDown size={16} /></div>
      <nav>{sections.map((item) => { const showGroup = group !== item.group; group = item.group; return <div key={item.id}>{showGroup && <div className="nav-group">{item.group}</div>}<button className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => { setPage(item.id); setOpen(false); }}><item.icon size={18} /><span>{item.label}</span>{item.id === "analyze" && <span className="nav-new">NEW</span>}</button></div>; })}</nav>
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><CircleHelp size={17} /></div><b>Need a little help?</b><p>Explore a recovery path, one step at a time.</p><button onClick={() => setPage("analyze")}>Start an analysis <ArrowRight size={14} /></button></div>
        <div className="sidebar-profile"><div className="profile-avatar">{user.name?.slice(0, 1).toUpperCase()}</div><div className="profile-label"><b>{user.name}</b><small>{user.email}</small></div><button className="icon-button" onClick={onLogout} aria-label="Log out"><LogOut size={17} /></button></div>
      </div>
    </aside>
  </>;
}

function Dashboard({ setPage }) {
  const [data, setData] = useState(null); const [error, setError] = useState("");
  const load = () => { setError(""); Promise.all([api.history(), api.impact()]).then(([history, impact]) => setData({ history, impact })).catch((e) => setError(e.message)); };
  useEffect(load, []);
  if (error) return <ErrorState error={error} retry={load} />;
  if (!data) return <Loading />;
  const history = data.history;
  const counts = ["repair", "resale", "donation", "reuse", "component salvage", "recycling"].map((action) => ({ action: action.replace("component salvage", "salvage"), count: history.filter((item) => item.recommendation === action).length }));
  const recent = history.slice(0, 4);
  return <>
    <PageHeading eyebrow="YOUR CIRCULAR OVERVIEW" title="Your recovery, at a glance." description="A little care goes a long way. Here's what's happening in your recovery journey." action={<button className="button button-primary" onClick={() => setPage("analyze")}><Sparkles size={16} /> Analyze a product</button>} />
    <div className="welcome-strip"><div className="welcome-illustration"><Leaf size={23} /></div><div><b>Make room for a better next chapter.</b><span>Explore practical, data-informed ways to repair, reuse, or recover the things you own.</span></div><button className="icon-button" onClick={() => setPage("simulator")}><ArrowRight size={18} /></button></div>
    <div className="stats-grid">
      <StatCard icon={ClipboardList} label="Products assessed" value={history.length} foot="Your saved product analyses" color="green" />
      <StatCard icon={Wrench} label="Repair-first choices" value={history.filter((item) => item.recommendation === "repair").length} foot="Based on your submitted details" color="blue" />
      <StatCard icon={HeartHandshake} label="Passports created" value={history.length} foot="Ownership history is user-submitted" color="peach" />
      <StatCard icon={Leaf} label="Impact totals" value="—" foot="Estimates not yet measured" color="lavender" />
    </div>
    <div className="dashboard-grid">
      <section className="panel chart-panel"><div className="panel-heading"><div><span className="section-kicker">YOUR ACTIVITY</span><h2>Recovery pathways</h2></div><span className="subtle-tag">All time</span></div>
        <div className="chart-area">{history.length ? <Suspense fallback={<div className="chart-empty">Loading chart…</div>}><RecoveryChart data={counts} /></Suspense> : <div className="chart-empty">Your recovery pathway chart will appear after your first analysis.</div>}</div>
      </section>
      <section className="panel action-panel"><div className="panel-heading"><div><span className="section-kicker">QUICK ACTIONS</span><h2>Where to next?</h2></div></div>
        <QuickAction icon={Sparkles} title="Understand an item" text="Get a recommendation" onClick={() => setPage("analyze")} /><QuickAction icon={Activity} title="Compare scenarios" text="Try the future-life simulator" onClick={() => setPage("simulator")} /><QuickAction icon={Compass} title="Find a next step" text="Browse sample recovery centers" onClick={() => setPage("centers")} />
      </section>
    </div>
    <section className="panel recent-panel"><div className="panel-heading"><div><span className="section-kicker">RECENT ACTIVITY</span><h2>Your latest assessments</h2></div><button className="text-button" onClick={() => setPage("history")}>View all <ArrowRight size={14} /></button></div>
      {recent.length ? <div className="recent-list">{recent.map((item) => <button key={item.id} className="recent-row" onClick={() => setPage("passport")}><div className="recent-product-icon"><PackageCheck size={18} /></div><span className="recent-title"><b>{capitalize(item.category)}</b><small>{new Date(item.created_at).toLocaleDateString()} · {item.condition} condition</small></span><span className="recommendation-badge">{item.recommendation}</span><ArrowRight size={16} /></button>)}</div> : <EmptyState title="Your journey starts here" text="Add a product to get a recovery recommendation and create its afterlife passport." action={<button className="button button-primary" onClick={() => setPage("analyze")}>Analyze your first product</button>} />}
    </section>
    <div className="fine-print"><ShieldCheck size={14} /> Advice is based on user-reported details and rule-based demo logic — not a professional inspection.</div>
  </>;
}

function Analyze({ setPage, setNotice }) {
  const [form, setForm] = useState({ category: "electronics", product_name: "Laptop", age_years: "2", useful_life_years: "2", condition: "good", location: "", visible_damage: "", repair_cost: "", resale_value: "" });
  const [image, setImage] = useState(null); const [imagePreview, setImagePreview] = useState(""); const [dragging, setDragging] = useState(false); const [result, setResult] = useState(null); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  const [productId, setProductId] = useState("");
  useEffect(() => {
    if (!image) { setImagePreview(""); return undefined; }
    const url = URL.createObjectURL(image);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  function chooseImage(file) {
    setError("");
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setImage(null);
      setError("Choose a JPG, PNG, or WebP product photo.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setImage(null);
      setError("Choose an image smaller than 5 MB.");
      return;
    }
    setImage(file);
  }
  const change = (key, value) => setForm({ ...form, [key]: value });
  async function submit(e) {
    e.preventDefault(); setLoading(true); setError(""); setResult(null);
    const body = new FormData();
    Object.entries(form).forEach(([key, value]) => body.append(key, value === "" && ["age_years", "useful_life_years", "repair_cost", "resale_value"].includes(key) ? "0" : value));
    if (productId) body.append("product_id", productId);
    if (image) body.append("image", image);
    try { const saved = await api.analyze(body); setResult(saved); setProductId(String(saved.product_id)); setNotice("Assessment saved to this product record. Its passport ID stays the same."); }
    catch (err) { setError(err.message); } finally { setLoading(false); }
  }
  return <>
    <PageHeading eyebrow="PRODUCT ASSESSMENT" title="What's the next best life?" description="Share what you know. ReLife compares practical pathways — your answers remain estimates, not an inspection." />
    <div className="analysis-layout"><form className="panel form-panel" onSubmit={submit}>
      <div className="form-section-title"><span className="step-number">01</span><div><b>Tell us about your product</b><small>Start with the basics; add an image if helpful.</small></div></div>
      <div className="form-grid"><label>Product category<select value={form.category} onChange={(e) => change("category", e.target.value)}>{["electronics", "furniture", "clothing", "household", "appliance", "other"].map((v) => <option key={v} value={v}>{capitalize(v)}</option>)}</select></label>
        <label>Product type / name<input type="text" maxLength="80" required value={form.product_name} onChange={(e) => change("product_name", e.target.value)} /><small>For example, laptop or chair</small></label>
        <label>Approximate age<input type="number" min="0" max="100" step="0.5" required value={form.age_years} onChange={(e) => change("age_years", e.target.value)} /><small>Years</small></label>
        <label>Expected additional useful life<input type="number" min="0" max="50" step="0.5" required value={form.useful_life_years} onChange={(e) => change("useful_life_years", e.target.value)} /><small>Your estimate in years</small></label>
        <label>Current condition<select value={form.condition} onChange={(e) => change("condition", e.target.value)}>{["excellent", "good", "fair", "poor", "broken"].map((v) => <option key={v}>{v}</option>)}</select></label>
        <label><span className="location-label-title"><MapPin size={13} /> Location (optional)</span><input type="text" maxLength="100" placeholder="Campus, neighborhood, or district" value={form.location || ""} onChange={(e) => change("location", e.target.value)} /><small>Used to rank nearby sample recipients; no precise address needed.</small></label>
        <label>Estimated repair cost<input type="number" min="0" step="0.01" placeholder="0.00" value={form.repair_cost} onChange={(e) => change("repair_cost", e.target.value)} /><small>Optional · in your local currency</small></label>
        <label>Estimated resale value<input type="number" min="0" step="0.01" placeholder="0.00" value={form.resale_value} onChange={(e) => change("resale_value", e.target.value)} /><small>Optional · your estimate</small></label>
        <label className="wide-field">Visible damage or notes<textarea rows="3" maxLength="1000" placeholder="Describe only what you can see or have observed…" value={form.visible_damage} onChange={(e) => change("visible_damage", e.target.value)} /></label>
      </div>
      <label className={`upload-zone ${dragging ? "dragging" : ""}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); chooseImage(e.dataTransfer.files?.[0]); }}><input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => chooseImage(e.target.files?.[0])} /><span className="upload-icon"><Cpu size={21} /></span><b>{image ? image.name : "Choose or drop a product photo"}</b><small>{image ? `${(image.size / 1024).toFixed(0)} KB · JPG, PNG, or WebP` : "Click to browse or drag a file here · max 5 MB"}</small></label>
      {image && <div className="image-preview-row"><img src={imagePreview} alt="Selected product preview" /><span><b>Photo ready to upload</b><small>It will be sent with this assessment and is not analyzed or retained.</small></span><button type="button" className="text-button" onClick={() => setImage(null)}>Remove photo</button></div>}
      {error && <div className="error-box">{error}</div>}
      <div className="form-footer"><span><ShieldCheck size={15} />Your data is saved to your private account.</span><button className="button button-primary" disabled={loading}>{loading ? <><span className="button-spinner" /> Analyzing…</> : <>Get my recommendation <ArrowRight size={16} /></>}</button></div>
    </form>
      <aside className="analysis-aside"><div className="aside-card nature-card"><span className="mini-label">HOW RELIFE WORKS</span><h3>Better decisions,<br /><em>less guesswork.</em></h3><p>We weigh repairability, condition, stated costs, and the next-use possibilities you share.</p><div className="pathway"><span><Wrench size={15} /></span><i /><span><HeartHandshake size={15} /></span><i /><span><Recycle size={15} /></span></div><small>Repair first · then recover responsibly</small></div><div className="disclaimer-card"><ShieldCheck size={17} /><div><b>Good to know</b><p>A photo cannot reveal internal faults. Always seek a qualified inspection for safety-critical items.</p></div></div></aside>
    </div>
    {result && <section className="panel result-panel"><div className="result-top"><div><div className="eyebrow"><span /> YOUR RESULT · {result.inference_mode || "rule-based demo"}</div><h2>We suggest: <span>{result.recommendation}</span></h2><p>{result.explanation}</p><small>Product record #{result.product_id} · Passport {result.passport_id}</small></div><div className="result-stamp"><Leaf size={25} /></div></div>{result.decision_calculation && <div className="result-note"><CircleHelp size={16} />{result.decision_calculation}</div>}<div className="option-grid">{(Array.isArray(result.options) ? result.options : []).map((option, index) => <div className="option-card" key={option.action || index}><b>{capitalize(option.action || "Option")}{option.recommended ? " · recommended" : ""}</b><span>{option.estimate || "Estimate not provided"}</span><small>{option.eligible === false ? "Not suitable under reported condition" : "Potentially suitable"}{typeof option.estimated_cost === "number" && <> · cost estimate {option.estimated_cost.toFixed(2)}</>}{typeof option.estimated_proceeds === "number" && <> · stated value {option.estimated_proceeds.toFixed(2)}</>}<br />{option.note}</small></div>)}</div>{(!Array.isArray(result.options) || result.options.length === 0) && <div className="notice-card wide-notice" role="status"><CircleHelp size={16} /><p>Recommendation saved, but the backend returned no option comparison. Refresh the page or restart the backend to load the latest result format.</p></div>}<div className="result-note"><CircleHelp size={16} />{result.image_note} All amounts are user estimates in the user's local currency; alternatives depend on inspection, recipient acceptance, and facility rules.</div><div className="result-actions"><button className="button button-secondary" onClick={() => { setProductId(""); setResult(null); }}>Start a different product</button><button className="button button-secondary" onClick={() => setPage("passport")}>Open product passport</button><button className="button button-primary" onClick={() => setPage("rescue")}>Generate recovery plan <ArrowRight size={15} /></button></div></section>}
  </>;
}

function HistoryPage({ setPage }) {
  const [items, setItems] = useState(null); const [error, setError] = useState("");
  const load = () => api.history().then(setItems).catch((e) => setError(e.message)); useEffect(() => { load(); }, []);
  if (error) return <ErrorState error={error} retry={load} />; if (!items) return <Loading />;
  return <><PageHeading eyebrow="YOUR SAVED WORK" title="My history" description="Every assessment and passport connected to your account." action={<button className="button button-primary" onClick={() => setPage("analyze")}><Sparkles size={16} /> New assessment</button>} />
    <section className="panel table-panel">{items.length ? <div className="table-scroll"><table><thead><tr><th>PRODUCT</th><th>CONDITION</th><th>LOCATION</th><th>RECOMMENDATION</th><th>DATE</th><th>PASSPORT</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><b>{item.product_name || capitalize(item.category)}</b><small>{item.age_years} years old</small></td><td><span className="condition-tag">{item.condition}</span></td><td>{item.location || "Not provided"}</td><td><span className="recommendation-badge">{item.recommendation}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><code>{item.passport_id}</code></td><td><button className="text-button" onClick={() => setPage("passport")}>Open <ArrowRight size={14} /></button></td></tr>)}</tbody></table></div> : <EmptyState title="No products saved yet" text="Start with a product assessment; your recommendations will be saved here." action={<button className="button button-primary" onClick={() => setPage("analyze")}>Analyze a product</button>} />}</section></>;
}

function getProduct(items) { return items?.[0]?.product_id || ""; }
function ProductPicker({ items, value, onChange }) {
  const seen = new Set();
  const products = items.filter((item) => {
    if (seen.has(item.product_id)) return false;
    seen.add(item.product_id);
    return true;
  });
  return <select value={value} onChange={(e) => onChange(e.target.value)}><option value="">Select a saved product</option>{products.map((item) => <option key={item.product_id} value={item.product_id}>{capitalize(item.product_name || item.category)} · {item.passport_id}</option>)}</select>;
}

function calculateScenarioPreview(form) {
  const assumptions = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, Number(value) || 0]));
  const period = assumptions.period_years;
  const life = assumptions.useful_life_years;
  const pathways = [
    ["repair", assumptions.repair_cost, assumptions.resale_value, life],
    ["resale", 0, assumptions.resale_value, life],
    ["donation", 0, 0, life],
    ["reuse", assumptions.reuse_value, 0, life],
    ["salvage", 0, assumptions.salvage_value, 0],
    ["recycling", 0, 0, 0],
  ];
  const rows = pathways.map(([action, cost, value, useful]) => {
    const total = Number((cost + assumptions.replacement_cost_per_year * (period - Math.min(period, useful))).toFixed(2));
    return {
      action, estimated_cost: cost, estimated_value: value, useful_life_years: useful,
      estimated_total_cost: total, estimated_net_cost: Number((total - value).toFixed(2)),
      cost_per_additional_year: useful > 0 ? Number((total / useful).toFixed(2)) : null,
      waste_avoided_units: Math.min(period, useful) || (action === "salvage" && value > 0 ? 0.5 : action === "recycling" ? 0.25 : 0),
    };
  });
  return { results: rows, best_action: [...rows].sort((a, b) => a.estimated_net_cost - b.estimated_net_cost)[0]?.action };
}

function PassportPage({ setPage, initialProductId }) {
  const [items, setItems] = useState([]); const [id, setId] = useState(""); const [passport, setPassport] = useState(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [note, setNote] = useState("");
  useEffect(() => { api.history().then((list) => { setItems(list); if (list.length) setId(String(initialProductId || getProduct(list))); }).catch((e) => setError(e.message)); }, [initialProductId]);
  useEffect(() => { if (!id) { setPassport(null); return; } api.passport(id).then(setPassport).catch((e) => setError(e.message)); }, [id]);
  async function addUpdate(type) { if (!note.trim()) return; setBusy(true); try { await api.passportUpdate(id, { update_type: type, detail: note }); setNote(""); setPassport(await api.passport(id)); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  async function transfer() { const email = window.prompt("Enter the next owner's email for this demo transfer"); if (!email) return; setBusy(true); try { await api.transfer(id, { new_owner_email: email, note: "Transfer proposed in demo workflow" }); setPassport(await api.passport(id)); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  return <><PageHeading eyebrow="PRODUCT STORY" title="Afterlife passport" description="A transparent, user-maintained timeline for each product — not an independently verified record." action={items.length > 0 && <div className="picker-wrap"><ProductPicker items={items} value={id} onChange={setId} /></div>} />
    {error && <div className="error-box">{error}</div>}
    {!items.length ? <EmptyState title="No passport yet" text="Analyze a product to create a unique ID and start its timeline." action={<button className="button button-primary" onClick={() => setPage("analyze")}>Create a passport</button>} /> : !passport ? <Loading /> : <div className="passport-grid"><section className="panel passport-main"><div className="passport-id"><div className="passport-leaf"><Leaf size={20} /></div><div><span>UNIQUE PRODUCT ID</span><h2>{passport.public_id}</h2></div><span className="live-tag"><i /> ACTIVE RECORD</span></div><div className="passport-product"><div className="product-placeholder"><PackageCheck size={32} /></div><div><span className="mini-label">PRODUCT PROFILE</span><h3>{passport.product_name || capitalize(passport.category)}</h3><p>Reported condition: <b>{passport.condition}</b>{passport.location && <> · <span className="passport-location">{passport.location}</span></>}</p><small>{passport.age_years} years old · {passport.useful_life_years} estimated additional useful years</small></div></div>
      <div className="timeline-title"><h3>Analysis history</h3><span>{passport.analysis_history.length} assessments</span></div><div className="passport-saved-data">{passport.analysis_history.map((item, index) => <div key={`${item.created_at}-${index}`}><b>{capitalize(item.recommendation)}</b><span>Repair estimate {item.repair_cost} · resale estimate {item.resale_value}</span><small>{new Date(item.created_at).toLocaleString()}</small></div>)}</div>
      {passport.components.length > 0 && <><div className="timeline-title"><h3>Latest component assessment</h3></div><div className="passport-saved-data">{passport.components.map((item) => <div key={item.name}><b>{capitalize(item.name)} · {capitalize(item.condition_state)}</b><span>{item.recovery_route}</span></div>)}</div></>}
      {passport.recovery_plan?.length > 0 && <><div className="timeline-title"><h3>Recovery plan progress</h3><span>{passport.recovery_plan.filter((step) => step.status === "completed").length}/{passport.recovery_plan.length} completed</span></div><div className="passport-saved-data">{passport.recovery_plan.map((step, index) => <div key={`${step.action}-${index}`}><b>{capitalize(step.action)} · {capitalize(step.status)}</b><span>{step.reason}</span></div>)}</div></>}
      <div className="timeline-title"><h3>Product journey</h3><span>{passport.events.length} updates</span></div><div className="timeline">{[...passport.events].reverse().map((event, index) => <div className="timeline-event" key={`${event.at}-${index}`}><div className="timeline-dot"><Check size={12} /></div><div><b>{capitalize(event.type)}</b><p>{event.detail}</p><small>{new Date(event.at).toLocaleString()}</small></div></div>)}</div>
      <div className="passport-update"><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a repair, condition update, or recovery outcome…" maxLength={500} /><button className="button button-primary" disabled={busy || !note.trim()} onClick={() => addUpdate("condition update")}>{busy ? "Saving…" : "Add update"}</button></div>
      <button className="text-button transfer-button" onClick={transfer}>Propose demo ownership transfer <ArrowRight size={14} /></button>
      </section><aside><div className="panel qr-panel"><span className="section-kicker">PASSPORT QR</span><div className="qr-box"><QRCodeSVG value={passport.qr_payload} size={142} bgColor="#ffffff" fgColor="#183a2e" /></div><b>Scan to identify</b><p>Demo QR payload only; it does not publish private account details.</p></div><div className="notice-card"><ShieldCheck size={17} /><p>{passport.verification_note}</p></div></aside></div>}
  </>;
}

function MatchingPage() {
  const [items, setItems] = useState([]); const [id, setId] = useState(""); const [matches, setMatches] = useState([]); const [error, setError] = useState(""); const [busy, setBusy] = useState(null);
  useEffect(() => { api.history().then((list) => { setItems(list); if (list.length) setId(String(getProduct(list))); }).catch((e) => setError(e.message)); }, []);
  useEffect(() => { if (id) api.matches(id).then(setMatches).catch((e) => setError(e.message)); }, [id]);
  async function update(requestId, status) { setBusy(requestId); try { await api.matchUpdate(id, requestId, status); setMatches(await api.matches(id)); } catch (e) { setError(e.message); } finally { setBusy(null); } }
  return <><PageHeading eyebrow="NEED BEFORE WASTE" title="A good match changes everything." description="Find sample recipient requests that could give your product another useful life." action={items.length > 0 && <div className="picker-wrap"><ProductPicker items={items} value={id} onChange={setId} /></div>} />{error && <div className="error-box">{error}</div>}
    {!items.length ? <EmptyState title="Assess a product to get started" text="Matching uses the category and reported condition of a saved product." /> : <><div className="demo-banner"><HeartHandshake size={18} /><span><b>Demo recipient data</b><small>These sample requests are illustrative; no real recipient is contacted.</small></span></div><div className="match-list">{matches.map((match, index) => <div className="panel match-card" key={match.id}><div className="match-rank">{String(index + 1).padStart(2, "0")}</div><div className="match-content"><div className="match-head"><div><h3>{match.name}</h3><span className="location-label"><Compass size={13} /> {match.location}</span></div><span className="match-score">{match.score}% <small>fit</small></span></div><p>{match.requirement}</p><div className="match-reason"><Sparkles size={14} />{match.reason}</div><div className="match-footer"><span className={`state-pill ${match.status}`}>{match.status}</span><div>{match.status === "pending" ? <button className="button button-secondary compact" disabled={busy === match.id} onClick={() => update(match.id, "accepted")}>Mark interested</button> : match.status === "accepted" ? <button className="button button-primary compact" disabled={busy === match.id} onClick={() => update(match.id, "completed")}>Mark completed</button> : <span className="completed-label"><Check size={14} /> Complete</span>}</div></div></div></div>)}{matches.length === 0 && <EmptyState title="No close matches yet" text="Try another product category or condition." />}</div></>}
  </>;
}

function SalvagePage() {
  const [items, setItems] = useState([]); const [id, setId] = useState(""); const [category, setCategory] = useState("laptop"); const [components, setComponents] = useState([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { api.history().then((list) => { setItems(list); if (list.length) setId(String(getProduct(list))); }).catch((e) => setError(e.message)); }, []);
  useEffect(() => {
    if (!id) { setComponents([]); return; }
    const selected = items.find((item) => String(item.product_id) === id);
    const name = selected?.product_name?.toLowerCase() || "";
    if (name.includes("laptop")) setCategory("laptop");
    else if (name.includes("phone") || name.includes("mobile")) setCategory("mobile_phone");
    else if (name.includes("chair")) setCategory("chair");
    else if (name.includes("appliance")) setCategory("household_appliance");
    api.getSalvage(id).then((result) => setComponents(result.components)).catch((e) => setError(e.message));
  }, [id, items]);
  function setState(name, condition_state) {
    setComponents((list) => list.map((item) => item.name === name ? { ...item, condition_state } : item));
  }
  async function assess() { if (!id) return; setLoading(true); setError(""); try { const condition_states = Object.fromEntries(components.map((item) => [item.name, item.condition_state])); const result = await api.salvage(id, { category, condition_states }); setComponents(result.components); } catch (e) { setError(e.message); } finally { setLoading(false); } }
  return <><PageHeading eyebrow="COMPONENT RECOVERY" title="Every part has potential." description="When a product is not useful as a whole, explore possible components and confirm their condition yourself." action={items.length > 0 && <div className="picker-wrap"><ProductPicker items={items} value={id} onChange={setId} /></div>} />{error && <div className="error-box">{error}</div>}
    <section className="panel salvage-controls"><div className="control-block"><label>Product type<select value={category} onChange={(e) => setCategory(e.target.value)}>{[["laptop", "Laptop"], ["mobile_phone", "Mobile phone"], ["chair", "Chair"], ["household_appliance", "Household appliance"], ["electronics", "Other electronics"], ["furniture", "Other furniture"], ["clothing", "Clothing"], ["household", "Other household goods"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><p>Components are suggestions for inspection, not claims about this product.</p></div><button className="button button-primary" onClick={assess} disabled={!id || loading}>{loading ? "Saving conditions…" : "Find recovery options"} <ArrowRight size={15} /></button></section>
    {components.length > 0 && <><div className="component-grid">{components.map((component) => <div className="panel component-card" key={component.name}><span className="component-name">{capitalize(component.name)}</span><span className="component-use">{component.potential_use}</span><label>Condition<select value={component.condition_state || "untested"} onChange={(e) => setState(component.name, e.target.value)}>{["working", "damaged", "untested"].map((state) => <option key={state} value={state}>{capitalize(state)}</option>)}</select></label><span className="verification-note">{component.verification}</span><span className="component-use">Route: {component.recovery_route}</span>{component.estimated_value_range && <span className="confirmed-text">Illustrative range: {component.estimated_value_range.low}–{component.estimated_value_range.high} (verify locally)</span>}</div>)}</div><div className="notice-card wide-notice"><Boxes size={17} /><p>Only user-marked working components receive illustrative value ranges; they are not market quotes. Hidden components remain untested until inspected. Save condition edits with “Find recovery options.”</p></div></>}
    {!items.length && <EmptyState title="Start with a product assessment" text="The salvage checklist can be attached to a saved product." />}
  </>;
}

function SimulatorPage() {
  const [items, setItems] = useState([]); const [id, setId] = useState(""); const [form, setForm] = useState({ repair_cost: 25, resale_value: 35, useful_life_years: 2, period_years: 3, reuse_value: 10, salvage_value: 5, replacement_cost_per_year: 0 }); const [results, setResults] = useState(null); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { api.history().then((list) => { setItems(list); if (list.length) { setId(String(getProduct(list))); const first = list[0]; setForm((v) => ({ ...v, repair_cost: first.repair_cost, resale_value: first.resale_value })); } }).catch((e) => setError(e.message)); }, []);
  useEffect(() => {
    if (!id) return undefined;
    let active = true;
    const selected = items.find((item) => String(item.product_id) === id);
    api.getSimulation(id).then((saved) => {
      if (!active) return;
      if (saved) {
        setForm(saved.assumptions);
        setResults(saved);
      } else {
        setForm((value) => ({ ...value, repair_cost: selected?.repair_cost ?? value.repair_cost, resale_value: selected?.resale_value ?? value.resale_value, useful_life_years: selected?.useful_life_years ?? value.useful_life_years }));
        setResults({
          formula: "Estimated total cost = one-time pathway cost + replacement cost per uncovered year. Net estimate = total cost - user-entered proceeds. Cost per added year = total cost / assumed added life. Continued-use proxy = assumed use years within the selected period.",
          disclaimer: "Illustrative assumptions only; no precise carbon or environmental savings are calculated.",
        });
      }
    }).catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [id, items]);
  async function run() { setError(""); setLoading(true); try { const result = await api.simulate({ product_id: Number(id), ...Object.fromEntries(Object.entries(form).map(([k, v]) => [k, Number(v)])) }); setResults(result); } catch (e) { setError(e.message); } finally { setLoading(false); } }
  const preview = results && calculateScenarioPreview(form);
  const chartData = preview?.results.map((r) => ({ action: capitalize(r.action), cost: r.estimated_total_cost, avoided: r.waste_avoided_units }));
  return <><PageHeading eyebrow="WHAT-IF PLANNING" title="Imagine what comes next." description="Change your assumptions and compare practical pathways over a period you choose." action={items.length > 0 && <div className="picker-wrap"><ProductPicker items={items} value={id} onChange={setId} /></div>} />{error && <div className="error-box">{error}</div>}
    {!items.length ? <EmptyState title="You need a saved product first" text="Run an assessment so the simulator can attach and save your assumptions." /> : <>    <section className="panel simulator-controls"><div className="simulator-intro"><div className="sim-icon"><Activity size={21} /></div><div><h3>Adjust your assumptions</h3><p>Results recalculate as you edit; Compare saves these assumptions to the selected product.</p></div></div><div className="sim-input-grid">{[["repair_cost", "Repair cost", "currency"], ["resale_value", "Resale value", "currency"], ["useful_life_years", "Additional useful life", "years"], ["period_years", "Comparison period", "years"], ["reuse_value", "Reuse / conversion cost", "currency"], ["salvage_value", "Salvage value", "currency"], ["replacement_cost_per_year", "Cost per uncovered year", "currency"]].map(([key, label, unit]) => <label key={key}>{label}<div className="input-unit"><input type="number" min={key === "period_years" ? 1 : 0} max={key === "period_years" ? 30 : key === "useful_life_years" ? 50 : 100000} step="1" value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} /><span>{unit === "years" ? "yrs" : "est."}</span></div></label>)}</div><button className="button button-primary" onClick={run} disabled={!id || loading}>{loading ? "Saving comparison…" : <>Save comparison <ArrowRight size={15} /></>}</button></section>
    {results && <><div className="sim-summary"><div><span className="section-kicker">LIVE ILLUSTRATIVE COMPARISON</span><h3>{form.period_years} year{Number(form.period_years) === 1 ? "" : "s"} · {preview.results.length} pathways · lowest net estimate: {capitalize(preview.best_action)}</h3></div><span className="estimate-tag"><ShieldCheck size={14} /> ESTIMATES, NOT MEASUREMENTS</span></div><div className="dashboard-grid"><section className="panel chart-panel"><div className="panel-heading"><div><span className="section-kicker">YOUR INPUT ESTIMATES</span><h2>Total estimated costs over period</h2></div></div><div className="chart-area"><Suspense fallback={<div className="chart-empty">Loading chart…</div>}><ScenarioCostChart data={chartData} /></Suspense></div></section><section className="panel formula-panel"><span className="section-kicker">HOW WE ESTIMATE</span><h2>Transparent by design.</h2><p>{results.formula}</p><div className="formula-equation">Your assumptions <ArrowRight size={14} /> scenario comparison</div><p className="muted">{results.disclaimer}</p></section></div><section className="panel scenario-table"><div className="panel-heading"><div><span className="section-kicker">ALL SCENARIOS</span><h2>Compare the trade-offs</h2></div></div><div className="scenario-grid">{preview.results.map((r) => <div className="scenario-row" key={r.action}><b>{capitalize(r.action)}{r.action === preview.best_action ? " · lowest net estimate" : ""}</b><span>Total cost: {r.estimated_total_cost.toFixed(2)}</span><span>Direct cost: {r.estimated_cost.toFixed(2)}</span><span>Estimated value: {r.estimated_value.toFixed(2)}</span><span>Net cost: {r.estimated_net_cost.toFixed(2)}</span><span>Cost / added year: {r.cost_per_additional_year === null ? "Not applicable" : r.cost_per_additional_year.toFixed(2)}</span><span>Potential continued-use proxy: {r.waste_avoided_units} units</span><small>Illustrative user-input estimate; no environmental savings are measured.</small></div>)}</div></section></>}</>}
  </>;
}

function RescuePage({ setNotice }) {
  const [items, setItems] = useState([]); const [id, setId] = useState(""); const [plan, setPlan] = useState(null); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { api.history().then((list) => { setItems(list); if (list.length) setId(String(getProduct(list))); }).catch((e) => setError(e.message)); }, []);
  useEffect(() => { if (!id) { setPlan(null); return; } api.getPlan(id).then(setPlan).catch((e) => setError(e.message)); }, [id]);
  async function build() { setLoading(true); setError(""); try { setPlan(await api.createPlan(id)); } catch (e) { setError(e.message); } finally { setLoading(false); } }
  async function update(step, status) { try { await api.updateStep(step.id, status); setPlan(await api.getPlan(id)); setNotice(`Recovery step marked ${status}.`); } catch (e) { setError(e.message); } }
  async function alternative(step) { setLoading(true); setError(""); try { const updated = await api.findPlanAlternative(id, step.id); setPlan(updated); setNotice(updated.alternative ? `Next feasible alternative: ${updated.alternative.action}.` : updated.alternative_note); } catch (e) { setError(e.message); } finally { setLoading(false); } }
  return <><PageHeading eyebrow="RECOVERY ORCHESTRATION" title="A clear path, with a plan B." description="Build a ranked recovery sequence that evaluates repair first when appropriate and keeps fallback options visible." action={items.length > 0 && <div className="picker-wrap"><ProductPicker items={items} value={id} onChange={(v) => { setId(v); setPlan(null); }} /></div>} />{error && <div className="error-box">{error}</div>}
    {!items.length ? <EmptyState title="Assess a product to make a plan" text="The recovery chain uses your saved condition, recommendation, and estimates." /> : <><div className="plan-intro"><div className="plan-intro-icon"><PackageCheck size={22} /></div><div><b>Built around your product — not a one-size-fits-all answer.</b><span>Steps are suggested using configurable demo rules. Provider availability is not live.</span></div><button className="button button-primary" onClick={build} disabled={loading}>{loading ? "Building plan…" : plan ? "Regenerate plan" : "Generate rescue chain"} <ArrowRight size={15} /></button></div>
      {plan && <>{plan.alternative && <div className="notice-card wide-notice"><ArrowRight size={17} /><p>Next feasible alternative: <b>{capitalize(plan.alternative.action)}</b> — {plan.alternative.reason}</p></div>}{plan.alternative_note && <div className="notice-card wide-notice"><ShieldCheck size={17} /><p>{plan.alternative_note}</p></div>}<div className="rescue-timeline">{plan.steps.map((step, index) => <div className={`rescue-step ${step.status}`} key={step.id}><div className="rescue-count">{String(index + 1).padStart(2, "0")}</div><div className="rescue-body"><div className="rescue-step-header"><h3>{capitalize(step.action)}</h3><span className={`state-pill ${step.status}`}>{step.status}</span></div><p>{step.reason}</p><div className="rescue-provider"><Compass size={14} />{step.provider ? `${step.provider} · sample listing` : step.fallback}</div><div className="rescue-step-actions"><button className="button button-secondary compact" onClick={() => update(step, "completed")} disabled={step.status === "completed"}><Check size={14} /> Mark complete</button><button className="text-button" onClick={() => update(step, "pending")} disabled={step.status === "pending"}>Mark pending</button><button className="text-button" onClick={() => update(step, "unavailable")} disabled={step.status === "unavailable"}>Unavailable</button>{step.status === "unavailable" && <button className="button button-primary compact" onClick={() => alternative(step)} disabled={loading}>Find alternative</button>}</div></div></div>)}</div></>}
    </>}
  </>;
}

function CentersPage() {
  const [filters, setFilters] = useState({ category: "", location: "", kind: "" });
  const [source, setSource] = useState("live");
  const [items, setItems] = useState([]);
  const [searchInfo, setSearchInfo] = useState(null);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadLive(event) {
    event?.preventDefault();
    if (!filters.location.trim()) { setError("Enter a city, district, or postal code to find nearby listings."); return; }
    setError(""); setLoading(true); setSearched(true);
    try {
      const result = await api.liveCenters({ location: filters.location.trim(), kind: filters.kind });
      setItems(result.centers);
      setSearchInfo(result);
    } catch (e) {
      setItems([]);
      setError(e.message);
    } finally { setLoading(false); }
  }

  async function loadSamples() {
    setSource("samples"); setError(""); setLoading(true); setSearched(true); setSearchInfo(null);
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
      setItems(await api.centers(params));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  function useLive() {
    setSource("live"); setItems([]); setSearchInfo(null); setSearched(false); setError("");
  }

  const visibleItems = source === "samples" && filters.category
    ? items.filter((item) => item.categories?.toLowerCase().includes(filters.category.toLowerCase()))
    : items;

  return <>
    <PageHeading eyebrow="LOCAL RECOVERY NETWORK" title="Find a next step near you." description="Search current OpenStreetMap provider listings by a city, district, or postal code. You can also browse the clearly marked sample directory." />
    <div className="provider-tabs"><button className={source === "live" ? "selected" : ""} onClick={useLive}><Compass size={15} /> OpenStreetMap search</button><button className={source === "samples" ? "selected" : ""} onClick={loadSamples}><Boxes size={15} /> Sample directory</button></div>
    <form className="panel center-filters" onSubmit={source === "live" ? loadLive : (e) => { e.preventDefault(); loadSamples(); }}>
      {source === "live" ? <label className="location-search"><span>City, district, or postal code</span><div className="search-field"><Search size={16} /><input placeholder="e.g. Vijayawada, India" value={filters.location} onChange={(e) => setFilters({ ...filters, location: e.target.value })} /></div></label> : <>
        <label><span>Product category</span><select value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}><option value="">All categories</option>{["electronics", "furniture", "clothing", "household"].map((v) => <option key={v}>{v}</option>)}</select></label>
        <label><span>Sample location</span><div className="search-field"><Search size={16} /><input placeholder="Campus, district…" value={filters.location} onChange={(e) => setFilters({ ...filters, location: e.target.value })} /></div></label>
      </>}
      <label><span>Recovery pathway</span><select value={filters.kind} onChange={(e) => setFilters({ ...filters, kind: e.target.value })}><option value="">All pathways</option>{["repair", "donation", "reuse", "recycling"].map((v) => <option key={v}>{v}</option>)}</select></label>
      <button className="button button-primary" disabled={loading}>{loading ? <><span className="button-spinner" /> Searching…</> : <><Search size={15} /> {source === "live" ? "Find live listings" : "Find sample centers"}</>}</button>
    </form>
    {source === "live" && <div className="live-source-banner"><MapPin size={17} /><span><b>Live map listings · OpenStreetMap</b><small>We only show contact and opening-hour details actually present in OpenStreetMap. This search sends the location you enter to OpenStreetMap.</small></span></div>}
    {error && <div className="error-box">{error}</div>}
    {loading ? <Loading label={source === "live" ? "Searching OpenStreetMap listings…" : "Loading sample listings…"} /> : visibleItems.length ? <>
      {source === "live" && searchInfo && <div className="search-meta"><span>{visibleItems.length} listing{visibleItems.length === 1 ? "" : "s"} near <b>{searchInfo.searched_location}</b></span><span>Updated {new Date(searchInfo.last_updated).toLocaleTimeString()}</span></div>}
      <div className="center-grid">{visibleItems.map((center) => <ProviderCard key={center.id} center={center} live={source === "live"} />)}</div>
      {source === "live" && searchInfo && <div className="fine-print osm-attribution">{searchInfo.attribution} · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">Map data and attribution</a></div>}
    </> : searched && !error ? <EmptyState title={source === "live" ? "No mapped providers found" : "No sample centers found"} text={source === "live" ? searchInfo?.message || "Try a nearby city or a different recovery pathway. OpenStreetMap coverage varies by area." : "Try clearing one or more filters."} /> : <div className="empty-search"><div className="empty-icon"><MapPin /></div><b>{source === "live" ? "Enter a location to search nearby" : "Choose filters to browse sample listings"}</b><span>{source === "live" ? "Search by city, district, or postal code — no precise address needed." : "Sample providers are illustrative and are not real listings."}</span></div>}
    {source === "live" && <div className="notice-card provider-disclaimer"><CircleHelp size={16} /><p>{searchInfo?.availability_note || "OpenStreetMap published hours can be incomplete or out of date. Map data does not show real-time appointment slots or service capacity. Call or message the provider to confirm opening and availability."}</p></div>}
    {source === "samples" && <div className="fine-print"><ShieldCheck size={14} />Sample listings are illustrative, with no real contact details or live availability.</div>}
  </>;
}

function ProviderCard({ center, live }) {
  const contacts = [
    center.phone && <a key="phone" className="contact-link" href={`tel:${center.phone}`}><Phone size={14} />{center.phone}</a>,
    center.email && <a key="email" className="contact-link" href={`mailto:${center.email}`}><Mail size={14} />{center.email}</a>,
    center.website && <a key="website" className="contact-link" href={center.website} target="_blank" rel="noreferrer"><Globe size={14} />Website <ArrowUpRight size={12} /></a>,
  ].filter(Boolean);
  return <article className={`panel center-card ${live ? "live-center-card" : ""}`}>
    <div className="center-icon"><Compass size={20} /></div><span className={`sample-tag ${live ? "live-listing-tag" : ""}`}>{live ? "OPENSTREETMAP" : "SAMPLE"}</span>
    <h3>{center.name}</h3><span className="center-kind">{capitalize(center.kind)} · {center.location}</span><p>{center.description}</p>
    {live ? <div className={`provider-hours ${center.availability_status}`}><Clock3 size={14} /><span>{center.availability}</span></div> : <div className="center-categories">{center.categories.split(",").map((category) => <span key={category}>{category}</span>)}</div>}
    {contacts.length > 0 ? <div className="provider-contacts">{contacts}</div> : live && <small className="no-contact"><CircleHelp size={13} />{center.contact_note}</small>}
    {live && <><small className="contact-note">{center.contact_note}</small><a className="map-link" href={center.map_url} target="_blank" rel="noreferrer">View OpenStreetMap entry <ArrowUpRight size={13} /></a><small className="category-warning">Accepted items are not verified; contact the provider first.</small></>}
    {!live && <small><CircleHelp size={13} /> {center.availability}</small>}
  </article>;
}

function ImpactPage() {
  const [data, setData] = useState(null); const [error, setError] = useState("");
  const load = () => api.impact().then(setData).catch((e) => setError(e.message)); useEffect(() => { load(); }, []);
  function exportCsv() { if (!data?.analyses?.length) return; const rows = [["Product category", "Recommendation", "Repair estimate", "Resale estimate", "Passport ID", "Date"], ...data.analyses.map((r) => [r.category, r.recommendation, r.repair_cost, r.resale_value, r.public_id, r.created_at])]; const csv = rows.map((row) => row.map((field) => `"${String(field ?? "").replaceAll('"', '""')}"`).join(",")).join("\r\n"); const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); const link = document.createElement("a"); link.href = url; link.download = "relife-impact-report.csv"; link.click(); URL.revokeObjectURL(url); }
  if (error) return <ErrorState error={error} retry={load} />; if (!data) return <Loading />;
  return <><PageHeading eyebrow="YOUR CIRCULAR CONTRIBUTION" title="Impact, with the fine print." description="A transparent summary of your saved activity. Estimates are clearly separated from measured results." action={<button className="button button-secondary" disabled={!data.analyses.length} onClick={exportCsv}><FileChartColumn size={15} /> Export CSV</button>} />
    <div className="impact-banner"><div className="impact-leaf"><Leaf size={22} /></div><div><b>We won't invent a number to make an impact look bigger.</b><span>Waste avoided and money saved are not measured in this demo. This report shows your actions and their status instead.</span></div></div>
    <div className="impact-stats"><StatCard icon={ClipboardList} label="Assessments saved" value={data.total_analyses} foot="Your submitted products" color="green" /><StatCard icon={Check} label="Recovery steps completed" value={data.analyses.reduce((sum, item) => sum + item.completed_steps, 0)} foot="Marked complete by you" color="blue" /><StatCard icon={ArrowDownRight} label="Money saved" value="Not measured" foot="No fabricated estimate" color="peach" /></div>
    <div className="dashboard-grid"><Suspense fallback={<div className="panel chart-empty">Loading chart…</div>}><ActivityChart title="Weekly activity" rows={data.weekly} unit="weeks" /></Suspense><Suspense fallback={<div className="panel chart-empty">Loading chart…</div>}><ActivityChart title="Monthly activity" rows={data.monthly} unit="months" /></Suspense></div>
    <section className="panel report-panel"><div className="panel-heading"><div><span className="section-kicker">ACTIVITY RECORD</span><h2>Your recovery history</h2></div><span className="subtle-tag">Estimate data only</span></div>{data.analyses.length ? <div className="table-scroll"><table><thead><tr><th>DATE</th><th>PRODUCT</th><th>PATHWAY</th><th>REPAIR EST.</th><th>RESALE EST.</th><th>PASSPORT</th><th>RECOVERY STATUS</th></tr></thead><tbody>{data.analyses.map((r) => <tr key={r.id}><td>{new Date(r.created_at).toLocaleDateString()}</td><td>{capitalize(r.category)}</td><td><span className="recommendation-badge">{r.recommendation}</span></td><td>{Number(r.repair_cost).toFixed(2)}</td><td>{Number(r.resale_value).toFixed(2)}</td><td><code>{r.public_id}</code></td><td>{r.plan_steps === 0 ? "No plan" : r.completed_steps === r.plan_steps ? "Completed" : r.completed_steps + r.unavailable_steps > 0 ? "In progress" : "Pending"} · {r.completed_steps}/{r.plan_steps} steps</td></tr>)}</tbody></table></div> : <EmptyState title="No activity to report yet" text="Assess your first product to start building an impact history." />}</section>
    <div className="fine-print"><ShieldCheck size={14} />Potential environmental outcomes are uncertain and are not represented as precise carbon or waste savings.</div>
  </>;
}

function ProfilePage({ user, onLogout }) {
  return <><PageHeading eyebrow="YOUR ACCOUNT" title="A little about you." description="Manage your ReLife AI workspace and account session." />
    <div className="profile-page-grid"><section className="panel profile-card"><div className="profile-hero"><div className="large-avatar">{user.name?.slice(0, 1).toUpperCase()}</div><div><span className="section-kicker">STUDENT WORKSPACE</span><h2>{user.name}</h2><p>{user.email}</p></div></div><div className="profile-details"><div><span>Display name</span><b>{user.name}</b></div><div><span>Email address</span><b>{user.email}</b></div>{user.student_id && <div><span>Student ID</span><b>{user.student_id}</b></div>}<div><span>Workspace type</span><b>Personal account</b></div><div><span>Security</span><b className="security-ok"><ShieldCheck size={15} /> Password protected</b></div></div><div className="profile-actions"><button className="button button-secondary" onClick={onLogout}><LogOut size={16} /> Sign out</button></div></section><aside className="panel privacy-card"><div className="privacy-icon"><ShieldCheck size={20} /></div><h3>Your data stays yours.</h3><p>Analyses, passports, and recovery plans are scoped to your account. Your password is stored as a one-way PBKDF2 hash.</p><div className="privacy-check"><Check size={15} />Private account history</div><div className="privacy-check"><Check size={15} />Authenticated API access</div><div className="privacy-check"><Check size={15} />No photo inference in this demo</div></aside></div>
  </>;
}
