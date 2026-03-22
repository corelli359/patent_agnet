import { useState } from 'react';
import { skill1API } from '../api';
import ReactMarkdown from 'react-markdown';

function Skill1() {
    const [sessionId, setSessionId] = useState('');
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [document, setDocument] = useState('');
    const [draftId, setDraftId] = useState('');

    const startSession = async () => {
        setLoading(true);
        try {
            const res = await skill1API.startConversation();
            setSessionId(res.data.data.session_id);
            setMessages([{ role: 'assistant', content: res.data.data.welcome_message }]);
        } catch (err) {
            alert('启动失败: ' + err.message);
        }
        setLoading(false);
    };

    const sendMessage = async () => {
        if (!input.trim() || !sessionId) return;

        const userMsg = { role: 'user', content: input };
        setMessages([...messages, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await skill1API.chat(sessionId, input);
            const data = res.data.data;
            setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);

            if (data.completed) {
                alert('对话完成！可以生成发明意图文档了');
            }
        } catch (err) {
            alert('发送失败: ' + err.message);
        }
        setLoading(false);
    };

    const generateDoc = async () => {
        setLoading(true);
        try {
            const res = await skill1API.generate(sessionId);
            setDocument(res.data.data.document);
            setDraftId(res.data.data.draft_id);
            alert('文档生成成功！Draft ID: ' + res.data.data.draft_id);
        } catch (err) {
            alert('生成失败: ' + err.message);
        }
        setLoading(false);
    };

    return (
        <div className="skill-page">
            <h1>Skill 1: 发明意图总结</h1>
            <p>通过多轮对话引导，生成结构化的发明意图文档</p>

            {!sessionId ? (
                <button onClick={startSession} className="btn" disabled={loading}>
                    {loading ? '启动中...' : '开始新会话'}
                </button>
            ) : (
                <div>
                    <div className="chat-box">
                        {messages.map((msg, i) => (
                            <div key={i} className={`message ${msg.role}`}>
                                <strong>{msg.role === 'user' ? '您' : 'AI'}:</strong> {msg.content}
                            </div>
                        ))}
                    </div>

                    <div className="input-group">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                            placeholder="输入您的技术创意..."
                            disabled={loading}
                        />
                        <button onClick={sendMessage} className="btn" disabled={loading || !input.trim()}>
                            发送
                        </button>
                        <button onClick={generateDoc} className="btn btn-success" disabled={loading}>
                            生成文档
                        </button>
                    </div>

                    {draftId && (
                        <div className="draft-id">
                            <strong>Draft ID:</strong> {draftId}
                            <span style={{ marginLeft: '10px', color: '#28a745' }}>✅ 可用于Skill 2</span>
                        </div>
                    )}

                    {document && (
                        <div className="document-preview">
                            <h3>生成的发明意图文档</h3>
                            <ReactMarkdown>{document}</ReactMarkdown>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default Skill1;
