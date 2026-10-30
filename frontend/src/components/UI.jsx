import { ArrowRight, CircleHelp, Leaf, Recycle } from "lucide-react";

export function Logo({ small = false }) {
  return <div className={`brand ${small ? "brand-small" : ""}`}><div className="brand-mark"><Recycle size={small ? 20 : 23} strokeWidth={2.2} /></div><div><b>ReLife<span>AI</span></b>{!small && <small>INTELLIGENT RECOVERY</small>}</div></div>;
}

export function PageHeading({ eyebrow, title, description, action }) {
  return <div className="page-heading"><div><div className="eyebrow"><span />{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}

export function Loading({ label = "Loading your data…" }) {
  return <div className="loading-state"><div className="spinner" />{label}</div>;
}

export function ErrorState({ error, retry }) {
  return <div className="empty-state"><div className="empty-icon"><CircleHelp /></div><h3>We couldn’t load this</h3><p>{error}</p>{retry && <button className="button button-secondary" onClick={retry}>Try again</button>}</div>;
}

export function EmptyState({ title, text, action }) {
  return <div className="empty-state"><div className="empty-icon"><Leaf /></div><h3>{title}</h3><p>{text}</p>{action}</div>;
}

export function StatCard({ icon: Icon, label, value, foot, color }) {
  return <div className="stat-card"><div className={`stat-icon ${color}`}><Icon size={19} /></div><span className="stat-label">{label}</span><strong>{value}</strong><small>{foot}</small></div>;
}

export function QuickAction({ icon: Icon, title, text, onClick }) {
  return <button className="quick-action" onClick={onClick}><div className="quick-icon"><Icon size={17} /></div><span><b>{title}</b><small>{text}</small></span><ArrowRight size={16} /></button>;
}

export function capitalize(value = "") {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
