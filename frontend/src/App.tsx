import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import ChatWidget from "./components/ChatWidget";
import DashboardPage from "./pages/DashboardPage";
import MarketplacePage from "./pages/MarketplacePage";
import ListingsPage from "./pages/ListingsPage";
import AgentsPage from "./pages/AgentsPage";
import TransactionsPage from "./pages/TransactionsPage";
import EscrowPage from "./pages/EscrowPage";

export default function App() {
  return (
    <div className="min-h-screen bg-ink-bg">
      <NavBar />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/marketplace" element={<MarketplacePage />} />
          <Route path="/listings" element={<ListingsPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/escrow" element={<EscrowPage />} />
        </Routes>
      </main>
      <ChatWidget />
    </div>
  );
}
