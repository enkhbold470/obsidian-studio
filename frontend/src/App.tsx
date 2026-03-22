import { Route, Routes } from "react-router-dom";
import { Login } from "./pages/Login";
import { Maker } from "./pages/Maker";
import { Register } from "./pages/Register";
import { RenderDetail } from "./pages/RenderDetail";
import { RendersGallery } from "./pages/RendersGallery";

const App = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route path="/u/:userId/renders/:slug" element={<RenderDetail />} />
    <Route path="/u/:userId/renders" element={<RendersGallery />} />
    <Route path="/" element={<Maker />} />
  </Routes>
);

export default App;
