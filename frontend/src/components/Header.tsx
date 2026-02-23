import React from 'react';
import { User } from 'lucide-react';

export default function Header() {
  return (
    <header className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center">
      <div className="flex items-center gap-2 text-brand-blue font-serif font-bold text-2xl">
        <span className="text-brand-blue">КЕМС-ЧЕМПИОНАТ</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-slate-700 font-medium">Анна С.</span>
        <div className="w-10 h-10 rounded-full bg-brand-blue text-white flex items-center justify-center">
          <User size={20} />
        </div>
      </div>
    </header>
  );
}
