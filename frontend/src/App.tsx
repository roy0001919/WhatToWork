import { useEffect, useState } from 'react'
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
  { label: string; description: string; className: string }
> = {
  eligible: {
    label: 'Eligible',
    description: '符合工作地點資格',
    className: 'status-eligible',
  },
  potential: {
    label: 'Potential',
    description: '可能符合資格，仍需確認',
    className: 'status-potential',
  },
  uncertain: {
    label: 'Uncertain',
    description: '尚無明確資格證據',
    className: 'status-uncertain',
  },
  excluded: {
    label: 'Excluded',
    description: '目前工作地點不符合限制',
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

function formatDate(value: string | null): string {
  if (!value) return 'Date unavailable'

  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

function getEvidenceLabel(type: string): string {
  return type.replaceAll('_', ' ')
}

function App() {
  const [analyses, setAnalyses] = useState<DashboardAnalysis[]>([])
  const [selectedAnalysis, setSelectedAnalysis] =
    useState<DashboardAnalysis | null>(null)

  const [counts, setCounts] = useState<Record<EligibilityStatus, number>>({
    eligible: 0,
    potential: 0,
    uncertain: 0,
    excluded: 0,
  })

  const [totalJobs, setTotalJobs] = useState(0)
  const [listTotal, setListTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<EligibilityStatus | 'all'>('all')
  const [page, setPage] = useState(0)

  const [loading, setLoading] = useState(true)
  const [statsLoading, setStatsLoading] = useState(true)
  const [error, setError] = useState('')

  // Load status counts independently from the current list filters.
  useEffect(() => {
    let cancelled = false

    async function loadStats() {
      setStatsLoading(true)

      try {
        const results = await Promise.all(
          statusOrder.map(async (status) => {
            const params = new URLSearchParams({
              eligibility_status: status,
              skip: '0',
              limit: '1',
            })
            const data = await fetchAnalyses(params)
            return [status, data.total] as const
          }),
        )

        if (cancelled) return

        const nextCounts = { ...counts }
        results.forEach(([status, count]) => {
          nextCounts[status] = count
        })

        setCounts(nextCounts)
        setTotalJobs(results.reduce((sum, [, count]) => sum + count, 0))
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
  }, [page, search, statusFilter])

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
            <div className="brand-caption">GLOBAL CAREER INTELLIGENCE</div>
          </div>
        </div>

        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="sidebar-nav">
          <a className="nav-item active" href="#overview">
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </a>
          <a className="nav-item" href="#jobs">
            <BriefcaseBusiness size={18} />
            <span>Job Discovery</span>
          </a>
        </nav>

        <div className="sidebar-divider" />

        <div className="sidebar-section-label">YOUR PROFILE</div>
        <div className="profile-card">
          <div className="profile-avatar">PH</div>
          <div className="profile-info">
            <strong>Candidate Profile</strong>
            <span><Globe2 size={12} /> Philippines</span>
          </div>
          <span className="profile-dot" />
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <span className="online-dot" />
            API connection
            <strong>Ready</strong>
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
            Workspace <span>/</span> <strong>Overview</strong>
          </div>
          <div className="topbar-right">
            <span className="topbar-date">
              <Activity size={15} />
              Live job intelligence
            </span>
            <div className="topbar-avatar">PH</div>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-section">
            <div>
              <div className="eyebrow">YOUR GLOBAL JOB SEARCH</div>
              <h1>Find where you <span>belong.</span></h1>
              <p>
                Discover international opportunities and understand your
                work-location eligibility before you apply.
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
                <h2>Eligibility overview</h2>
                <p>Work-location compatibility across your job matches</p>
              </div>
              <div className="updated-label">
                <Clock3 size={14} />
                {statsLoading ? 'Updating...' : 'Based on latest analysis'}
              </div>
            </div>

            <div className="stats-grid">
              <button
                className={`stat-card stat-total ${statusFilter === 'all' ? 'stat-selected' : ''}`}
                onClick={() => handleStatusChange('all')}
              >
                <div className="stat-topline">
                  <span className="stat-icon"><BriefcaseBusiness size={18} /></span>
                  <span className="stat-trend">ALL JOBS</span>
                </div>
                <div className="stat-value">{statsLoading ? '—' : totalJobs}</div>
                <div className="stat-label">Analyzed opportunities</div>
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
                    <span className="stat-trend">{status.toUpperCase()}</span>
                  </div>
                  <div className="stat-value">{statsLoading ? '—' : counts[status]}</div>
                  <div className="stat-label">{statusConfig[status].description}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="jobs-section" id="jobs">
            <div className="section-heading jobs-heading">
              <div>
                <h2>Job opportunities</h2>
                <p>Explore roles and review your eligibility</p>
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
                  placeholder="Search job title or company..."
                  value={search}
                  onChange={(event) => handleSearch(event.target.value)}
                />
                {search && (
                  <button
                    className="clear-search"
                    onClick={() => handleSearch('')}
                    aria-label="Clear search"
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
                  aria-label="Filter by eligibility"
                >
                  <option value="all">All eligibility</option>
                  {statusOrder.map((status) => (
                    <option key={status} value={status}>
                      {statusConfig[status].label}
                    </option>
                  ))}
                </select>
                <Filter size={14} />
              </div>
            </div>

            {error && (
              <div className="error-banner">
                <AlertCircle size={18} />
                <div>
                  <strong>Unable to load dashboard data</strong>
                  <span>{error}</span>
                  <small>
                    Make sure the FastAPI server is running at {API_BASE_URL}.
                  </small>
                </div>
              </div>
            )}

            <div className="jobs-table-wrap">
              <table className="jobs-table">
                <thead>
                  <tr>
                    <th>POSITION</th>
                    <th>LOCATION</th>
                    <th>WORK TYPE</th>
                    <th>ELIGIBILITY</th>
                    <th>POSTED</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="table-message">
                        <div className="loading-spinner" />
                        Loading opportunities...
                      </td>
                    </tr>
                  ) : analyses.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="table-message">
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
                              {analysis.job.country ?? 'Location not specified'}
                              {analysis.job.location ? ` · ${analysis.job.location}` : ''}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="work-type">
                            {analysis.job.workplace_type ?? 'Not specified'}
                          </span>
                        </td>
                        <td>
                          <span className={`status-pill ${statusConfig[analysis.eligibility_status].className}`}>
                            <span className="status-indicator" />
                            {statusConfig[analysis.eligibility_status].label}
                          </span>
                        </td>
                        <td className="date-cell">{formatDate(analysis.job.posted_at)}</td>
                        <td>
                          <button
                            className="row-action"
                            aria-label={`View ${analysis.job.title}`}
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
                Showing {analyses.length ? page * PAGE_SIZE + 1 : 0}–
                {page * PAGE_SIZE + analyses.length} of {filteredTotal} opportunities
              </span>
              <div className="pagination">
                <button
                  disabled={page === 0 || loading}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={17} />
                </button>
                <span>Page {page + 1} of {totalPages}</span>
                <button
                  disabled={page + 1 >= totalPages || loading}
                  onClick={() => setPage((current) => current + 1)}
                  aria-label="Next page"
                >
                  <ChevronRight size={17} />
                </button>
              </div>
            </div>
          </section>

          <footer className="main-footer">
            <span>© 2026 WhatToWork</span>
            <span>Helping talent work without borders.</span>
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
              <span className="detail-label">YOUR ELIGIBILITY</span>
              <span className={`status-pill ${statusConfig[selectedAnalysis.eligibility_status].className}`}>
                <span className="status-indicator" />
                {statusConfig[selectedAnalysis.eligibility_status].label}
              </span>
              <p>{selectedAnalysis.summary ?? 'No additional explanation is available.'}</p>
              <div className="confidence-row">
                <span>Analysis confidence</span>
                <strong>
                  {selectedAnalysis.confidence == null
                    ? 'Not available'
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

            <div className="detail-section">
              <h4>Location & employment</h4>
              <div className="detail-facts">
                <div><span>Country</span><strong>{selectedAnalysis.job.country ?? 'Not specified'}</strong></div>
                <div><span>Location</span><strong>{selectedAnalysis.job.location ?? 'Not specified'}</strong></div>
                <div><span>Workplace</span><strong>{selectedAnalysis.job.workplace_type ?? 'Not specified'}</strong></div>
                <div><span>Employment</span><strong>{selectedAnalysis.job.employment_type ?? 'Not specified'}</strong></div>
                <div><span>Posted</span><strong>{formatDate(selectedAnalysis.job.posted_at)}</strong></div>
              </div>
            </div>

            <div className="detail-section">
              <h4>Eligibility evidence</h4>
              {selectedEvidence.length > 0 ? (
                <div className="evidence-list">
                  {selectedEvidence.map((item, index) => (
                    <div className="evidence-item" key={`${item.type}-${index}`}>
                      <span className="evidence-type">{getEvidenceLabel(item.type)}</span>
                      <p>{item.text}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted-copy">No explicit evidence was recorded for this analysis.</p>
              )}
            </div>

            <div className="detail-note">
              <AlertCircle size={17} />
              <p>
                Eligibility is an automated assessment, not a guarantee of
                employment or visa sponsorship. Confirm the location policy
                with the employer before applying.
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
