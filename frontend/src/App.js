import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import CallDetails from "./pages/CallDetails";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/call/:callId" element={<CallDetails />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;