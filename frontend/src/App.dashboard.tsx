import { useEffect, useState } from 'react'
import type { Language } from './i18n'
import './App.css'
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  ExternalLink,
  Filter,
  Globe2,
  LayoutDashboard,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react'

type EligibilityStatus = 'eligible' | 'potential' | 'uncertain' | 'excluded'
type AnalysisType = 'all' | 'genai' | 'eligibility'

interface MatchAssessment {
  status?: string
  reason?: string
}

interface GenAIResult {
  job_category?: string
  technical_match_score?: number
  overall_match_score?: number
  experience_match?: MatchAssessment
  seniority_match?: MatchAssessment
  leadership_match?: MatchAssessment
  required_skills?: string[]
  preferred_skills?: string[]
  matched_required_skills?: string[]
  missing_required_skills?: string[]
  matched_preferred_skills?: string[]
  missing_preferred_skills?: string[]
  matched_skills?: string[]
  missing_skills?: string[]
  work_arrangement?: string
  salary_analysis?: {
    status?: string
    reason?: string
  }
  application_recommendation?: string
  recommendation_reason?: string
  summary?: string
  security_requirements?: string[]
}

interface Evidence {
  type: string
  text: string
}

interface DashboardJob {
  id: number
  title: string
  company: string
  location: string | null
  country: string | null
  workplace_type: string | null
  employment_type: string | null
  salary_min: number | null
  salary_max: number | null
  salary_currency: string | null
  source_url: string
  apply_url: string | null
  posted_at: string | null
  is_active: boolean
}

interface DashboardAnalysis {
  id: number
  job_id: number
  profile_id: number
  eligibility_status: EligibilityStatus
  technical_match_score: number | null
  summary: string | null
  confidence: number | null
  structured_result: {
    eligibility?: {
      reason?: string
      status?: EligibilityStatus
      evidence?: Evidence[]
      confidence?: number
    }
    genai?: GenAIResult
    recommendation?: {
      final_recommendation?: 'apply' | 'consider' | 'skip'
      recommendation_reason?: string
      decision?: string
      reason?: string
    } | null
  }
  analyzed_at: string
  job: DashboardJob
}

interface DashboardResponse {
  items: DashboardAnalysis[]
  total: number
  skip: number
  limit: number
}

const API_BASE_URL = 'http://127.0.0.1:8000'
const PROFILE_ID = 1
const PAGE_SIZE = 10

const statusConfig: Record<
  EligibilityStatus,
  {
    label: string
    description: string
    labelZh: string
    descriptionZh: string
    className: string
  }
> = {
  eligible: {
    label: 'Eligible',
    description: 'Meets work-location requirements',
    labelZh: '符合資格',
    descriptionZh: '符合工作地點資格',
    className: 'status-eligible',
  },
  potential: {
    label: 'Potential',
    description: 'May be eligible; further verification needed',
    labelZh: '可能符合資格',
    descriptionZh: '可能符合資格，仍需確認',
    className: 'status-potential',
  },
  uncertain: {
    label: 'Uncertain',
    description: 'Insufficient evidence to determine eligibility',
    labelZh: '尚不確定',
    descriptionZh: '尚無明確資格證據',
    className: 'status-uncertain',
  },
  excluded: {
    label: 'Excluded',
    description: 'Current work location does not meet requirements',
    labelZh: '不符合資格',
    descriptionZh: '目前工作地點不符合限制',
    className: 'status-excluded',
  },
}

const statusOrder: EligibilityStatus[] = [
  'eligible',
  'potential',
  'uncertain',
  'excluded',
]

async function fetchAnalyses(params: URLSearchParams): Promise<DashboardResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/job-analyses/profiles/${PROFILE_ID}?${params.toString()}`,
  )

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<DashboardResponse>
}

function formatDate(value: string | null, language: Language): string {
  if (!value) return language === 'en' ? 'Date unavailable' : '日期無法取得'

  return new Intl.DateTimeFormat(language === 'en' ? 'en' : 'zh-TW', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

function getEvidenceLabel(type: string, language: Language): string {
  const labels: Record<string, string> = {
    remote_policy: '遠端工作政策',
    location_requirement: '工作地點要求',
    country_requirement: '國家要求',
    work_authorization: '工作許可',
    sponsorship: '簽證贊助',
    office_location: '辦公室地點',
    employment_type: '聘僱類型',
    security_requirement: '安全要求',
  }

  if (language === 'zh-TW') {
    return labels[type] ?? type.replaceAll('_', ' ')
  }

  return type.replaceAll('_', ' ')
}

interface DashboardProps {
  language: Language
  onLanguageChange: (language: Language) => void
  onOpenAI: () => void
}

function App({ language, onLanguageChange, onOpenAI }: DashboardProps) {
  const [isLanguageMenuOpen, setIsLanguageMenuOpen] = useState(false)
  const [analyses, setAnalyses] = useState<DashboardAnalysis[]>([])
  const [recommendedJobs, setRecommendedJobs] = useState<DashboardAnalysis[]>([])
  const [selectedAnalysis, setSelectedAnalysis] =
    useState<DashboardAnalysis | null>(null)

  const [counts, setCounts] = useState<Record<EligibilityStatus, number>>({
    eligible: 0,
    potential: 0,
    uncertain: 0,
    excluded: 0,
  })

  const [totalJobs, setTotalJobs] = useState(0)
  const [, setGenaiTotal] = useState(0)
  const [listTotal, setListTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<EligibilityStatus | 'all'>('all')
  const [analysisType, setAnalysisType] = useState<AnalysisType>('all')
  const [page, setPage] = useState(0)

  const [loading, setLoading] = useState(true)
  const [statsLoading, setStatsLoading] = useState(true)
  const [error, setError] = useState('')

  // Load and rank AI-recommended jobs independently from the job list.
  useEffect(() => {
    let cancelled = false

    async function loadRecommendedJobs() {
      try {
        const params = new URLSearchParams({
          analysis_type: 'genai',
          skip: '0',
          limit: '100',
        })

        const data = await fetchAnalyses(params)

        if (cancelled) return

        const eligibilityPriority: Record<EligibilityStatus, number> = {
          eligible: 0,
          potential: 1,
          uncertain: 2,
          excluded: 3,
        }

        const recommendationPriority: Record<string, number> = {
          apply: 0,
          consider: 1,
        }

        const rankedJobs = data.items
          .filter((item) => {
            const recommendation =
              item.structured_result.recommendation?.final_recommendation

            return (
              (recommendation === 'apply' ||
                recommendation === 'consider') &&
              item.eligibility_status !== 'excluded'
            )
          })
          .sort((a, b) => {
            const recommendationA =
              a.structured_result.recommendation?.final_recommendation ?? ''
            const recommendationB =
              b.structured_result.recommendation?.final_recommendation ?? ''

            const decisionDifference =
              recommendationPriority[recommendationA] -
              recommendationPriority[recommendationB]

            if (decisionDifference !== 0) return decisionDifference

            const eligibilityDifference =
              eligibilityPriority[a.eligibility_status] -
              eligibilityPriority[b.eligibility_status]

            if (eligibilityDifference !== 0) return eligibilityDifference

            const scoreA =
              a.structured_result.genai?.overall_match_score ??
              a.structured_result.genai?.technical_match_score ??
              0

            const scoreB =
              b.structured_result.genai?.overall_match_score ??
              b.structured_result.genai?.technical_match_score ??
              0

            return scoreB - scoreA
          })
          .slice(0, 5)

        setRecommendedJobs(rankedJobs)
      } catch (err) {
        console.error('Unable to load AI recommended jobs:', err)
      }
    }

    void loadRecommendedJobs()

    return () => {
      cancelled = true
    }
  }, [])

  // Load status counts independently from the current list filters.
  useEffect(() => {
    let cancelled = false

    async function loadStats() {
      setStatsLoading(true)

      try {
        const [results, genaiData] = await Promise.all([
          Promise.all(
            statusOrder.map(async (status) => {
              const params = new URLSearchParams({
                eligibility_status: status,
                skip: '0',
                limit: '1',
              })
              const data = await fetchAnalyses(params)
              return [status, data.total] as const
            }),
          ),
          fetchAnalyses(
            new URLSearchParams({
              analysis_type: 'genai',
              skip: '0',
              limit: '1',
            }),
          ),
        ])

        if (cancelled) return

        const nextCounts = { ...counts }
        results.forEach(([status, count]) => {
          nextCounts[status] = count
        })

        setCounts(nextCounts)
        setTotalJobs(results.reduce((sum, [, count]) => sum + count, 0))
        setGenaiTotal(genaiData.total)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to load dashboard statistics.',
          )
        }
      } finally {
        if (!cancelled) setStatsLoading(false)
      }
    }

    void loadStats()

    return () => {
      cancelled = true
    }
    // Load once when the dashboard mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load the job list whenever search, status, or page changes.
  useEffect(() => {
    let cancelled = false

    async function loadJobs() {
      setLoading(true)
      setError('')

      const params = new URLSearchParams({
        skip: String(page * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      })

      params.set('analysis_type', analysisType)

      if (statusFilter !== 'all') {
        params.set('eligibility_status', statusFilter)
      }

      if (search.trim()) {
        params.set('search', search.trim())
      }

      try {
        const data = await fetchAnalyses(params)

        if (cancelled) return

        setAnalyses(data.items)
        setListTotal(data.total)
        if (selectedAnalysis) {
          const updatedSelected = data.items.find(
            (item) => item.id === selectedAnalysis.id,
          )
          if (!updatedSelected) setSelectedAnalysis(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Unable to load job listings.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void loadJobs()

    return () => {
      cancelled = true
    }
  }, [page, search, statusFilter, analysisType])

  const filteredTotal = listTotal

  const totalPages = Math.max(1, Math.ceil(filteredTotal / PAGE_SIZE))

  function handleSearch(value: string) {
    setSearch(value)
    setPage(0)
  }

  function handleStatusChange(value: EligibilityStatus | 'all') {
    setStatusFilter(value)
    setPage(0)
  }

  function handleAnalysisTypeChange(value: AnalysisType) {
    setAnalysisType(value)
    setPage(0)
  }

  const selectedGenAI = selectedAnalysis?.structured_result?.genai
  const selectedEvidence =
    selectedAnalysis?.structured_result?.eligibility?.evidence ?? []

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <BriefcaseBusiness size={21} strokeWidth={2.2} />
          </div>
          <div>
            <div className="brand-name">WhatToWork</div>
            <div className="brand-caption">{language === "en" ? "GLOBAL CAREER INTELLIGENCE" : "全球職涯情報"}</div>
          </div>
        </div>

        <div className="sidebar-section-label">{language === "en" ? "WORKSPACE" : "工作區"}</div>
        <nav className="sidebar-nav">
          <a className="nav-item active" href="#overview">
            <LayoutDashboard size={18} />
            <span>{language === "en" ? "Overview" : "總覽"}</span>
          </a>
          <a className="nav-item" href="#jobs">
            <BriefcaseBusiness size={18} />
            <span>{language === "en" ? "Job Discovery" : "職缺探索"}</span>
          </a>
        </nav>

        <div className="sidebar-divider" />

        <div className="sidebar-section-label">{language === "en" ? "YOUR PROFILE" : "個人檔案"}</div>
        <div className="profile-card">
          <div className="profile-avatar">PH</div>
          <div className="profile-info">
            <strong>{language === "en" ? "Candidate Profile" : "求職者檔案"}</strong>
            <span><Globe2 size={12} /> Philippines</span>
          </div>
          <span className="profile-dot" />
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <span className="online-dot" />
            {language === "en" ? "API connection" : "API 連線"}
            <strong>{language === "en" ? "Ready" : "就緒"}</strong>
          </div>
          <div className="sidebar-footer">
            <span>WhatToWork</span>
            <span>v0.1.0</span>
          </div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb">
            {language === "en" ? <>Workspace <span>/</span> <strong>Overview</strong></> : <>工作區 <span>/</span> <strong>總覽</strong></>}
          </div>
          <div className="topbar-right">
            <span className="topbar-date">
              <Activity size={15} />
              {language === "en" ? "Live job intelligence" : "即時職缺情報"}
            </span>

            <div className="language-menu">
              <button
                className="language-menu-button"
                type="button"
                aria-label={language === "en" ? "Change language" : "切換介面語言"}
                aria-expanded={isLanguageMenuOpen}
                onClick={() => setIsLanguageMenuOpen((open) => !open)}
              >
                <Globe2 size={19} />
              </button>

              {isLanguageMenuOpen && (
                <div className="language-menu-dropdown">
                  <button
                    className={`language-menu-option ${language === "en" ? "active" : ""}`}
                    type="button"
                    onClick={() => {
                      onLanguageChange("en")
                      setIsLanguageMenuOpen(false)
                    }}
                  >
                    English
                    {language === "en" && <span>✓</span>}
                  </button>

                  <button
                    className={`language-menu-option ${language === "zh-TW" ? "active" : ""}`}
                    type="button"
                    onClick={() => {
                      onLanguageChange("zh-TW")
                      setIsLanguageMenuOpen(false)
                    }}
                  >
                    繁體中文
                    {language === "zh-TW" && <span>✓</span>}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-section">
            <div>
              <div className="eyebrow">{language === "en" ? "YOUR GLOBAL JOB SEARCH" : "你的全球求職探索"}</div>
              <h1>{language === "en" ? <>Find where you <span>belong.</span></> : <>找到適合你的<span>職涯方向。</span></>}</h1>
              <p>
                {language === "en" ? "Discover international opportunities and understand your work-location eligibility before you apply." : "探索國際職缺，並在申請前了解自己是否符合工作地點要求。"}
              </p>
            </div>
            <div className="welcome-illustration">
              <div className="illustration-globe"><Globe2 size={38} /></div>
              <div className="illustration-orbit orbit-one" />
              <div className="illustration-orbit orbit-two" />
              <span className="orbit-dot dot-one" />
              <span className="orbit-dot dot-two" />
            </div>
          </section>

          <section className="stats-section">
            <div className="section-heading">
              <div>
                <h2>{language === "en" ? "Eligibility overview" : "工作資格總覽"}</h2>
                <p>{language === "en" ? "Work-location compatibility across your job matches" : "檢視符合你工作地點條件的職缺"}</p>
              </div>
              <div className="stats-heading-actions">
                <div className="updated-label">
                  <Clock3 size={14} />
                  {statsLoading ? (language === 'en' ? 'Updating...' : '更新中...') : (language === 'en' ? 'Based on latest analysis' : '依據最新分析結果')}
                </div>
                <button
                  className="ai-recommendation-link"
                  type="button"
                  onClick={onOpenAI}
                >
                  <Activity size={16} />
                  {language === 'en' ? 'AI Recommendations' : 'AI 推薦'}
                </button>
              </div>
            </div>

            <div className="stats-grid">
              <button
                className={`stat-card stat-total ${statusFilter === 'all' ? 'stat-selected' : ''}`}
                onClick={() => handleStatusChange('all')}
              >
                <div className="stat-topline">
                  <span className="stat-icon"><BriefcaseBusiness size={18} /></span>
                  <span className="stat-trend">{language === "en" ? "ALL JOBS" : "全部職缺"}</span>
                </div>
                <div className="stat-value">{statsLoading ? '—' : totalJobs}</div>
                <div className="stat-label">{language === "en" ? "Analyzed opportunities" : "已分析職缺"}</div>
              </button>

              {statusOrder.map((status) => (
                <button
                  key={status}
                  className={`stat-card ${statusConfig[status].className} ${statusFilter === status ? 'stat-selected' : ''}`}
                  onClick={() => handleStatusChange(status)}
                >
                  <div className="stat-topline">
                    <span className="stat-icon">
                      {status === 'eligible' && <CheckCircle2 size={18} />}
                      {status === 'potential' && <AlertCircle size={18} />}
                      {status === 'uncertain' && <CircleHelp size={18} />}
                      {status === 'excluded' && <X size={18} />}
                    </span>
                    <span className="stat-trend">{(language === "en" ? statusConfig[status].label : statusConfig[status].labelZh).toUpperCase()}</span>
                  </div>
                  <div className="stat-value">{statsLoading ? '—' : counts[status]}</div>
                  <div className="stat-label">{(language === 'en' ? statusConfig[status].description : statusConfig[status].descriptionZh)}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="recommended-section">
            <div className="section-heading recommended-heading">
              <div>
                <h2>{language === 'en' ? 'AI Recommended Jobs' : 'AI 推薦職缺'}</h2>
                <p>
                  {language === 'en'
                    ? 'Opportunities ranked by work eligibility and AI job matching'
                    : '依據工作資格與 AI 職缺匹配結果排序'}
                </p>
              </div>
              <div className="recommended-count">
                {recommendedJobs.length} / 5
              </div>
            </div>

            {recommendedJobs.length > 0 ? (
              <div className="recommended-grid">
                {recommendedJobs.map((analysis) => {
                  const recommendation =
                    analysis.structured_result.recommendation
                  const genai = analysis.structured_result.genai
                  const score =
                    genai?.overall_match_score ??
                    genai?.technical_match_score ??
                    analysis.technical_match_score
                  const location =
                    analysis.job.location ??
                    analysis.job.country ??
                    analysis.job.workplace_type ??
                    (language === 'en' ? 'Location not specified' : '未提供地點')
                  const reason =
                    recommendation?.recommendation_reason ??
                    genai?.recommendation_reason ??
                    analysis.summary ??
                    (language === 'en'
                      ? 'No recommendation explanation available.'
                      : '目前沒有推薦說明。')
                  const decision = recommendation?.final_recommendation

                  return (
                    <button
                      key={analysis.id}
                      type="button"
                      className="recommended-card"
                      onClick={() => setSelectedAnalysis(analysis)}
                    >
                      <div className="recommended-card-top">
                        <span className={`recommended-decision ${decision === 'apply' ? 'decision-apply' : 'decision-consider'}`}>
                          {decision === 'apply'
                            ? (language === 'en' ? 'Recommended to apply' : '建議申請')
                            : (language === 'en' ? 'Worth considering' : '值得考慮')}
                        </span>
                        <span className="recommended-score">
                          {score == null ? '—' : `${score}%`}
                          <small> {language === 'en' ? 'Match' : '匹配度'}</small>
                        </span>
                      </div>

                      <div className="recommended-job-title">
                        {analysis.job.title}
                      </div>
                      <div className="recommended-company">
                        {analysis.job.company}
                      </div>

                      <div className="recommended-meta">
                        <span>
                          <Globe2 size={13} />
                          {location}
                        </span>
                        <span className={`status-pill ${statusConfig[analysis.eligibility_status].className}`}>
                          {language === 'en'
                            ? statusConfig[analysis.eligibility_status].label
                            : statusConfig[analysis.eligibility_status].labelZh}
                        </span>
                      </div>

                      <p className="recommended-reason">{reason}</p>

                      <div className="recommended-card-footer">
                        {language === 'en' ? 'View AI analysis' : '查看 AI 分析'}
                        <ArrowUpRight size={15} />
                      </div>
                    </button>
                  )
                })}
              </div>
            ) : (
              <div className="recommended-empty">
                {language === 'en'
                  ? 'No eligible AI recommendations available yet.'
                  : '目前還沒有符合推薦條件的 AI 職缺。'}
              </div>
            )}
          </section>

          <section className="jobs-section" id="jobs">
            <div className="section-heading jobs-heading">
              <div>
                <h2>{language === "en" ? "Job opportunities" : "職缺列表"}</h2>
                <p>{language === "en" ? "Explore roles and review your eligibility" : "探索職位並查看你的工作資格"}</p>
              </div>
              <div className="job-count">
                <span className="count-dot" />
                {filteredTotal} opportunities
              </div>
            </div>

            <div className="toolbar">
              <div className="search-box">
                <Search size={17} />
                <input
                  type="search"
                  placeholder={language === "en" ? "Search job title or company..." : "搜尋職稱或公司..."}
                  value={search}
                  onChange={(event) => handleSearch(event.target.value)}
                />
                {search && (
                  <button
                    className="clear-search"
                    onClick={() => handleSearch('')}
                    aria-label={language === "en" ? "Clear search" : "清除搜尋"}
                  >
                    <X size={15} />
                  </button>
                )}
              </div>

              <div className="filter-control">
                <SlidersHorizontal size={16} />
                <select
                  value={statusFilter}
                  onChange={(event) =>
                    handleStatusChange(event.target.value as EligibilityStatus | 'all')
                  }
                  aria-label={language === "en" ? "Filter by eligibility" : "依工作資格篩選"}
                >
                  <option value="all">{language === "en" ? "All eligibility" : "所有資格狀態"}</option>
                  {statusOrder.map((status) => (
                    <option key={status} value={status}>
                      {(language === 'en' ? statusConfig[status].label : statusConfig[status].labelZh)}
                    </option>
                  ))}
                </select>
                <Filter size={14} />
              </div>

              <div className="filter-control">
                <Activity size={16} />
                <select
                  value={analysisType}
                  onChange={(event) =>
                    handleAnalysisTypeChange(event.target.value as AnalysisType)
                  }
                  aria-label={language === "en" ? "Filter by analysis type" : "依分析類型篩選"}
                >
                  <option value="all">{language === "en" ? "All analyses" : "所有分析"}</option>
                  <option value="genai">{language === "en" ? "AI Recommendations" : "AI 推薦"}</option>
                  <option value="eligibility">{language === "en" ? "Eligibility only" : "僅工作資格分析"}</option>
                </select>
              </div>
            </div>

            {error && (
              <div className="error-banner">
                <AlertCircle size={18} />
                <div>
                  <strong>{language === "en" ? "Unable to load dashboard data" : "無法載入儀表板資料"}</strong>
                  <span>{error}</span>
                  <small>
                    {language === "en" ? "Make sure the FastAPI server is running at" : "請確認 FastAPI 伺服器正在此網址執行："} {API_BASE_URL}.
                  </small>
                </div>
              </div>
            )}

            <div className="jobs-table-wrap">
              <table className="jobs-table">
                <thead>
                  <tr>
                    <th>{language === "en" ? "POSITION" : "職位"}</th>
                    <th>{language === "en" ? "LOCATION" : "地點"}</th>
                    <th>{language === "en" ? "WORK TYPE" : "工作方式"}</th>
                    <th>{language === "en" ? "ELIGIBILITY" : "工作資格"}</th>
                    <th>{language === "en" ? "AI MATCH" : "AI 匹配度"}</th>
                    <th>{language === "en" ? "ANALYSIS" : "分析類型"}</th>
                    <th>{language === "en" ? "POSTED" : "發布日期"}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={8} className="table-message">
                        <div className="loading-spinner" />
                        Loading opportunities...
                      </td>
                    </tr>
                  ) : analyses.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="table-message">
                        <div className="empty-state">
                          <Search size={25} />
                          <strong>No opportunities found</strong>
                          <span>Try changing your search or eligibility filter.</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    analyses.map((analysis) => (
                      <tr
                        key={analysis.id}
                        className={selectedAnalysis?.id === analysis.id ? 'row-selected' : ''}
                        onClick={() => setSelectedAnalysis(analysis)}
                      >
                        <td>
                          <div className="position-cell">
                            <div className="company-logo">
                              <Building2 size={18} />
                            </div>
                            <div className="position-info">
                              <strong>{analysis.job.title}</strong>
                              <span>{analysis.job.company}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="location-cell">
                            <Globe2 size={14} />
                            <span>
                              {analysis.job.country ?? (language === 'en' ? 'Location not specified' : '未提供地點')}
                              {analysis.job.location ? ` · ${analysis.job.location}` : ''}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="work-type">
                            {analysis.job.workplace_type ?? (language === 'en' ? 'Not specified' : '未提供')}
                          </span>
                        </td>
                        <td>
                          <span className={`status-pill ${statusConfig[analysis.eligibility_status].className}`}>
                            <span className="status-indicator" />
                            {(language === 'en' ? statusConfig[analysis.eligibility_status].label : statusConfig[analysis.eligibility_status].labelZh)}
                          </span>
                        </td>
                        <td>
                          {analysis.structured_result.genai?.technical_match_score != null ? (
                            <span className="ai-match-score">
                              {analysis.structured_result.genai.technical_match_score}%
                            </span>
                          ) : (
                            <span className="muted-copy">—</span>
                          )}
                        </td>
                        <td>
                          <span className={`analysis-type-pill ${analysis.structured_result.genai ? 'analysis-genai' : 'analysis-legacy'}`}>
                            {analysis.structured_result.genai ? (language === 'en' ? 'GenAI' : '生成式 AI') : (language === 'en' ? 'Eligibility' : '資格分析')}
                          </span>
                        </td>
                        <td className="date-cell">{formatDate(analysis.job.posted_at, language)}</td>
                        <td>
                          <button
                            className="row-action"
                            aria-label={language === "en" ? `View ${analysis.job.title}` : `查看 ${analysis.job.title}`}
                            onClick={(event) => {
                              event.stopPropagation()
                              setSelectedAnalysis(analysis)
                            }}
                          >
                            <ArrowUpRight size={17} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="table-footer">
              <span>
                {language === 'en'
                  ? `Showing ${analyses.length ? page * PAGE_SIZE + 1 : 0}–${page * PAGE_SIZE + analyses.length} of ${filteredTotal} opportunities`
                  : `顯示第 ${analyses.length ? page * PAGE_SIZE + 1 : 0} 至第 ${page * PAGE_SIZE + analyses.length} 筆，共 ${filteredTotal} 筆職缺`}
              </span>
              <div className="pagination">
                <button
                  disabled={page === 0 || loading}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  aria-label={language === "en" ? "Previous page" : "上一頁"}
                >
                  <ChevronLeft size={17} />
                </button>
                <span>{language === "en" ? `Page ${page + 1} of ${totalPages}` : `第 ${page + 1} 頁，共 ${totalPages} 頁`}</span>
                <button
                  disabled={page + 1 >= totalPages || loading}
                  onClick={() => setPage((current) => current + 1)}
                  aria-label={language === "en" ? "Next page" : "下一頁"}
                >
                  <ChevronRight size={17} />
                </button>
              </div>
            </div>
          </section>

          <footer className="main-footer">
            <span>© 2026 WhatToWork</span>
            <span>{language === "en" ? "Helping talent work without borders." : "讓人才跨越疆界，連結全球機會。"}</span>
          </footer>
        </div>
      </main>

      {selectedAnalysis && (
        <div className="detail-backdrop" onClick={() => setSelectedAnalysis(null)}>
          <aside className="detail-panel" onClick={(event) => event.stopPropagation()}>
            <div className="detail-header">
              <div>
                <span className="eyebrow">JOB ANALYSIS</span>
                <h2>Opportunity details</h2>
              </div>
              <button
                className="detail-close"
                onClick={() => setSelectedAnalysis(null)}
                aria-label="Close details"
              >
                <X size={19} />
              </button>
            </div>

            <div className="detail-company">
              <div className="company-logo large"><Building2 size={23} /></div>
              <div>
                <h3>{selectedAnalysis.job.title}</h3>
                <p>{selectedAnalysis.job.company}</p>
              </div>
            </div>

            <div className="detail-status-block">
              <span className="detail-label">{language === "en" ? "YOUR ELIGIBILITY" : "你的工作資格"}</span>
              <span className={`status-pill ${statusConfig[selectedAnalysis.eligibility_status].className}`}>
                <span className="status-indicator" />
                {(language === 'en' ? statusConfig[selectedAnalysis.eligibility_status].label : statusConfig[selectedAnalysis.eligibility_status].labelZh)}
              </span>
              <p>{selectedAnalysis.summary ?? (language === 'en' ? 'No additional explanation is available.' : '目前沒有其他說明。')}</p>
              <div className="confidence-row">
                <span>{language === "en" ? "Analysis confidence" : "分析信心度"}</span>
                <strong>
                  {selectedAnalysis.confidence == null
                    ? (language === 'en' ? 'Not available' : '無資料')
                    : `${Math.round(selectedAnalysis.confidence * 100)}%`}
                </strong>
              </div>
              {selectedAnalysis.confidence != null && (
                <div className="confidence-track">
                  <div
                    className="confidence-fill"
                    style={{ width: `${Math.max(0, Math.min(100, selectedAnalysis.confidence * 100))}%` }}
                  />
                </div>
              )}
            </div>

            {selectedGenAI && (
              <div className="detail-section ai-detail-section">
                <h4>{language === "en" ? "AI Recommendation Assessment" : "AI 推薦評估"}</h4>

                <div className="ai-score-grid">
                  <div>
                    <span>{language === "en" ? "Technical match" : "技術匹配度"}</span>
                    <strong>{selectedGenAI.technical_match_score ?? '—'}{selectedGenAI.technical_match_score != null ? '%' : ''}</strong>
                  </div>
                  <div>
                    <span>{language === "en" ? "Overall match" : "整體匹配度"}</span>
                    <strong>{selectedGenAI.overall_match_score ?? '—'}{selectedGenAI.overall_match_score != null ? '%' : ''}</strong>
                  </div>
                </div>

                <div className="ai-assessment-list">
                  {([
                    [language === 'en' ? 'Experience' : '經驗匹配', selectedGenAI.experience_match],
                    [language === 'en' ? 'Seniority' : '資歷匹配', selectedGenAI.seniority_match],
                    [language === 'en' ? 'Leadership' : '領導能力', selectedGenAI.leadership_match],
                  ] as const).map(([label, result]) => result && (
                    <div className="ai-assessment-item" key={label}>
                      <div>
                        <strong>{label}</strong>
                        <span className={`ai-match-status status-${result.status ?? 'unknown'}`}>
                          {result.status ?? 'unknown'}
                        </span>
                      </div>
                      {result.reason && <p>{result.reason}</p>}
                    </div>
                  ))}
                </div>

                <div className="ai-recommendation">
                  <span className="detail-label">{language === "en" ? "AI APPLICATION RECOMMENDATION" : "AI 申請建議"}</span>
                  <strong className={`recommendation-${(selectedGenAI.application_recommendation ?? 'unknown').toLowerCase()}`}>
                    {(selectedGenAI.application_recommendation ?? (language === 'en' ? 'Not available' : '無資料')).toUpperCase()}
                  </strong>
                  {selectedGenAI.recommendation_reason && (
                    <p>{selectedGenAI.recommendation_reason}</p>
                  )}
                </div>

                <div className="ai-skill-group">
                  <strong>{language === "en" ? "Matched required skills" : "符合的必要技能"}</strong>
                  <div className="skill-tags">
                    {(selectedGenAI.matched_required_skills ?? []).map((skill) => (
                      <span className="skill-tag skill-matched" key={skill}>{skill}</span>
                    ))}
                    {(selectedGenAI.matched_required_skills ?? []).length === 0 && (
                      <span className="muted-copy">{language === "en" ? "No matched required skills recorded." : "尚未記錄符合的必要技能。"}</span>
                    )}
                  </div>
                </div>

                <div className="ai-skill-group">
                  <strong>{language === "en" ? "Missing required skills" : "缺少的必要技能"}</strong>
                  <div className="skill-tags">
                    {(selectedGenAI.missing_required_skills ?? []).map((skill) => (
                      <span className="skill-tag skill-missing" key={skill}>{skill}</span>
                    ))}
                    {(selectedGenAI.missing_required_skills ?? []).length === 0 && (
                      <span className="muted-copy">{language === "en" ? "No missing required skills recorded." : "尚未記錄缺少的必要技能。"}</span>
                    )}
                  </div>
                </div>

                {selectedGenAI.salary_analysis && (
                  <div className="ai-extra-fact">
                    <strong>Salary analysis · {selectedGenAI.salary_analysis.status ?? 'unknown'}</strong>
                    {selectedGenAI.salary_analysis.reason && <p>{selectedGenAI.salary_analysis.reason}</p>}
                  </div>
                )}

                {selectedGenAI.security_requirements && selectedGenAI.security_requirements.length > 0 && (
                  <div className="ai-extra-fact">
                    <strong>{language === "en" ? "Security requirements" : "安全要求"}</strong>
                    <ul>
                      {selectedGenAI.security_requirements.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="detail-section">
              <h4>{language === "en" ? "Location & employment" : "工作地點與聘用資訊"}</h4>
              <div className="detail-facts">
                <div><span>{language === "en" ? "Country" : "國家"}</span><strong>{selectedAnalysis.job.country ?? (language === "en" ? "Not specified" : "未提供")}</strong></div>
                <div><span>{language === "en" ? "Location" : "地點"}</span><strong>{selectedAnalysis.job.location ?? (language === "en" ? "Not specified" : "未提供")}</strong></div>
                <div><span>{language === "en" ? "Workplace" : "工作模式"}</span><strong>{selectedAnalysis.job.workplace_type ?? (language === "en" ? "Not specified" : "未提供")}</strong></div>
                <div><span>{language === "en" ? "Employment" : "聘用類型"}</span><strong>{selectedAnalysis.job.employment_type ?? (language === "en" ? "Not specified" : "未提供")}</strong></div>
                <div><span>{language === "en" ? "Posted" : "發布日期"}</span><strong>{formatDate(selectedAnalysis.job.posted_at, language)}</strong></div>
              </div>
            </div>

            <div className="detail-section">
              <h4>{language === "en" ? "Eligibility evidence" : "資格判斷依據"}</h4>
              {selectedEvidence.length > 0 ? (
                <div className="evidence-list">
                  {selectedEvidence.map((item, index) => (
                    <div className="evidence-item" key={`${item.type}-${index}`}>
                      <span className="evidence-type">{getEvidenceLabel(item.type, language)}</span>
                      <p>{item.text}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted-copy">{language === "en" ? "No explicit evidence was recorded for this analysis." : "此分析尚未記錄明確的判斷依據。"}</p>
              )}
            </div>

            <div className="detail-note">
              <AlertCircle size={17} />
              <p>
                {language === 'en'
                  ? 'Eligibility is an automated assessment, not a guarantee of employment or visa sponsorship. Confirm the location policy with the employer before applying.'
                  : '工作資格判斷為自動化評估，並不保證錄取或取得簽證贊助。申請前請向雇主確認工作地點政策。'}
              </p>
            </div>

            <div className="detail-actions">
              {selectedAnalysis.job.apply_url && (
                <a
                  className="apply-button"
                  href={selectedAnalysis.job.apply_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  View application <ExternalLink size={16} />
                </a>
              )}
              <a
                className="source-link"
                href={selectedAnalysis.job.source_url}
                target="_blank"
                rel="noreferrer"
              >
                View original listing <ArrowUpRight size={15} />
              </a>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}

export default App
