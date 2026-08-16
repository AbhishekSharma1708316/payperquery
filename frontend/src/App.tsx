import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import DashboardPage from "./pages/DashboardPage";
import AgentsPage from "./pages/AgentsPage";
import ProvidersPage from "./pages/ProvidersPage";
import TransactionsPage from "./pages/TransactionsPage";
import SecurityPage from "./pages/SecurityPage";

export default function App() {
  return (
    <div className="min-h-screen bg-vault-bg">
      <NavBar />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/security" element={<SecurityPage />} />
        </Routes>
      </main>
    </div>
  );
}
