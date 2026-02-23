import React, { useState } from 'react';
import Header from './components/Header';
import HomePage from './pages/HomePage.tsx';
import ResultsPage from './pages/ResultsPage.tsx';

export default function App() {
  const [currentPage, setCurrentPage] = useState<'home' | 'results'>('home');

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentPage === 'home' ? (
          <HomePage onSearch={() => setCurrentPage('results')} />
        ) : (
          <ResultsPage onBack={() => setCurrentPage('home')} />
        )}
      </main>
    </div>
  );
}
