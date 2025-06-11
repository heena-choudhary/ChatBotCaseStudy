import React, { useState, useRef, useEffect } from 'react';
import chatService from '../services/chat';
import './ChatWidget.css';

const ChatWidget = ({ language = 'en' }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            const response = await chatService.sendMessage(userMessage, language);
            setMessages(prev => [...prev, { role: 'assistant', content: response }]);
        } catch (error) {
            console.error('Error:', error);
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                content: 'I apologize, but I encountered an error. Please try again.' 
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-widget" dir={language === 'ar' ? 'rtl' : 'ltr'}>
            <div className="chat-messages" id="response-content-container">
                {messages.map((message, index) => (
                    <div 
                        key={index} 
                        className={`message ${message.role}`}
                    >
                        <p dir="auto">{message.content}</p>
                    </div>
                ))}
                {isLoading && (
                    <div className="loading-indicator" id="loading-indicator">
                        <div className="spinner"></div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <form onSubmit={handleSubmit} className="chat-input-form">
                <input
                    type="text"
                    id="chat-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={language === 'ar' ? 'اكتب رسالتك هنا...' : 'Type your message here...'}
                    disabled={isLoading}
                />
                <button 
                    type="submit" 
                    id="send-message-button"
                    disabled={isLoading || !input.trim()}
                >
                    {language === 'ar' ? 'إرسال' : 'Send'}
                </button>
            </form>
        </div>
    );
};

export default ChatWidget; 