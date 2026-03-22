import { useState } from 'react';
import { skill2API, skill3API, skill4API, skill5API, skill6API } from '../api';
import ReactMarkdown from 'react-markdown';

// Skill 2
export function Skill2() {
    const [draftId, setDraftId] = useState('');
    const [result, setResult] = useState('');
    const [loading, setLoading] = useState(false);

    const generate = async () => {
        if (!draftId.trim()) return alert('请输入Draft ID');
        setLoading(true);
        try {
            const res = await skill2API.generate(draftId);
            setResult(res.data.data.disclosure_doc);
        } catch (err) {
            alert('生成失败: ' + err.message);
        }
        setLoading(false);
    };

    return (
        <div className="skill-page">
            <h1>Skill 2: 技术交底书撰写</h1>
            <div className="input-group">
                <input value={draftId} onChange={(e) => setDraftId(e.target.value)} placeholder="输入Draft ID (来自Skill 1)" />
                <button onClick={generate} className="btn" disabled={loading}>{loading ? '生成中...' : '生成交底书'}</button>
            </div>
            {result && <div className="document-preview"><ReactMarkdown>{result}</ReactMarkdown></div>}
        </div>
    );
}

// Skill 3
export function Skill3() {
    const [draftId, setDraftId] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const generate = async () => {
        if (!draftId.trim()) return alert('请输入Draft ID');
        setLoading(true);
        try {
            const res = await skill3API.generate(draftId);
            setResult(res.data.data);
        } catch (err) {
            alert('生成失败: ' + err.message);
        }
        setLoading(false);
    };

    return (
        <div className="skill-page">
            <h1>Skill 3: 专利申请文件起草</h1>
            <div className="input-group">
                <input value={draftId} onChange={(e) => setDraftId(e.target.value)} placeholder="输入Draft ID" />
                <button onClick={generate} className="btn" disabled={loading}>{loading ? '生成中...' : '生成专利文件'}</button>
            </div>
            {result && (
                <>
                    <div className="document-preview"><h3>权利要求书</h3><ReactMarkdown>{result.claims}</ReactMarkdown></div>
                    <div className="document-preview"><h3>说明书</h3><ReactMarkdown>{result.specification}</ReactMarkdown></div>
                    <div className="document-preview"><h3>摘要</h3><ReactMarkdown>{result.abstract}</ReactMarkdown></div>
                </>
            )}
        </div>
    );
}

// Skill 4
export function Skill4() {
    const [draftId, setDraftId] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const examine = async () => {
        if (!draftId.trim()) return alert('请输入Draft ID');
        setLoading(true);
        try {
            const res = await skill4API.examine(draftId);
            setResult(res.data.data);
        } catch (err) {
            alert('审查失败: ' + err.message);
        }
        setLoading(false);
    };

    return (
        <div className="skill-page">
            <h1>Skill 4: 实质审查模拟</h1>
            <div className="input-group">
                <input value={draftId} onChange={(e) => setDraftId(e.target.value)} placeholder="输入Draft ID" />
                <button onClick={examine} className="btn" disabled={loading}>{loading ? '审查中...' : '执行审查'}</button>
            </div>
            {result && (
                <>
                    <div className="status-badge" style={{ background: result.status === 'pass' ? '#28a745' : '#dc3545' }}>
                        状态: {result.status}
                    </div>
                    <div className="document-preview"><ReactMarkdown>{result.report}</ReactMarkdown></div>
                </>
            )}
        </div>
    );
}

// Skill 5
export function Skill5() {
    const [opinionText, setOpinionText] = useState('');
    const [issues, setIssues] = useState(null);
    const [loading, setLoading] = useState(false);

    const parse = async () => {
        if (!opinionText.trim()) return alert('请输入审查意见');
        setLoading(true);
        try {
            const res = await skill5API.parseOpinion(opinionText);
            setIssues(res.data.data.issues);
        } catch (err) {
            alert('解析失败: ' + err.message);
        }
        setLoading(false);
    };

    return (
        <div className="skill-page">
            <h1>Skill 5: 专利修复</h1>
            <div className="input-group">
                <textarea value={opinionText} onChange={(e) => setOpinionText(e.target.value)} rows="10" placeholder="粘贴审查意见通知书内容..." />
                <button onClick={parse} className="btn" disabled={loading}>{loading ? '解析中...' : '解析审查意见'}</button>
            </div>
            {issues && (
                <div className="document-preview">
                    <h3>识别到 {issues.length} 个问题</h3>
                    {issues.map((issue, i) => (
                        <div key={i} className="issue-item">
                            <strong>问题 {i + 1}:</strong> {issue.description}<br />
                            <small>类型: {issue.type} | 严重程度: {issue.severity}</small>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// Skill 6
export function Skill6() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);

    const search = async () => {
        if (!query.trim()) return alert('请输入检索关键词');
        setLoading(true);
        try {
            const res = await skill6API.search(query, 10);
            setResults(res.data.data);
        } catch (err) {
            alert('检索失败: ' + err.message);
        }
        setLoading(false);
    };

    return (
        <div className="skill-page">
            <h1>Skill 6: 专利检索与分析</h1>
            <div className="input-group">
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="输入检索关键词，如：区块链 密钥管理" />
                <button onClick={search} className="btn" disabled={loading}>{loading ? '检索中...' : '开始检索'}</button>
            </div>
            {results && (
                <div className="document-preview">
                    <h3>找到 {results.result_count} 条结果</h3>
                    {results.results?.map((patent, i) => (
                        <div key={i} className="patent-card">
                            <h4>{i + 1}. {patent.title || '无标题'}</h4>
                            <p>专利号: {patent.patent_number || 'N/A'}</p>
                            {patent.link && <a href={patent.link} target="_blank">查看详情</a>}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default { Skill2, Skill3, Skill4, Skill5, Skill6 };
