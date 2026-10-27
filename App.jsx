

import { useEffect, useState } from "react";
import { phase3Api } from "./api";
import { useAuth } from "./context/AuthContext.jsx";
import Login from "./pages/Login.jsx";
import "./App.css";

const modules = [
  { name: "Shift Management", load: phase3Api.getShifts },
  { name: "Leave Calendar", load: phase3Api.getLeaves },
  { name: "Documents", load: phase3Api.getDocuments },
  { name: "Performance Reviews", load: phase3Api.getPerformance },
  { name: "Analytics & Reports", load: phase3Api.getAnalytics },
  { name: "Notifications", load: phase3Api.getNotifications },
  { name: "Employee Search", load: phase3Api.getEmployees },
];

export default function App() {
  // Declare user BEFORE using it in useEffect.
  const { user, loading, logout } = useAuth();

  const [results, setResults] = useState({});
  const [errors, setErrors] = useState({});

  useEffect(() => {
    // Do not request protected data before authentication.
    if (loading || !user) {
      return;
    }

    let cancelled = false;

    async function loadModules() {
      const nextResults = {};
      const nextErrors = {};

      await Promise.all(
        modules.map(async (module) => {
          try {
            nextResults[module.name] = await module.load();
          } catch (error) {
            nextErrors[module.name] =
              error.response?.data?.detail ||
              error.message ||
              "Failed to load data";
          }
        })
      );

      if (!cancelled) {
        setResults(nextResults);
        setErrors(nextErrors);
      }
    }

    loadModules();

    return () => {
      cancelled = true;
    };
  }, [user, loading]);

  if (loading) {
    return <div className="loading">Loading WorkSphere...</div>;
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>WorkSphere HRMS</h1>
          <p>Welcome, {user.full_name || user.username || user.email || "User"}</p>
        </div>

        <button type="button" onClick={logout}>
          Logout
        </button>
      </header>

      <main className="dashboard">
        <h2>Phase 3 Dashboard</h2>

        <div className="module-grid">
          {modules.map((module) => (
            <section className="module-card" key={module.name}>
              <h3>{module.name}</h3>

              {errors[module.name] ? (
                <p className="error">
                  {String(errors[module.name])}
                </p>
              ) : results[module.name] !== undefined ? (
                <pre>
                  {JSON.stringify(results[module.name], null, 2)}
                </pre>
              ) : (
                <p>Loading data...</p>
              )}
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}
