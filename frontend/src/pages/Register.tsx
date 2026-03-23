import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api";
import { inputClass } from "../lib/obsidianStyles";

export const Register = () => {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      const data = await register(email, password);
      if (data.error) {
        setError(String(data.error));
        return;
      }
      nav("/", { replace: true });
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col justify-center px-4 py-12 sm:px-6">
      <div className="rounded-2xl border border-outline-variant/10 bg-surface-container p-8 shadow-primaryGlow">
        <h1 className="font-headline text-2xl font-extrabold tracking-tight text-on-surface">Create account</h1>
        <p className="mt-1 text-sm text-on-surface-variant">Join ReelMaker</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-on-surface" htmlFor="reg-email">
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-on-surface" htmlFor="reg-password">
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
              required
            />
          </div>
          {error ? (
            <p className="rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-sm text-error" role="alert">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-primary to-primary-dim py-3 font-headline text-sm font-bold text-on-surface shadow-lg shadow-primary/20 transition hover:brightness-110 disabled:opacity-50"
            aria-busy={loading}
          >
            {loading ? "…" : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-on-surface-variant">
          Already have an account?{" "}
          <Link className="font-bold text-primary hover:underline" to="/login">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
};
