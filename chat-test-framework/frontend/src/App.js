import React, { useState } from 'react';
import ChatWidget from './components/ChatWidget';
import './App.css';

function App() {
    const [language, setLanguage] = useState('en');

    const toggleLanguage = () => {
        setLanguage(prev => prev === 'en' ? 'ar' : 'en');
    };

    return (
        <div className="app">
            <header className="app-header">
                <h1>UAE Information Assistant</h1>
                <button 
                    onClick={toggleLanguage}
                    className="language-toggle"
                >
                    {language === 'en' ? 'العربية' : 'English'}
                </button>
            </header>
            <main className="app-main">
                <ChatWidget language={language} />
            </main>
        </div>
    );
}

export default App; 