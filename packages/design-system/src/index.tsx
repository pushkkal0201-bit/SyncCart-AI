import type { ButtonHTMLAttributes, PropsWithChildren, ReactNode } from "react";

export function Button({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`sc-button ${className}`} {...props} />;
}

export function Card({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return <section className={`sc-card ${className}`}>{children}</section>;
}

export function StatusPill({ tone, children }: PropsWithChildren<{ tone: "good" | "warn" | "danger" | "info" }>) {
  return <span className={`sc-pill sc-pill--${tone}`}>{children}</span>;
}

export function AppShell({ children }: PropsWithChildren) {
  return <main className="sc-shell">{children}</main>;
}

export function SectionTitle({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <header className="sc-section-title">
      <div>
        {eyebrow ? <p className="sc-eyebrow">{eyebrow}</p> : null}
        <h2>{title}</h2>
      </div>
      {action}
    </header>
  );
}

export function Spinner() {
  return <span className="sc-spinner" aria-label="Loading" />;
}
