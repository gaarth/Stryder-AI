import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Terminal from './pages/Terminal';
import LandingPage from './pages/LandingPage';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/terminal" element={<Terminal />} />
      </Routes>
    </BrowserRouter>
  );
}
