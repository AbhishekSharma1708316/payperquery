import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Dashboard" },
  { to: "/marketplace", label: "Marketplace" },
  { to: "/listings", label: "Listings" },
  { to: "/agents", label: "Agents" },
  { to: "/transactions", label: "Transactions" },
  { to: "/escrow", label: "Escrow" },
];

export default function NavBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-ink-line bg-ink-bg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <span className="font-display text-lg font-semibold tracking-tight text-paper">
          APIMarket
        </span>
        <nav className="flex gap-1">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 font-body text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brass/15 text-brass-bright"
                    : "text-paper-muted hover:bg-ink-panel2 hover:text-paper"
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
