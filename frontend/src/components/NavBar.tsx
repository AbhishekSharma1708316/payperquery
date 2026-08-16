import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Dashboard" },
  { to: "/agents", label: "Agents" },
  { to: "/transactions", label: "Transactions" },
  { to: "/providers", label: "Providers" },
  { to: "/security", label: "Security" },
];

export default function NavBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-vault-border bg-vault-bg/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-vault-accent/20 text-vault-accent">
            ⛨
          </div>
          <span className="text-lg font-semibold tracking-tight">AgentVault</span>
        </div>
        <nav className="flex gap-1">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-vault-accent/15 text-vault-accent"
                    : "text-slate-400 hover:bg-vault-panel hover:text-slate-100"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
