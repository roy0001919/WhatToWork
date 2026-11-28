import { useEffect, useState } from 'react'
import type { Language } from '../i18n'
import {
  ArrowUp,
  Bot,
  Mic,
  Clock3,
} from 'lucide-react'
import './ChatPage.css'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  tasks?: string[]
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const PROFILE_ID = 1

const automationTasks = [
  {
    id: 'discover',
    title: 'Find matching jobs',
    description: 'Search global job opportunities.',
    available: true,
  },
  {
    id: 'eligibility',
    title: 'Check job eligibility',
    description: 'Check location and remote-work eligibility.',
    available: true,
  },
  {
    id: 'analyze',
    title: 'Analyze job requirements',
    description: 'Evaluate skills and experience match.',
    available: true,
  },
  {
    id: 'rank',
    title: 'Rank opportunities',
    description: 'Prioritize the best matching jobs.',
    available: true,
  },
  {
    id: 'resume',
    title: 'Prepare applications',
    description: 'Create tailored resumes and cover letters.',
    available: false,
  },
  {
    id: 'track',
    title: 'Track applications',
    description: 'Organize and monitor application progress.',
    available: false,
  },
]

interface AgentToolCallPayload {
  id?: string | null
  name: string
  arguments?: Record<string, unknown>
  result?: unknown
}

interface AgentToolResultPayload {
  id?: string | null
  name: string
  success: boolean
  result?: unknown
  error?: string | null
}

interface ChatPageProps {
  language: Language
  onAgentAction: (actions: AgentToolCallPayload[]) => void
}

export default function ChatPage({ language, onAgentAction }: ChatPageProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      role: 'assistant',
      content:
        language === 'en'
          ? 'Feel free to ask me anything about your job search. I can help you discover global opportunities, check work-location eligibility, analyze job requirements, and identify the best opportunities to apply for. Tell me what kind of role you are looking for.'
          : '有任何求職相關問題，都可以直接在這裡發問！我可以協助你搜尋全球職缺、確認工作資格、分析職缺要求，並找出最值得申請的機會。請告訴我你目前想找的工作或遇到的問題。',
    },
  ])
  const [nextId, setNextId] = useState(1)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)

  useEffect(() => {
    setMessages((current) =>
      current.map((message) =>
        message.id === 0
          ? {
              ...message,
              content:
                language === 'en'
                  ? 'Feel free to ask me anything about your job search. I can help you discover global opportunities, check work-location eligibility, analyze job requirements, and identify the best opportunities to apply for. Tell me what kind of role you are looking for.'
                  : '有任何求職相關問題，都可以直接在這裡發問！我可以協助你搜尋全球職缺、確認工作資格、分析職缺要求，並找出最值得申請的機會。請告訴我你目前想找的工作或遇到的問題。',
            }
          : message,
      ),
    )
  }, [language])

  const localizedTaskText: Record<string, { title: string; description: string }> = {
    discover: {
      title: language === 'en' ? 'Find matching jobs' : '搜尋符合條件的職缺',
      description: language === 'en' ? 'Search global job opportunities.' : '搜尋全球工作機會。',
    },
    eligibility: {
      title: language === 'en' ? 'Check job eligibility' : '確認工作資格',
      description: language === 'en' ? 'Check location and remote-work eligibility.' : '確認所在地與遠端工作的資格。',
    },
    analyze: {
      title: language === 'en' ? 'Analyze job requirements' : '分析職缺要求',
      description: language === 'en' ? 'Evaluate skills and experience match.' : '評估技能與工作經驗的符合程度。',
    },
    rank: {
      title: language === 'en' ? 'Rank opportunities' : '排序工作機會',
      description: language === 'en' ? 'Prioritize the best matching jobs.' : '優先挑選最值得申請的職缺。',
    },
    resume: {
      title: language === 'en' ? 'Prepare applications' : '準備求職文件',
      description: language === 'en' ? 'Create tailored resumes and cover letters.' : '建立客製化履歷與求職信。',
    },
    track: {
      title: language === 'en' ? 'Track applications' : '追蹤申請進度',
      description: language === 'en' ? 'Organize and monitor application progress.' : '整理並追蹤求職申請進度。',
    },
  }

  const localizedTasks = automationTasks.map((task) => ({
    ...task,
    ...localizedTaskText[task.id],
  }))

  const [selectedTasks, setSelectedTasks] = useState<string[]>([
    'discover',
    'eligibility',
    'analyze',
    'rank',
  ])

  function toggleTask(taskId: string) {
    setSelectedTasks((current) =>
      current.includes(taskId)
        ? current.filter((id) => id !== taskId)
        : [...current, taskId],
    )
  }

  async function sendMessage(value = input) {
    const content = value.trim()

    if (!content || isSending) return

    const selectedTaskNames = localizedTasks
      .filter((task) => selectedTasks.includes(task.id))
      .map((task) => task.title)

    const userMessageId = nextId
    const assistantMessageId = nextId + 1

    setMessages((current) => [
      ...current,
      {
        id: userMessageId,
        role: 'user',
        content,
        tasks: selectedTaskNames,
      },
    ])

    setNextId((current) => current + 2)
    setInput('')
    setError('')
    setIsSending(true)

    try {
      const agentMessage = selectedTaskNames.length
        ? `${content}\n\nPlease prioritize these selected tasks: ${selectedTaskNames.join(', ')}.`
        : content

      const response = await fetch(
        `${API_BASE_URL}/api/v1/agent/chat`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            profile_id: PROFILE_ID,
            message: agentMessage,
            conversation_id: conversationId || undefined,
          }),
        },
      )

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          data.detail ||
          `Agent API request failed (${response.status})`,
        )
      }

      setConversationId(data.conversation_id)

      const toolCalls =
        (data.tool_calls ?? []) as AgentToolCallPayload[]

      const toolResults =
        (data.tool_results ?? []) as AgentToolResultPayload[]

      const usedResultIndexes = new Set<number>()

      const completedActions = toolCalls.flatMap((call) => {
        const resultIndex = toolResults.findIndex((result, index) => {
          if (usedResultIndexes.has(index)) return false

          if (call.id) {
            return result.id === call.id
          }

          return !result.id && result.name === call.name
        })

        if (resultIndex === -1) return []

        usedResultIndexes.add(resultIndex)

        const matchingResult = toolResults[resultIndex]

        if (!matchingResult.success) return []

        return [{
          ...call,
          result: matchingResult.result,
        }]
      })

      if (completedActions.length > 0) {
        onAgentAction(completedActions)
      }

      setMessages((current) => [
        ...current,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: data.message,
        },
      ])
    } catch (err) {
      console.error('Agent API error:', err)

      setError(
        err instanceof Error
          ? err.message
          : language === 'en'
            ? 'Unable to connect to the AI Agent.'
            : '無法連線至 AI Agent。',
      )
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="chat-workspace">
      <header className="chat-topbar">
        <div>
          <div className="chat-breadcrumb">
            {language === 'en' ? 'Workspace' : '工作空間'} <span>/</span> <strong>{language === 'en' ? 'AI Agent' : 'AI 助理'}</strong>
          </div>
          <div className="chat-page-subtitle">
            {language === 'en' ? 'Your personal job search assistant' : '你的 AI 求職助理'}
          </div>
        </div>

        <div className="agent-status">
          <span className="agent-status-dot" />
          {language === 'en' ? 'AI Agent' : 'AI 助理'}
        </div>
      </header>

      <div className="chat-content">
        <section className="chat-main">

          {/* Automation Options */}
          <section className="automation-options">
            <div className="automation-heading">
              <div>
                <h2>{language === 'en' ? 'Automation Options' : '自動化任務'}</h2>
                <p>{language === 'en' ? 'Select the tasks you want your AI agent to handle.' : '選擇希望 AI 助理執行的任務。'}</p>
              </div>

              <div className="automation-heading-actions">
                <button
                  type="button"
                  className="automation-select-all"
                  onClick={() => {
                    const availableTaskIds = automationTasks
                      .filter((task) => task.available)
                      .map((task) => task.id)

                    const allSelected = availableTaskIds.every((id) =>
                      selectedTasks.includes(id)
                    )

                    setSelectedTasks(allSelected ? [] : availableTaskIds)
                  }}
                >
                  {automationTasks
                    .filter((task) => task.available)
                    .every((task) => selectedTasks.includes(task.id))
                    ? (language === 'en' ? 'Deselect All' : '全部取消')
                    : (language === 'en' ? 'Select All' : '全部選取')}
                </button>

                <span className="automation-selected-count">
                  {language === 'en' ? `${selectedTasks.length} selected` : `已選取 ${selectedTasks.length} 項`}
                </span>
              </div>
            </div>

            <div className="automation-grid">
              {automationTasks.map((task) => {
                const checked = selectedTasks.includes(task.id)

                return (
                  <label
                    className={`automation-option ${
                      checked ? 'selected' : ''
                    } ${!task.available ? 'coming-soon' : ''}`}
                    key={task.id}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!task.available}
                      onChange={() => toggleTask(task.id)}
                    />

                    <span className="automation-checkbox">
                      {checked ? '✓' : ''}
                    </span>

                    <span className="automation-option-copy">
                      <strong>{task.title}</strong>
                      <small>{task.description}</small>
                    </span>

                    {!task.available && (
                      <span className="automation-coming-soon">
                        <Clock3 size={11} />
                        {language === 'en' ? 'Soon' : '即將推出'}
                      </span>
                    )}
                  </label>
                )
              })}
            </div>
          </section>

          {/* Chat Messages */}
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="chat-welcome chat-welcome-empty" />
            ) : (
              <div className="chat-message-list">
                {messages.map((message) => (
                  <div
                    className={`chat-message chat-message-${message.role}`}
                    key={message.id}
                  >
                    {message.role === 'assistant' && (
                      <div className="message-avatar">
                        <Bot size={17} />
                      </div>
                    )}

                    <div className="message-bubble">
                      <div className="message-role">
                        {message.role === 'user'
                          ? (language === 'en' ? 'You' : '你')
                          : 'WhatToWork Agent'}
                      </div>

                      <p>{message.content}</p>

                      {message.role === 'user' &&
                        message.tasks &&
                        message.tasks.length > 0 && (
                          <div className="message-selected-tasks">
                            <span>{language === 'en' ? 'Selected tasks:' : '已選擇的任務：'}</span>
                            {message.tasks.map((task) => (
                              <span
                                className="message-task-tag"
                                key={task}
                              >
                                {task}
                              </span>
                            ))}
                          </div>
                        )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {isSending && (
            <div className="chat-request-status">
              {language === 'en'
                ? 'AI Agent is working...'
                : 'AI 助理正在處理你的請求...'}
            </div>
          )}

          {error && (
            <div className="chat-error" role="alert">
              {language === 'en' ? 'Request failed: ' : '請求失敗：'}
              {error}
            </div>
          )}

          {/* Chat Input */}
          <div className="chat-composer-area">
            <div className="chat-composer">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === 'Enter' &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault()
                    sendMessage()
                  }
                }}
                placeholder={language === 'en' ? 'Tell your AI agent what you want to accomplish...' : '告訴 AI 助理你想完成什麼任務...'}
                rows={2}
              />

              <div className="composer-toolbar">
                <div className="composer-tools">
                  <button
                    className="composer-tool"
                    type="button"
                    disabled
                    title={language === "en" ? "Voice input will be added in a later phase" : "語音輸入功能將於後續版本推出"}
                  >
                    <Mic size={17} />
                    <span>{language === 'en' ? 'Voice' : '語音'}</span>
                  </button>

                  <span className="composer-hint">
                    {language === 'en' ? 'Enter to send · Shift + Enter for new line' : 'Enter 送出 · Shift + Enter 換行'}
                  </span>
                </div>

                <button
                  className="composer-send"
                  type="button"
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || isSending}
                  aria-label={language === "en" ? "Send message" : "送出訊息"}
                >
                  <ArrowUp size={19} />
                </button>
              </div>
            </div>

            <p className="chat-disclaimer">
              {language === 'en'
                ? 'AI-generated responses may require verification.'
                : 'AI 產生的回覆仍建議自行確認。'}
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
