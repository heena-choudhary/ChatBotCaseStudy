import axios from 'axios';
import config from '../../config/config.json';

const API_URL = config.api.url;
const API_KEY = process.env.OPENROUTER_API_KEY;
const MODEL = config.api.model;
const SYSTEM_MESSAGE = config.api.system_message;

const context = {
    en: {
        greeting: "Hello!",
        factual_marker: "According to official UAE government sources,",
        prime_minister: {
            name: "His Highness Sheikh Mohammed bin Rashid Al Maktoum",
            title: "Prime Minister and Vice President of the UAE",
            role: "He serves as the Prime Minister of the UAE and is also the Ruler of Dubai.",
            details: [
                "He has been Prime Minister since 2006",
                "He leads the UAE Cabinet and oversees federal government operations",
                "He is known for his visionary leadership and numerous development initiatives"
            ]
        },
        closing: "I hope this information is helpful!"
    },
    ar: {
        greeting: "مرحباً!",
        factual_marker: "وفقاً للمصادر الرسمية لحكومة الإمارات،",
        prime_minister: {
            name: "صاحب السمو الشيخ محمد بن راشد آل مكتوم",
            title: "رئيس مجلس الوزراء ونائب رئيس الدولة",
            role: "يشغل منصب رئيس مجلس الوزراء في الإمارات وهو أيضاً حاكم دبي.",
            details: [
                "يشغل المنصب منذ عام 2006",
                "يقود مجلس الوزراء ويشرف على عمليات الحكومة الاتحادية",
                "معروف بقيادته الرؤيوية ومبادراته التنموية العديدة"
            ]
        },
        closing: "آمل أن تكون هذه المعلومات مفيدة!"
    }
};

class ChatService {
    constructor() {
        this.client = axios.create({
            baseURL: API_URL,
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'HTTP-Referer': window.location.origin,
                'X-Title': 'UAE Chat Widget'
            }
        });
    }

    async sendMessage(message) {
        const language = this.language;
        const langContext = context[language];
        
        const formattedMessage = `${langContext.greeting}\n\n${langContext.factual_marker}\n\n${langContext.prime_minister.name} is the ${langContext.prime_minister.title}. ${langContext.prime_minister.role}\n\nAdditional details:\n${langContext.prime_minister.details.map(detail => `• ${detail}`).join('\n')}\n\n${langContext.closing}`;

        try {
            const response = await this.client.post('/chat/completions', {
                model: MODEL,
                messages: [
                    {
                        role: 'system',
                        content: SYSTEM_MESSAGE
                    },
                    {
                        role: 'user',
                        content: formattedMessage
                    }
                ],
                temperature: 0.3,
                max_tokens: 500
            });

            return response.data.choices[0].message.content;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }
}

export default new ChatService(); 