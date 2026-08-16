import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { OverviewPage } from "./pages/OverviewPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { ComparePage } from "./pages/ComparePage";
import { PredictionPage } from "./pages/PredictionPage";
import { AnomaliesPage } from "./pages/AnomaliesPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { ScrapesPage } from "./pages/ScrapesPage";
import { NewsPage } from "./pages/NewsPage";
import { ChangesPage } from "./pages/ChangesPage";
import { DeskPage } from "./pages/DeskPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/desk" element={<DeskPage />} />
        <Route path="/products/:code" element={<ProductDetailPage />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/prediction" element={<PredictionPage />} />
        <Route path="/anomalies" element={<AnomaliesPage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/scrapes" element={<ScrapesPage />} />
        <Route path="/news" element={<NewsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
