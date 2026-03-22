import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Skill1 from './pages/Skill1'
import { Skill2, Skill3, Skill4, Skill5, Skill6 } from './pages/Skills'
import ProjectWorkbench from './pages/ProjectWorkbench'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="nav">
          <div className="nav-container">
            <Link to="/" className="nav-logo">Patent Expert System</Link>
            <div className="nav-links">
              <Link to="/workspace">项目工作台</Link>
              <Link to="/skill1">Skill 1</Link>
              <Link to="/skill2">Skill 2</Link>
              <Link to="/skill3">Skill 3</Link>
              <Link to="/skill4">Skill 4</Link>
              <Link to="/skill5">Skill 5</Link>
              <Link to="/skill6">Skill 6</Link>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/workspace" element={<ProjectWorkbench />} />
            <Route path="/skill1" element={<Skill1 />} />
            <Route path="/skill2" element={<Skill2 />} />
            <Route path="/skill3" element={<Skill3 />} />
            <Route path="/skill4" element={<Skill4 />} />
            <Route path="/skill5" element={<Skill5 />} />
            <Route path="/skill6" element={<Skill6 />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
