import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function RecoveryChart({ data }) {
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 8, left: -22, bottom: 0 }}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9eee7" /><XAxis dataKey="action" axisLine={false} tickLine={false} tick={{ fill: "#829087", fontSize: 11 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#829087", fontSize: 11 }} /><Tooltip cursor={{ fill: "#f4f7f2" }} /><Bar dataKey="count" fill="#28744d" radius={[5, 5, 0, 0]} barSize={27}>{data.map((entry, index) => <Cell key={entry.action} fill={["#32845c", "#e7a873", "#6588a2", "#98b877", "#d0a76f", "#9aa9a2"][index]} />)}</Bar></BarChart></ResponsiveContainer>;
}

export function ActivityChart({ title, rows, unit }) {
  const data = rows.map((row) => ({ period: row.period, assessments: row.assessments }));
  return <section className="panel chart-panel"><div className="panel-heading"><div><span className="section-kicker">ASSESSMENTS SAVED</span><h2>{title}</h2></div><span className="subtle-tag">{data.length} {unit}</span></div><div className="chart-area">{data.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 8, left: -22, bottom: 0 }}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9eee7" /><XAxis dataKey="period" axisLine={false} tickLine={false} tick={{ fill: "#829087", fontSize: 9 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#829087", fontSize: 10 }} /><Tooltip /><Bar dataKey="assessments" name="Assessments" fill="#32845c" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer> : <div className="chart-empty">Activity counts will appear here after you save assessments.</div>}</div></section>;
}

export function ScenarioCostChart({ data }) {
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 8, left: -22, bottom: 0 }}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9eee7" /><XAxis dataKey="action" axisLine={false} tickLine={false} tick={{ fill: "#829087", fontSize: 11 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#829087", fontSize: 11 }} /><Tooltip /><Bar dataKey="cost" name="Estimated total cost" fill="#32845c" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer>;
}
