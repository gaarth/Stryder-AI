import { Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import Terminal from './pages/Terminal';
import './index.css';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/terminal" element={<Terminal />} />
    </Routes>
  );
}
