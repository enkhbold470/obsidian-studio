import { Route, Routes } from "react-router-dom";
import { Login } from "./pages/Login";
import { Maker } from "./pages/Maker";
import { Register } from "./pages/Register";

const App = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route path="/" element={<Maker />} />
  </Routes>
);

export default App;
