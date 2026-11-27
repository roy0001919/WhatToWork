import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  BriefcaseBusiness,
  LayoutDashboard,
  MessageSquare,
  X,
} from 'lucide-react'

import ChatPage from './pages/ChatPage'
import type { Language } from './i18n'
import Dashboard from './App.dashboard'
import './AppShell.css'

export default function App() {
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [drawerWidth, setDrawerWidth] = useState(420)
  const [language, setLanguage] = useState<Language>(() => {
    return localStorage.getItem('whattowork-language') === 'zh-TW'
      ? 'zh-TW'
      : 'en'
  })

  const resizeStart = useRef<{
    x: number
    width: number
  } | null>(null)

  useEffect(() => {
    localStorage.setItem('whattowork-language', language)
  }, [language])

  function handleResizeStart(event: React.PointerEvent<HTMLDivElement>) {
    if (window.innerWidth <= 760) return

    event.currentTarget.setPointerCapture(event.pointerId)

    resizeStart.current = {
      x: event.clientX,
      width: drawerWidth,
    }
  }

  function handleResizeMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!resizeStart.current) return

    const delta = resizeStart.current.x - event.clientX

    const nextWidth = Math.min(
      800,
      Math.max(420, resizeStart.current.width + delta),
      window.innerWidth - 24,
    )

    setDrawerWidth(nextWidth)
  }

  function handleResizeEnd() {
    resizeStart.current = null
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsChatOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-brand">
          <div className="app-brand-icon">
            <Bot size={22} />
          </div>

          <div>
            <div className="app-brand-name">WhatToWork</div>
            <div className="app-brand-caption">AI JOB SEARCH AGENT</div>
          </div>
        </div>

        <div className="app-sidebar-section">{language === 'en' ? 'WORKSPACE' : '工作區'}</div>

        <nav className="app-navigation">
          <button
            className="app-nav-item active"
            type="button"
            aria-current="page"
          >
            <LayoutDashboard size={18} />
            <span>{language === 'en' ? 'Dashboard' : '總覽儀表板'}</span>
          </button>
        </nav>

        <div className="app-sidebar-bottom">
          <div className="sidebar-profile-icon">
            <BriefcaseBusiness size={17} />
          </div>

          <div className="sidebar-profile-text">
            <strong>{language === 'en' ? 'Job Workspace' : '求職工作區'}</strong>
            <span>{language === 'en' ? 'Personal workspace' : '個人工作區'}</span>
          </div>

          <span className="sidebar-online-dot" />
        </div>
      </aside>

      <main className="app-main">
        <div className="app-main-dashboard">
          <Dashboard language={language} onLanguageChange={setLanguage} onOpenAI={() => setIsChatOpen(true)} />
        </div>
      </main>

      {!isChatOpen && (
        <button
          className="ask-ai-button"
          type="button"
          onClick={() => setIsChatOpen(true)}
          aria-label={language === "en" ? "Open AI assistant" : "開啟 AI 助理"}
        >
          <MessageSquare size={19} />
          <span>{language === 'en' ? 'Ask AI' : '詢問 AI'}</span>
        </button>
      )}

      {isChatOpen && (
        <>
          <button
            className="chat-drawer-backdrop"
            type="button"
            aria-label={language === "en" ? "Close AI assistant" : "關閉 AI 助理"}
            onClick={() => setIsChatOpen(false)}
          />

          <aside
            className="chat-drawer"
            style={{
              width: `min(${drawerWidth}px, calc(100vw - 24px))`,
            }}
            role="dialog"
            aria-modal="true"
            aria-label={language === "en" ? "WhatToWork AI Assistant" : "WhatToWork AI 助理"}
          >
            <div
              className="chat-drawer-resize-handle"
              onPointerDown={handleResizeStart}
              onPointerMove={handleResizeMove}
              onPointerUp={handleResizeEnd}
              onPointerCancel={handleResizeEnd}
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize chat panel"
            />

            <button
              className="chat-drawer-close"
              type="button"
              onClick={() => setIsChatOpen(false)}
              aria-label={language === "en" ? "Close chat" : "關閉對話"}
            >
              <X size={19} />
            </button>

            <ChatPage language={language} />
          </aside>
        </>
      )}
    </div>
  )
}
