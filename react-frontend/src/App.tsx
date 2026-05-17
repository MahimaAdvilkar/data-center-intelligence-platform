import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import GravityModel from "./pages/GravityModel";
import Optimizer from "./pages/Optimizer";
import ClusterPredictor from "./pages/ClusterPredictor";
import DataExplorer from "./pages/DataExplorer";
import AIChat from "./pages/AIChat";
import SiteScout from "./pages/SiteScout";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="gravity"   element={<GravityModel />} />
          <Route path="optimizer" element={<Optimizer />} />
          <Route path="cluster"   element={<ClusterPredictor />} />
          <Route path="explorer"  element={<DataExplorer />} />
          <Route path="ai"        element={<AIChat />} />
          <Route path="scout"     element={<SiteScout />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
