import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { projectAPI, skill1API, skill2API, skill3API, skill4API, skill5API, skill6API } from '../api'
import './ProjectWorkbench.css'

const USER_ID = 'default_user'

const documentTabs = [
  { key: 'invention_intent_doc', label: '发明意图' },
  { key: 'search_report', label: '检索报告' },
  { key: 'disclosure_doc', label: '技术交底书' },
  { key: 'claims', label: '权利要求书' },
  { key: 'specification', label: '说明书' },
  { key: 'abstract', label: '摘要' },
  { key: 'exam_report', label: '审查报告' },
  { key: 'repair_strategies', label: '修复策略' },
  { key: 'response_opinion', label: '答复意见书' },
  { key: 'delivery_package', label: '交付包' },
]

const editableDocumentKeys = new Set([
  'invention_intent_doc',
  'disclosure_doc',
  'claims',
  'specification',
  'abstract',
  'response_opinion',
])

function ProjectWorkbench() {
  const [projects, setProjects] = useState([])
  const [activeDraftId, setActiveDraftId] = useState('')
  const [overview, setOverview] = useState(null)
  const [listLoading, setListLoading] = useState(false)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [actionKey, setActionKey] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const [createForm, setCreateForm] = useState({
    title: '',
    patent_type: '发明',
    technical_field: '',
    summary: '',
    initial_notes: '',
  })

  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState([])
  const [intentInput, setIntentInput] = useState('')

  const [searchQuery, setSearchQuery] = useState('')
  const [latestSearch, setLatestSearch] = useState(null)
  const [selectedDocKey, setSelectedDocKey] = useState('delivery_package')
  const [manualDraftId, setManualDraftId] = useState('')
  const [manualOpinionText, setManualOpinionText] = useState('')
  const [parsedIssues, setParsedIssues] = useState([])
  const [repairMode, setRepairMode] = useState('conservative')
  const [docDraft, setDocDraft] = useState('')
  const [isEditingDoc, setIsEditingDoc] = useState(false)
  const [versionItems, setVersionItems] = useState([])
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [versionDiff, setVersionDiff] = useState(null)
  const [diffLoading, setDiffLoading] = useState(false)

  const selectedDoc = overview?.documents?.[selectedDocKey] || ''
  const examinationDefects = overview?.examination?.defects || []
  const persistedRepairIssues = overview?.repair?.issues || []
  const currentRepairIssues = parsedIssues.length > 0
    ? parsedIssues
    : (persistedRepairIssues.length > 0 ? persistedRepairIssues : examinationDefects)
  const currentStrategies = overview?.repair?.strategies || []
  const repairApplication = overview?.repair?.application || null
  const selectedTab = documentTabs.find((tab) => tab.key === selectedDocKey)
  const isEditableDoc = Boolean(overview?.editable_documents?.includes(selectedDocKey) || editableDocumentKeys.has(selectedDocKey))
  const actionGuards = overview?.action_guards || {}

  const activeProjectCard = useMemo(
    () => projects.find((item) => item.draft_id === activeDraftId),
    [projects, activeDraftId]
  )

  const blockedActions = useMemo(
    () => Object.values(actionGuards).filter((item) => item && item.ready === false),
    [actionGuards]
  )

  useEffect(() => {
    refreshProjects()
  }, [])

  useEffect(() => {
    if (!activeDraftId) {
      setOverview(null)
      return
    }
    setParsedIssues([])
    setManualOpinionText('')
    refreshOverview(activeDraftId)
  }, [activeDraftId])

  useEffect(() => {
    setDocDraft(selectedDoc)
    setIsEditingDoc(false)
    setVersionDiff(null)
    if (activeDraftId && isEditableDoc) {
      loadVersions(activeDraftId, selectedDocKey)
    } else {
      setVersionItems([])
    }
  }, [activeDraftId, selectedDocKey, selectedDoc, isEditableDoc])

  const refreshProjects = async (preferredDraftId = '') => {
    setListLoading(true)
    setError('')
    try {
      const res = await projectAPI.list(USER_ID, 30)
      const items = res.data.data.items || []
      setProjects(items)

      const hasPreferred = preferredDraftId && items.some((item) => item.draft_id === preferredDraftId)
      const hasCurrent = activeDraftId && items.some((item) => item.draft_id === activeDraftId)

      if (hasPreferred) {
        setActiveDraftId(preferredDraftId)
      } else if (!hasCurrent && items[0]) {
        setActiveDraftId(items[0].draft_id)
      } else if (!items.length) {
        setActiveDraftId('')
      }
    } catch (err) {
      setError(`加载项目列表失败：${extractError(err)}`)
    } finally {
      setListLoading(false)
    }
  }

  const refreshOverview = async (draftId = activeDraftId) => {
    if (!draftId) return
    setOverviewLoading(true)
    setError('')
    try {
      const res = await projectAPI.get(draftId)
      setOverview(res.data.data)
      syncDocumentTab(res.data.data)
    } catch (err) {
      setError(`加载项目总览失败：${extractError(err)}`)
    } finally {
      setOverviewLoading(false)
    }
  }

  const syncDocumentTab = (nextOverview) => {
    const docs = nextOverview?.documents || {}
    if (docs[selectedDocKey]) return
    const firstAvailable = documentTabs.find((tab) => docs[tab.key])
    setSelectedDocKey(firstAvailable?.key || 'delivery_package')
  }

  const loadVersions = async (draftId = activeDraftId, documentKey = selectedDocKey) => {
    if (!draftId || !editableDocumentKeys.has(documentKey)) {
      setVersionItems([])
      return
    }
    setVersionsLoading(true)
    try {
      const res = await projectAPI.listVersions(draftId, documentKey, 12)
      setVersionItems(res.data.data.items || [])
    } catch (err) {
      setError(`加载版本历史失败：${extractError(err)}`)
    } finally {
      setVersionsLoading(false)
    }
  }

  const loadVersionDiff = async (versionId) => {
    if (!activeDraftId || !selectedDocKey) return
    setDiffLoading(true)
    setError('')
    try {
      const res = await projectAPI.getVersionDiff(activeDraftId, versionId, selectedDocKey, 'current')
      setVersionDiff(res.data.data)
    } catch (err) {
      setError(`加载版本差异失败：${extractError(err)}`)
    } finally {
      setDiffLoading(false)
    }
  }

  const createProject = async () => {
    setActionKey('create-project')
    setError('')
    setNotice('')
    try {
      const payload = {
        ...createForm,
        user_id: USER_ID,
      }
      const res = await projectAPI.create(payload)
      const draftId = res.data.data.draft_id
      setNotice('项目已创建，可以直接在当前工作台推进 Skill 1 对话和后续流程。')
      setCreateForm({
        title: '',
        patent_type: '发明',
        technical_field: '',
        summary: '',
        initial_notes: '',
      })
      await refreshProjects(draftId)
      setActiveDraftId(draftId)
    } catch (err) {
      setError(`创建项目失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const startIntentSession = async () => {
    setActionKey('intent-start')
    setError('')
    setNotice('')
    try {
      const res = await skill1API.startConversation(USER_ID)
      setSessionId(res.data.data.session_id)
      setMessages([{ role: 'assistant', content: res.data.data.welcome_message }])
      setNotice('发明意图会话已启动。完成几轮澄清后，可直接写回当前项目。')
    } catch (err) {
      setError(`启动发明意图会话失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const sendIntentMessage = async () => {
    if (!sessionId || !intentInput.trim()) return

    const content = intentInput.trim()
    setMessages((prev) => [...prev, { role: 'user', content }])
    setIntentInput('')
    setActionKey('intent-chat')

    try {
      const res = await skill1API.chat(sessionId, content, USER_ID)
      const data = res.data.data
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
      if (data.completed) {
        setNotice('对话轮次已满足，可以点击“写入当前项目”。')
      }
    } catch (err) {
      setError(`发送消息失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const generateIntentIntoProject = async () => {
    if (!activeDraftId || !sessionId) return
    setActionKey('intent-generate')
    setError('')
    try {
      await skill1API.generate(sessionId, USER_ID, activeDraftId)
      setSelectedDocKey('invention_intent_doc')
      setNotice('发明意图文档已写回当前项目。')
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
    } catch (err) {
      setError(`写入发明意图失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const runSearch = async () => {
    if (!searchQuery.trim()) return
    setActionKey('search')
    setError('')
    setNotice('')
    try {
      const res = await skill6API.search(searchQuery.trim(), 10, USER_ID)
      setLatestSearch(res.data.data)
      setNotice('检索已完成。确认结果后，可直接挂接到当前项目。')
    } catch (err) {
      setError(`执行检索失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const attachSearch = async () => {
    if (!activeDraftId || !latestSearch?.search_id) return
    setActionKey('attach-search')
    setError('')
    try {
      await projectAPI.attachSearch(activeDraftId, latestSearch.search_id)
      setSelectedDocKey('search_report')
      setNotice('检索快照已绑定到当前项目。')
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
    } catch (err) {
      setError(`挂接检索结果失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const parseManualOpinion = async () => {
    if (!manualOpinionText.trim()) return
    setActionKey('parse-opinion')
    setError('')
    try {
      const res = await skill5API.parseOpinion(manualOpinionText.trim())
      const issues = res.data.data.issues || []
      setParsedIssues(issues)
      setNotice(`已解析出 ${issues.length} 个问题点，可直接生成修复策略。`)
    } catch (err) {
      setError(`解析审查意见失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const generateRepairStrategies = async () => {
    if (!activeDraftId || currentRepairIssues.length === 0) return
    if (actionGuards.generate_repair_strategies && !actionGuards.generate_repair_strategies.ready) {
      setError(actionGuards.generate_repair_strategies.message)
      return
    }
    setActionKey('repair-strategies')
    setError('')
    try {
      await skill5API.generateStrategies(currentRepairIssues, activeDraftId)
      setSelectedDocKey('repair_strategies')
      setNotice('修复策略已生成并写回当前项目。')
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
    } catch (err) {
      setError(`生成修复策略失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const generateResponseOpinion = async () => {
    if (!activeDraftId || currentRepairIssues.length === 0 || currentStrategies.length === 0) return
    if (actionGuards.generate_response_opinion && !actionGuards.generate_response_opinion.ready) {
      setError(actionGuards.generate_response_opinion.message)
      return
    }
    setActionKey('repair-response')
    setError('')
    try {
      await skill5API.generateResponse(currentRepairIssues, currentStrategies, activeDraftId)
      setSelectedDocKey('response_opinion')
      setNotice('答复意见书已生成并写回当前项目。')
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
    } catch (err) {
      setError(`生成答复意见书失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const applyRepairStrategies = async (withReexamination = false) => {
    if (!activeDraftId) return
    if (actionGuards.apply_repair_strategies && !actionGuards.apply_repair_strategies.ready) {
      setError(actionGuards.apply_repair_strategies.message)
      return
    }

    setActionKey(withReexamination ? 'repair-apply-exam' : 'repair-apply')
    setError('')
    setNotice('')
    try {
      await skill5API.applyStrategies(activeDraftId, repairMode)
      if (withReexamination) {
        await skill4API.examine(activeDraftId)
        setSelectedDocKey('exam_report')
        setNotice('修复策略已落稿，并完成新一轮审查。')
      } else {
        setSelectedDocKey('claims')
        setNotice('修复策略已应用到当前文稿，并生成新的修订版本。')
      }
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
    } catch (err) {
      setError(`${withReexamination ? '应用修复并重新审查' : '应用修复策略'}失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const runProjectAction = async (key, handler, successMessage, errorPrefix, docKey = '') => {
    if (!activeDraftId) return
    const guard = {
      'generate-disclosure': actionGuards.generate_disclosure,
      'generate-drafting': actionGuards.generate_drafting,
      'run-exam': actionGuards.run_examination,
      'delivery-package': actionGuards.build_delivery_package,
    }[key]
    if (guard && guard.strict && !guard.ready) {
      setError(guard.message)
      return
    }
    setActionKey(key)
    setError('')
    try {
      await handler()
      if (docKey) setSelectedDocKey(docKey)
      setNotice(successMessage)
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
    } catch (err) {
      setError(`${errorPrefix}：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const saveEditedDocument = async () => {
    if (!activeDraftId || !isEditableDoc) return
    setActionKey('save-document')
    setError('')
    setNotice('')
    try {
      await projectAPI.updateDocument(activeDraftId, selectedDocKey, docDraft)
      setIsEditingDoc(false)
      setNotice(`${selectedTab?.label || '文档'}已保存，并生成新版本。`)
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
      await loadVersions(activeDraftId, selectedDocKey)
    } catch (err) {
      setError(`保存文档失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const cancelEditingDocument = () => {
    setDocDraft(selectedDoc)
    setIsEditingDoc(false)
  }

  const restoreDocumentVersion = async (versionId, versionNumber) => {
    if (!activeDraftId || !selectedDocKey) return
    const confirmed = window.confirm(`确认将当前文档恢复到 v${versionNumber} 吗？系统会再生成一个新版本用于记录这次恢复。`)
    if (!confirmed) return

    setActionKey('restore-document')
    setError('')
    setNotice('')
    try {
      await projectAPI.restoreVersion(activeDraftId, versionId, selectedDocKey)
      setVersionDiff(null)
      setIsEditingDoc(false)
      setNotice(`${selectedTab?.label || '文档'}已恢复到 v${versionNumber}，并生成新的恢复版本。`)
      await refreshOverview(activeDraftId)
      await refreshProjects(activeDraftId)
      await loadVersions(activeDraftId, selectedDocKey)
    } catch (err) {
      setError(`恢复版本失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const downloadDeliveryExport = async () => {
    if (!activeDraftId) return
    setActionKey('delivery-export')
    setError('')
    setNotice('')
    try {
      const res = await projectAPI.downloadDeliveryExport(activeDraftId)
      const blob = new Blob([res.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `patent-delivery-${activeDraftId}.zip`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      setNotice('交付包 ZIP 已开始下载。')
    } catch (err) {
      setError(`下载交付包失败：${extractError(err)}`)
    } finally {
      setActionKey('')
    }
  }

  const loadManualDraft = async () => {
    if (!manualDraftId.trim()) return
    setActiveDraftId(manualDraftId.trim())
    setManualDraftId('')
  }

  return (
    <div className="workbench">
      <aside className="project-sidebar">
        <div className="sidebar-panel">
          <div className="sidebar-heading">
            <div>
              <p className="sidebar-kicker">Project Console</p>
              <h2>专利项目工作台</h2>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => refreshProjects(activeDraftId)}
              disabled={listLoading}
            >
              {listLoading ? '刷新中...' : '刷新'}
            </button>
          </div>

          <div className="create-form">
            <h3>新建项目</h3>
            <input
              value={createForm.title}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="发明名称，如：一种面向风控的异常检测方法"
            />
            <div className="create-grid">
              <select
                value={createForm.patent_type}
                onChange={(e) => setCreateForm((prev) => ({ ...prev, patent_type: e.target.value }))}
              >
                <option value="发明">发明</option>
                <option value="实用新型">实用新型</option>
                <option value="外观设计">外观设计</option>
              </select>
              <input
                value={createForm.technical_field}
                onChange={(e) => setCreateForm((prev) => ({ ...prev, technical_field: e.target.value }))}
                placeholder="技术领域"
              />
            </div>
            <textarea
              rows="4"
              value={createForm.summary}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, summary: e.target.value }))}
              placeholder="一句话写清当前技术问题、业务场景与目标收益"
            />
            <textarea
              rows="4"
              value={createForm.initial_notes}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, initial_notes: e.target.value }))}
              placeholder="可补充竞品、已有方案、必须保护的关键点"
            />
            <button type="button" className="btn" onClick={createProject} disabled={actionKey === 'create-project'}>
              {actionKey === 'create-project' ? '创建中...' : '创建项目'}
            </button>
          </div>

          <div className="manual-loader">
            <h3>打开已有项目</h3>
            <div className="manual-row">
              <input
                value={manualDraftId}
                onChange={(e) => setManualDraftId(e.target.value)}
                placeholder="输入 Draft ID"
              />
              <button type="button" className="btn btn-secondary" onClick={loadManualDraft}>
                打开
              </button>
            </div>
          </div>
        </div>

        <div className="sidebar-panel sidebar-list">
          <div className="sidebar-heading compact">
            <h3>项目列表</h3>
            <span>{projects.length} 个项目</span>
          </div>
          {projects.length === 0 && !listLoading && (
            <div className="empty-hint">还没有项目。建议先创建一个项目，再用工作台推进各阶段。</div>
          )}
          <div className="project-list">
            {projects.map((item) => (
              <button
                type="button"
                key={item.draft_id}
                className={`project-card-mini ${item.draft_id === activeDraftId ? 'active' : ''}`}
                onClick={() => setActiveDraftId(item.draft_id)}
              >
                <div className="project-card-mini-top">
                  <strong>{item.title}</strong>
                  <span>{item.progress}%</span>
                </div>
                <p>{formatStage(item.current_stage)}</p>
                <div className="project-card-mini-meta">
                  <span>{item.patent_type}</span>
                  <span>质量 {item.quality_score}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="project-main">
        <div className="main-hero">
          <div>
            <p className="hero-kicker">Patent Delivery Workspace</p>
            <h1>从创意到交付包，围绕单一项目推进整条专利链路</h1>
            <p className="hero-text">
              工作台将 Skill 1-6 串成统一项目视角。你现在可以在一页内看到阶段状态、质量分、检索证据、生成文档和最终交付包。
            </p>
          </div>
          <div className="hero-status">
            <div>
              <span>当前项目</span>
              <strong>{activeProjectCard?.title || '未选择'}</strong>
            </div>
            <div>
              <span>当前阶段</span>
              <strong>{formatStage(overview?.current_stage)}</strong>
            </div>
          </div>
        </div>

        {error && <div className="status-banner error">{error}</div>}
        {notice && <div className="status-banner notice">{notice}</div>}

        {!activeDraftId && (
          <div className="workbench-empty">
            <h2>先创建或打开一个项目</h2>
            <p>创建项目后，工作台会展示阶段进度、风险和文档预览，并可直接调用发明意图、检索、交底、起草、审查和交付包生成。</p>
          </div>
        )}

        {activeDraftId && overview && (
          <>
            <div className="summary-grid">
              <div className="summary-card primary">
                <span>项目完成度</span>
                <strong>{overview.progress}%</strong>
                <p>{formatStage(overview.current_stage)}</p>
              </div>
              <div className="summary-card">
                <span>质量评分</span>
                <strong>{overview.quality_checks.score}</strong>
                <p>越高说明越接近可交付状态</p>
              </div>
              <div className="summary-card">
                <span>绑定检索</span>
                <strong>{overview.linked_search_ids.length}</strong>
                <p>用于支撑新颖性与创造性判断</p>
              </div>
              <div className="summary-card">
                <span>更新时间</span>
                <strong>{formatDate(overview.updated_at)}</strong>
                <p>项目始终以最新中间产物为准</p>
              </div>
            </div>

            <div className="stage-strip">
              {overview.stages.map((stage) => (
                <div key={stage.key} className={`stage-pill ${stage.status}`}>
                  <strong>{stage.label}</strong>
                  <span>{stage.status}</span>
                </div>
              ))}
            </div>

            <div className="action-bar">
              <button type="button" className="btn btn-secondary" onClick={() => refreshOverview()}>
                {overviewLoading ? '刷新中...' : '刷新项目'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  runProjectAction(
                    'generate-disclosure',
                    () => skill2API.generate(activeDraftId),
                    '技术交底书已生成。',
                    '生成技术交底书失败',
                    'disclosure_doc'
                  )
                }
                disabled={actionKey === 'generate-disclosure' || !actionGuards.generate_disclosure?.ready}
                title={actionGuards.generate_disclosure?.message || ''}
              >
                {actionKey === 'generate-disclosure' ? '生成中...' : '生成交底书'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  runProjectAction(
                    'generate-drafting',
                    () => skill3API.generate(activeDraftId),
                    '专利申请文件已生成。',
                    '生成专利申请文件失败',
                    'claims'
                  )
                }
                disabled={actionKey === 'generate-drafting' || !actionGuards.generate_drafting?.ready}
                title={actionGuards.generate_drafting?.message || ''}
              >
                {actionKey === 'generate-drafting' ? '起草中...' : '生成申请文件'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() =>
                  runProjectAction(
                    'run-exam',
                    () => skill4API.examine(activeDraftId),
                    '审查模拟已完成。',
                    '执行审查模拟失败',
                    'exam_report'
                  )
                }
                disabled={actionKey === 'run-exam' || !actionGuards.run_examination?.ready}
                title={actionGuards.run_examination?.message || ''}
              >
                {actionKey === 'run-exam' ? '审查中...' : '执行审查'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  runProjectAction(
                    'delivery-package',
                    () => projectAPI.buildDeliveryPackage(activeDraftId),
                    '项目交付包已生成。',
                    '生成项目交付包失败',
                    'delivery_package'
                  )
                }
                disabled={actionKey === 'delivery-package'}
                title={actionGuards.build_delivery_package?.message || ''}
              >
                {actionKey === 'delivery-package' ? '打包中...' : '生成交付包'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={downloadDeliveryExport}
                disabled={actionKey === 'delivery-export'}
              >
                {actionKey === 'delivery-export' ? '下载中...' : '下载交付 ZIP'}
              </button>
            </div>

            {blockedActions.length > 0 && (
              <div className="guard-list">
                {blockedActions.slice(0, 4).map((item) => (
                  <div key={item.label} className="guard-item">
                    <strong>{item.label}</strong>
                    <span>{item.message}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="workspace-grid">
              <div className="panel-stack">
                <section className="workspace-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="panel-kicker">Skill 1</p>
                      <h2>发明意图工作区</h2>
                    </div>
                    {!sessionId && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={startIntentSession}
                        disabled={actionKey === 'intent-start'}
                      >
                        {actionKey === 'intent-start' ? '启动中...' : '开始对话'}
                      </button>
                    )}
                  </div>
                  {!sessionId && (
                    <p className="section-text">
                      建议先通过几轮问答明确技术问题、方案主干、关键实施步骤和创新点，然后再写回当前项目。
                    </p>
                  )}
                  {sessionId && (
                    <>
                      <div className="intent-chat">
                        {messages.map((msg, index) => (
                          <div key={`${msg.role}-${index}`} className={`intent-bubble ${msg.role}`}>
                            <strong>{msg.role === 'user' ? '你' : 'AI'}</strong>
                            <p>{msg.content}</p>
                          </div>
                        ))}
                      </div>
                      <div className="intent-composer">
                        <textarea
                          rows="3"
                          value={intentInput}
                          onChange={(e) => setIntentInput(e.target.value)}
                          placeholder="补充技术场景、实施步骤、差异化点或现有方案缺陷"
                        />
                        <div className="intent-actions">
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={sendIntentMessage}
                            disabled={actionKey === 'intent-chat' || !intentInput.trim()}
                          >
                            {actionKey === 'intent-chat' ? '发送中...' : '发送消息'}
                          </button>
                          <button
                            type="button"
                            className="btn"
                            onClick={generateIntentIntoProject}
                            disabled={actionKey === 'intent-generate'}
                          >
                            {actionKey === 'intent-generate' ? '写入中...' : '写入当前项目'}
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </section>

                <section className="workspace-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="panel-kicker">Skill 6</p>
                      <h2>检索与挂接</h2>
                    </div>
                  </div>
                  <p className="section-text">
                    在这里直接跑现有技术检索。检索成功后可以一键绑定到当前项目，形成后续起草和审查的证据基线。
                  </p>
                  <div className="search-inline">
                    <input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="例如：边缘计算 模型切换 低功耗"
                    />
                    <button type="button" className="btn btn-secondary" onClick={runSearch} disabled={actionKey === 'search'}>
                      {actionKey === 'search' ? '检索中...' : '执行检索'}
                    </button>
                    <button
                      type="button"
                      className="btn"
                      onClick={attachSearch}
                      disabled={actionKey === 'attach-search' || !latestSearch?.search_id}
                    >
                      {actionKey === 'attach-search' ? '挂接中...' : '挂接到项目'}
                    </button>
                  </div>
                  {latestSearch && (
                    <div className="search-result-box">
                      <div className="search-result-summary">
                        <strong>{latestSearch.result_count} 条检索结果</strong>
                        <span>Search ID: {latestSearch.search_id}</span>
                      </div>
                      <div className="search-result-list">
                        {(latestSearch.results || []).slice(0, 5).map((item, index) => (
                          <div key={`${item.patent_number}-${index}`} className="search-result-item">
                            <strong>{index + 1}. {item.title || '无标题'}</strong>
                            <p>{item.abstract || '暂无摘要'}</p>
                            <span>{item.patent_number || 'N/A'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </section>

                <section className="workspace-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="panel-kicker">Skill 4 + Skill 5</p>
                      <h2>审查与修复闭环</h2>
                    </div>
                  </div>
                  <div className="review-summary">
                    <div className="review-chip">
                      <span>最近审查状态</span>
                      <strong>{overview?.examination?.available ? (overview.examination.status || 'unknown') : '未执行'}</strong>
                    </div>
                    <div className="review-chip">
                      <span>问题数量</span>
                      <strong>{currentRepairIssues.length}</strong>
                    </div>
                    <div className="review-chip">
                      <span>策略数量</span>
                      <strong>{currentStrategies.length}</strong>
                    </div>
                    <div className="review-chip">
                      <span>修订稿状态</span>
                      <strong>{repairApplication?.applied_at ? '已落稿' : '未落稿'}</strong>
                    </div>
                  </div>
                  <p className="section-text">
                    默认优先使用最近一次审查模拟暴露的问题。也可以粘贴外部审查意见，先解析后生成修复策略和答复意见书。
                  </p>
                  {overview?.examination?.stale && (
                    <div className="status-banner notice">申请文件已经在上一轮审查后被修订，当前审查结论已过期，建议重新审查。</div>
                  )}
                  {repairApplication?.applied_at && (
                    <div className="repair-application-box">
                      <strong>最近一次修订</strong>
                      <p>
                        {formatDate(repairApplication.applied_at)}，采用 {repairApplication.mode === 'aggressive' ? '积极方案' : '保守方案'}，
                        已应用 {repairApplication.applied_items?.length || 0} 项修改，
                        未自动落稿 {repairApplication.unresolved_items?.length || 0} 项。
                      </p>
                    </div>
                  )}
                  <div className="repair-actions">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={generateRepairStrategies}
                      disabled={
                        actionKey === 'repair-strategies'
                        || currentRepairIssues.length === 0
                        || !actionGuards.generate_repair_strategies?.ready
                      }
                      title={actionGuards.generate_repair_strategies?.message || ''}
                    >
                      {actionKey === 'repair-strategies' ? '生成中...' : '生成修复策略'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => applyRepairStrategies(false)}
                      disabled={
                        actionKey === 'repair-apply'
                        || actionKey === 'repair-apply-exam'
                        || !actionGuards.apply_repair_strategies?.ready
                      }
                      title={actionGuards.apply_repair_strategies?.message || ''}
                    >
                      {actionKey === 'repair-apply' ? '落稿中...' : '应用到文稿'}
                    </button>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => applyRepairStrategies(true)}
                      disabled={
                        actionKey === 'repair-apply'
                        || actionKey === 'repair-apply-exam'
                        || !actionGuards.apply_repair_strategies?.ready
                      }
                      title={actionGuards.apply_repair_strategies?.message || ''}
                    >
                      {actionKey === 'repair-apply-exam' ? '处理中...' : '应用并重新审查'}
                    </button>
                    <button
                      type="button"
                      className="btn"
                      onClick={generateResponseOpinion}
                      disabled={
                        actionKey === 'repair-response'
                        || currentRepairIssues.length === 0
                        || currentStrategies.length === 0
                        || !actionGuards.generate_response_opinion?.ready
                      }
                      title={actionGuards.generate_response_opinion?.message || ''}
                    >
                      {actionKey === 'repair-response' ? '生成中...' : '生成答复意见书'}
                    </button>
                  </div>
                  <div className="repair-mode-toggle">
                    <span>落稿策略</span>
                    <select value={repairMode} onChange={(e) => setRepairMode(e.target.value)}>
                      <option value="conservative">保守方案</option>
                      <option value="aggressive">积极方案</option>
                    </select>
                  </div>
                  <div className="manual-opinion-box">
                    <textarea
                      rows="4"
                      value={manualOpinionText}
                      onChange={(e) => setManualOpinionText(e.target.value)}
                      placeholder="如有正式审查意见通知书，可粘贴在此并点击解析。"
                    />
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={parseManualOpinion}
                      disabled={actionKey === 'parse-opinion' || !manualOpinionText.trim()}
                    >
                      {actionKey === 'parse-opinion' ? '解析中...' : '解析审查意见'}
                    </button>
                  </div>
                  <div className="defect-list">
                    {currentRepairIssues.length > 0 ? (
                      currentRepairIssues.map((issue, index) => (
                        <div key={`${issue.id || index}-${issue.location || ''}`} className="defect-item">
                          <div className="defect-top">
                            <strong>问题 {index + 1}</strong>
                            <span>{issue.type || '未分类'} / {issue.severity || '未标注'}</span>
                          </div>
                          <p>{issue.description || '暂无描述'}</p>
                          <small>{issue.location || '未标注位置'}</small>
                        </div>
                      ))
                    ) : (
                      <div className="empty-hint">尚无可用于修复的问题列表。先执行审查，或粘贴外部审查意见进行解析。</div>
                    )}
                  </div>
                </section>
              </div>

              <div className="panel-stack">
                <section className="workspace-panel compact-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="panel-kicker">Status</p>
                      <h2>下一步与风险</h2>
                    </div>
                  </div>
                  <div className="status-columns">
                    <div>
                      <h3>下一步动作</h3>
                      <ul className="plain-list">
                        {overview.next_actions.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h3>主要风险</h3>
                      <ul className="plain-list risks">
                        {overview.risks.length > 0 ? (
                          overview.risks.map((risk) => (
                            <li key={`${risk.level}-${risk.description}`}>
                              <strong>{risk.level.toUpperCase()}</strong> {risk.description}
                            </li>
                          ))
                        ) : (
                          <li>当前未识别到高优先级风险。</li>
                        )}
                      </ul>
                    </div>
                  </div>
                </section>

                <section className="workspace-panel compact-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="panel-kicker">Quality</p>
                      <h2>质量检查</h2>
                    </div>
                  </div>
                  <div className="quality-list">
                    {overview.quality_checks.items.map((item) => (
                      <div key={item.key} className={`quality-item ${item.status}`}>
                        <div>
                          <strong>{item.label}</strong>
                          <p>{item.detail}</p>
                        </div>
                        <span>{item.status}</span>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="workspace-panel compact-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="panel-kicker">Deliverables</p>
                      <h2>交付物状态</h2>
                    </div>
                  </div>
                  <div className="deliverable-list">
                    {overview.deliverables.map((item) => (
                      <div key={item.key} className={`deliverable-item ${item.ready ? 'ready' : 'pending'}`}>
                        <div>
                          <strong>{item.label}</strong>
                          <p>{item.detail}</p>
                        </div>
                        <span>{item.ready ? '已完成' : item.required ? '必补' : '可后补'}</span>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </div>

            <section className="workspace-panel document-panel">
              <div className="panel-heading">
                <div>
                  <p className="panel-kicker">Documents</p>
                  <h2>项目文档与版本</h2>
                </div>
              </div>
              <div className="document-tabs">
                {documentTabs.map((tab) => (
                  <button
                    type="button"
                    key={tab.key}
                    className={selectedDocKey === tab.key ? 'active' : ''}
                    onClick={() => setSelectedDocKey(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="document-toolbar">
                <div className="document-toolbar-meta">
                  <span>当前文档：{selectedTab?.label || '未选择'}</span>
                  <span>项目版本 v{overview.version}</span>
                  <span>{isEditableDoc ? '支持手工编辑' : '系统生成只读'}</span>
                </div>
                {isEditableDoc && (
                  <div className="document-toolbar-actions">
                    {isEditingDoc ? (
                      <>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={cancelEditingDocument}
                          disabled={actionKey === 'save-document'}
                        >
                          取消编辑
                        </button>
                        <button
                          type="button"
                          className="btn"
                          onClick={saveEditedDocument}
                          disabled={actionKey === 'save-document' || docDraft === selectedDoc}
                        >
                          {actionKey === 'save-document' ? '保存中...' : '保存为新版本'}
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => {
                          setDocDraft(selectedDoc)
                          setIsEditingDoc(true)
                        }}
                      >
                        编辑当前文档
                      </button>
                    )}
                  </div>
                )}
              </div>
              <div className={`document-layout ${isEditableDoc ? 'with-history' : ''}`}>
                <div className="document-stage">
                  {isEditingDoc ? (
                    <textarea
                      className="document-editor"
                      value={docDraft}
                      onChange={(e) => setDocDraft(e.target.value)}
                      placeholder="在这里直接修订当前文档内容。"
                    />
                  ) : selectedDoc ? (
                    <ReactMarkdown>{selectedDoc}</ReactMarkdown>
                  ) : (
                    <div className="empty-hint">当前标签还没有内容。可以继续推进前面的阶段，生成后会自动显示在这里。</div>
                  )}
                </div>
                {isEditableDoc && (
                  <aside className="version-sidebar">
                    <div className="version-sidebar-heading">
                      <div>
                        <strong>版本历史</strong>
                        <p>按当前文档筛选，便于回看和恢复。</p>
                      </div>
                      <span>{versionItems.length} 条</span>
                    </div>
                    {versionsLoading ? (
                      <div className="empty-hint">版本加载中...</div>
                    ) : versionItems.length > 0 ? (
                      <div className="version-list">
                        {versionItems.map((item) => (
                          <div key={item.version_id} className="version-item">
                            <div className="version-item-top">
                              <strong>v{item.version_number}</strong>
                              <span>{formatDate(item.created_at)}</span>
                            </div>
                            <p>{item.change_summary || '未填写变更说明'}</p>
                            <div className="version-item-actions">
                              <button
                                type="button"
                                className="text-btn"
                                onClick={() => loadVersionDiff(item.version_id)}
                                disabled={diffLoading}
                              >
                                {diffLoading ? '加载中...' : '查看差异'}
                              </button>
                              <button
                                type="button"
                                className="text-btn danger"
                                onClick={() => restoreDocumentVersion(item.version_id, item.version_number)}
                                disabled={actionKey === 'restore-document'}
                              >
                                恢复此版
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-hint">当前文档还没有可用的历史版本。</div>
                    )}

                    {versionDiff && (
                      <div className="version-diff">
                        <div className="version-diff-heading">
                          <strong>差异预览</strong>
                          <span>
                            v{versionDiff.base_version?.version_number} 对比 {versionDiff.compare_version?.label}
                          </span>
                        </div>
                        <pre>{versionDiff.diff || '未检测到文本差异。'}</pre>
                      </div>
                    )}
                  </aside>
                )}
              </div>
            </section>
          </>
        )}
      </section>
    </div>
  )
}

function extractError(error) {
  return error?.response?.data?.detail || error?.message || '未知错误'
}

function formatDate(value) {
  if (!value) return '未更新'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatStage(stageKey) {
  const mapping = {
    project_intake: '项目立项',
    invention_intent: '发明意图',
    prior_art_search: '现有技术检索',
    disclosure: '技术交底书',
    application_drafting: '申请文件起草',
    examination: '审查模拟',
    repair: '修复与答复',
    delivery: '交付打包',
  }
  return mapping[stageKey] || '待开始'
}

export default ProjectWorkbench
