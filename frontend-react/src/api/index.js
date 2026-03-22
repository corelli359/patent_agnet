import axios from 'axios';

const isLocalDev = typeof window !== 'undefined'
    && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    && ['5173', '4173'].includes(window.location.port);

const API_BASE = import.meta.env.VITE_API_BASE || (isLocalDev ? 'http://localhost:8000/api/v1' : '/api/v1');

// Skill 1: 发明意图
export const skill1API = {
    startConversation: (user_id = 'default_user') =>
        axios.post(`${API_BASE}/skills/invention-intent/start`, { user_id }),

    chat: (session_id, message, user_id = 'default_user') =>
        axios.post(`${API_BASE}/skills/invention-intent/chat`, { session_id, message, user_id }),

    generate: (session_id, user_id = 'default_user', draft_id = null) =>
        axios.post(`${API_BASE}/skills/invention-intent/generate`, { session_id, user_id, draft_id })
};

// Skill 2: 技术交底书
export const skill2API = {
    generate: (draft_id) =>
        axios.post(`${API_BASE}/skills/disclosure-writing/generate`, { draft_id })
};

// Skill 3: 专利起草
export const skill3API = {
    generate: (draft_id) =>
        axios.post(`${API_BASE}/skills/patent-drafting/generate`, { draft_id })
};

// Skill 4: 实质审查
export const skill4API = {
    examine: (draft_id) =>
        axios.post(`${API_BASE}/skills/examination/examine`, { draft_id })
};

// Skill 5: 专利修复
export const skill5API = {
    parseOpinion: (opinion_text) =>
        axios.post(`${API_BASE}/skills/repair/parse-opinion`, { opinion_text }),

    generateStrategies: (issues, draft_id) =>
        axios.post(`${API_BASE}/skills/repair/generate-strategies`, { issues, draft_id }),

    generateResponse: (issues, strategies, draft_id) =>
        axios.post(`${API_BASE}/skills/repair/generate-response`, { issues, strategies, draft_id }),

    applyStrategies: (draft_id, mode = 'conservative') =>
        axios.post(`${API_BASE}/skills/repair/apply-strategies`, { draft_id, mode })
};

// Skill 6: 专利检索
export const skill6API = {
    search: (query, max_results = 10, user_id = 'default_user') =>
        axios.post(`${API_BASE}/search`, { query, max_results, user_id })
};

export const projectAPI = {
    list: (user_id = 'default_user', limit = 20) =>
        axios.get(`${API_BASE}/projects`, { params: { user_id, limit } }),

    create: (payload) =>
        axios.post(`${API_BASE}/projects`, payload),

    get: (draft_id) =>
        axios.get(`${API_BASE}/projects/${draft_id}`),

    updateDocument: (draft_id, document_key, content, change_summary = '') =>
        axios.put(`${API_BASE}/projects/${draft_id}/documents/${document_key}`, { content, change_summary }),

    listVersions: (draft_id, document_key = '', limit = 20) =>
        axios.get(`${API_BASE}/projects/${draft_id}/versions`, { params: { document_key, limit } }),

    getVersionDiff: (draft_id, version_id, document_key, compare_target = 'current') =>
        axios.get(`${API_BASE}/projects/${draft_id}/versions/${version_id}/diff`, {
            params: { document_key, compare_target },
        }),

    restoreVersion: (draft_id, version_id, document_key = '', change_summary = '') =>
        axios.post(`${API_BASE}/projects/${draft_id}/versions/${version_id}/restore`, { document_key, change_summary }),

    attachSearch: (draft_id, search_id) =>
        axios.post(`${API_BASE}/projects/${draft_id}/attach-search`, { search_id }),

    buildDeliveryPackage: (draft_id) =>
        axios.get(`${API_BASE}/projects/${draft_id}/delivery-package`),

    downloadDeliveryExport: (draft_id) =>
        axios.get(`${API_BASE}/projects/${draft_id}/delivery-export`, { responseType: 'blob' })
};

export default {
    skill1: skill1API,
    skill2: skill2API,
    skill3: skill3API,
    skill4: skill4API,
    skill5: skill5API,
    skill6: skill6API,
    project: projectAPI
};
