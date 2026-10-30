import { useState } from "react";
import { ArrowDownRight, ArrowRight, Leaf, ShieldCheck } from "lucide-react";
import { api } from "../services/api";
import { Logo } from "../components/UI";

export default function AuthPage({ onSuccess }) {
  const [mode, setMode] = useState("login");
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", student_id: "", identifier: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = mode === "login"
        ? await api.login({ identifier: form.identifier, password: form.password })
        : await api.register(form);
      onSuccess(result);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-visual">
        <div className="auth-visual-inner">
          <Logo />
          <div className="visual-copy">
            <div className="eyebrow light"><span /> THE CIRCULAR WAY FORWARD</div>
            <h1>Good things<br />deserve <em>another life.</em></h1>
            <p>Make smarter choices for the things you own — repair, pass on, repurpose, and recover.</p>
            <div className="orbit-card">
              <div className="orbit-icon"><Leaf size={21} /></div>
              <div><strong>Every product has a next chapter.</strong><span>Find the path that makes sense for you.</span></div>
              <ArrowDownRight size={19} />
            </div>
          </div>
          <div className="visual-footer"><span>REPAIR</span><i /><span>REUSE</span><i /><span>RECOVER</span></div>
        </div>
        <div className="visual-decoration decor-one" /><div className="visual-decoration decor-two" />
      </section>
      <section className="auth-form-side">
        <div className="auth-form-wrap">
          <div className="mobile-brand"><Logo /></div>
          <span className="eyebrow"><span /> YOUR CIRCULAR WORKSPACE</span>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="muted">{mode === "login" ? "Sign in to pick up where you left off." : "Start giving your products a better next chapter."}</p>
          <form onSubmit={submit} className="auth-form">
            {mode === "register" && <><label>Full name<input required minLength="2" maxLength="80" autoComplete="name" placeholder="e.g. Alex Morgan" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label>Email address<input required type="email" autoComplete="email" placeholder="you@college.edu" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label>Student ID <span className="muted">(optional)</span><input maxLength="32" autoComplete="off" placeholder="e.g. STU-1042" value={form.student_id} onChange={(e) => setForm({ ...form, student_id: e.target.value })} /></label></>}
            {mode === "login" && <label>Email or student ID<input required type="text" autoComplete="username" placeholder="you@college.edu or STU-1042" value={form.identifier} onChange={(e) => setForm({ ...form, identifier: e.target.value })} /></label>}
            <label>Password<div className="password-field"><input required minLength={mode === "register" ? 8 : 1} type={showPassword ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="Enter your password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><button type="button" onClick={() => setShowPassword(!showPassword)}>{showPassword ? "Hide" : "Show"}</button></div></label>
            {mode === "login" && <button type="button" className="text-button forgot" onClick={() => setError("Password reset is not configured in this demo. Contact your project administrator.")}>Forgot password?</button>}
            {error && <div className="error-box">{error}</div>}
            <button className="button button-primary auth-submit" disabled={loading}>{loading ? <><span className="button-spinner" /> Please wait…</> : mode === "login" ? "Sign in to ReLife" : "Create account"}<ArrowRight size={17} /></button>
          </form>
          <div className="auth-switch">{mode === "login" ? "New to ReLife?" : "Already have an account?"} <button className="text-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></div>
          <div className="secure-note"><ShieldCheck size={15} />Your password is securely hashed before it is stored.</div>
        </div>
      </section>
    </div>
  );
}
