import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import {
  ChatContainerRoot,
  ChatContainerContent,
} from "@/components/ui/chat-container"
import {
  Message,
  MessageContent,
  MessageActions,
  MessageAction,
} from "@/components/ui/message"
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from "@/components/ui/prompt-input"
import { ScrollButton } from "@/components/ui/scroll-button"
import { Loader } from "@/components/ui/loader"
import { FileUpload, FileUploadTrigger } from "@/components/ui/file-upload"
import { Button } from "@/components/ui/button"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { useAuth } from "@/context/AuthContext"
import { useTheme } from "@/context/ThemeContext"
import { cn } from "@/lib/utils"
import {
  ArrowUp,
  BarChart3,
  Copy,
  FileText,
  FileInput,
  Pencil,
  Plus,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react"
import {
  getConversations,
  createConversation,
  getConversationMessages,
  sendMessage,
  deleteConversation,
  updateConversation,
  uploadDocuments,
  submitFeedback,
  getGoogleAuthUrl,
  debugLogin,
  checkDebugMode,
  type Conversation,
  type Message as ApiMessage,
  type MessageResponse,
} from "@/lib/api"

interface ChatMessage extends ApiMessage {
  interactionId?: number | null
  sourceDocuments?: string[]
  isLoading?: boolean
  feedback?: boolean | null
}

interface ConversationGroup {
  period: string
  conversations: Conversation[]
}

function groupConversationsByDate(conversations: Conversation[]): ConversationGroup[] {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
  const lastMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

  const groups: { [key: string]: Conversation[] } = {
    Today: [],
    Yesterday: [],
    "Last 7 days": [],
    "Last month": [],
    Older: [],
  }

  conversations.forEach((conv) => {
    const date = new Date(conv.updated_at)
    if (date >= today) {
      groups.Today.push(conv)
    } else if (date >= yesterday) {
      groups.Yesterday.push(conv)
    } else if (date >= lastWeek) {
      groups["Last 7 days"].push(conv)
    } else if (date >= lastMonth) {
      groups["Last month"].push(conv)
    } else {
      groups.Older.push(conv)
    }
  })

  return Object.entries(groups)
    .filter(([, convs]) => convs.length > 0)
    .map(([period, convs]) => ({ period, conversations: convs }))
}

function ChatSidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onRenameConversation,
}: {
  conversations: Conversation[]
  currentConversationId?: string
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  onDeleteConversation: (id: string) => void
  onRenameConversation: (id: string, title: string) => void
}) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState("")
  const groups = groupConversationsByDate(conversations)

  const handleStartEdit = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(conv.id)
    setEditingTitle(conv.title)
  }

  const handleSaveEdit = (id: string) => {
    if (editingTitle.trim()) {
      onRenameConversation(id, editingTitle.trim())
    }
    setEditingId(null)
    setEditingTitle("")
  }

  return (
    <Sidebar>
      <SidebarHeader className="flex flex-row items-center justify-between gap-2 border-b px-2 py-4">
        <div className="flex flex-row items-center gap-2 px-2">
          <div className="bg-primary/10 size-8 rounded-md" />
          <div className="text-primary text-md font-medium tracking-tight">InfolegAI</div>
        </div>
      </SidebarHeader>
      <div className="p-4">
        <Button variant="outline" className="flex w-full items-center gap-2" onClick={onNewChat}>
          <Plus className="size-4" />
          <span>New Chat</span>
        </Button>
      </div>
      <SidebarContent className="pt-0">
        {groups.map((group) => (
          <SidebarGroup key={group.period}>
            <SidebarGroupLabel>{group.period}</SidebarGroupLabel>
            <SidebarMenu>
              {group.conversations.map((conv) => (
                <SidebarMenuItem key={conv.id}>
                  <div className="group relative flex w-full items-center">
                    {editingId === conv.id ? (
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onBlur={() => handleSaveEdit(conv.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit(conv.id)
                          if (e.key === "Escape") setEditingId(null)
                        }}
                        className="bg-background w-full rounded-md px-2 py-1.5 text-sm"
                        autoFocus
                      />
                    ) : (
                      <>
                        <SidebarMenuButton
                          isActive={currentConversationId === conv.id}
                          onClick={() => onSelectConversation(conv.id)}
                          className="flex-1 truncate pr-16"
                        >
                          <span className="truncate">{conv.title}</span>
                        </SidebarMenuButton>
                        <div className="absolute right-1 hidden items-center gap-0.5 group-hover:flex">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7"
                            onClick={(e) => handleStartEdit(conv, e)}
                          >
                            <Pencil className="size-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="hover:text-destructive size-7"
                            onClick={(e) => {
                              e.stopPropagation()
                              onDeleteConversation(conv.id)
                            }}
                          >
                            <Trash2 className="size-3" />
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>
    </Sidebar>
  )
}

function ChatContent({
  messages,
  isLoading,
  isSending,
  inputValue,
  onInputChange,
  onSendMessage,
  onFeedback,
  onFilesAdded,
  conversationTitle,
  user,
  onLogout,
  onGoogleSignIn,
  onDebugLogin,
  debugMode,
}: {
  messages: ChatMessage[]
  isLoading: boolean
  isSending: boolean
  inputValue: string
  onInputChange: (value: string) => void
  onSendMessage: () => void
  onFeedback: (interactionId: number, isPositive: boolean) => void
  onFilesAdded: (files: File[]) => void
  conversationTitle?: string
  user: { email: string; is_superuser: boolean } | null
  onLogout: () => void
  onGoogleSignIn: () => void
  onDebugLogin: () => void
  debugMode: boolean
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { theme, toggleTheme } = useTheme()
  const [localFeedback, setLocalFeedback] = useState<Record<number, boolean>>({})
  const [copiedId, setCopiedId] = useState<number | null>(null)

  // Compute feedback state: local overrides take precedence over server state
  const feedbackState = useMemo(() => {
    const state: Record<number, boolean | null> = {}
    for (const msg of messages) {
      if (msg.interactionId) {
        if (msg.interactionId in localFeedback) {
          state[msg.interactionId] = localFeedback[msg.interactionId]
        } else if (msg.feedback !== undefined && msg.feedback !== null) {
          state[msg.interactionId] = msg.feedback
        }
      }
    }
    return state
  }, [messages, localFeedback])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "u") {
        e.preventDefault()
        fileInputRef.current?.click()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  const handleCopy = async (content: string, messageIndex: number) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(messageIndex)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error("Failed to copy:", err)
    }
  }

  const handleFeedbackClick = (interactionId: number, isPositive: boolean) => {
    setLocalFeedback((prev) => ({ ...prev, [interactionId]: isPositive }))
    onFeedback(interactionId, isPositive)
  }

  return (
    <main className="flex h-full flex-col overflow-hidden">
      <header className="bg-background z-10 flex h-14 w-full shrink-0 items-center justify-between gap-2 border-b px-4">
        <div className="flex items-center gap-2">
          <SidebarTrigger className="-ml-1" />
          <div className="text-foreground truncate">{conversationTitle || "New conversation"}</div>
        </div>
        <div className="flex items-center gap-3">
          <nav className="flex items-center gap-2">
            <Link to="/documents">
              <Button variant="ghost" size="sm" className="gap-2">
                <FileText className="size-4" />
                <span className="hidden sm:inline">Documents</span>
              </Button>
            </Link>
            {user?.is_superuser && (
              <Link to="/analytics">
                <Button variant="ghost" size="sm" className="gap-2">
                  <BarChart3 className="size-4" />
                  <span className="hidden sm:inline">Analytics</span>
                </Button>
              </Link>
            )}
          </nav>
          <Button variant="ghost" size="sm" onClick={toggleTheme} className="size-9 p-0">
            {theme === "dark" ? "☀️" : "🌙"}
          </Button>
          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground hidden text-sm sm:inline">{user.email}</span>
              <Button variant="outline" size="sm" onClick={onLogout}>
                Logout
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {debugMode && (
                <Button variant="outline" size="sm" onClick={onDebugLogin}>
                  Admin
                </Button>
              )}
              <Button size="sm" onClick={onGoogleSignIn}>
                Sign in
              </Button>
            </div>
          )}
        </div>
      </header>

      <FileUpload onFilesAdded={onFilesAdded} accept=".pdf">
        <div className="relative flex-1 overflow-hidden">
          <ChatContainerRoot className="h-full">
            <ChatContainerContent className="space-y-0 px-5 py-12">
              {isLoading ? (
                <div className="flex justify-center py-8">
                  <Loader variant="dots" />
                </div>
              ) : messages.length === 0 ? (
                <div className="text-muted-foreground flex h-full items-center justify-center">
                  <div className="text-center">
                    <p className="mb-2 text-lg">Start a conversation</p>
                    <p className="text-sm">Ask questions about your uploaded documents</p>
                  </div>
                </div>
              ) : (
                messages.map((message, index) => {
                  const isAssistant = message.role === "assistant"
                  const isLastMessage = index === messages.length - 1

                  return (
                    <Message
                      key={index}
                      className={cn(
                        "mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 py-4",
                        isAssistant ? "items-start" : "items-end"
                      )}
                    >
                      {isAssistant ? (
                        <div className="group flex w-full flex-col gap-1">
                          {message.isLoading ? (
                            <Loader variant="typing" size="sm" />
                          ) : (
                            <>
                              <MessageContent
                                className="text-foreground prose flex-1 rounded-lg bg-transparent p-0"
                                markdown
                              >
                                {message.content}
                              </MessageContent>
                              {message.sourceDocuments && message.sourceDocuments.length > 0 && (
                                <div className="text-muted-foreground mt-2 text-xs">
                                  Sources: {message.sourceDocuments.join(", ")}
                                </div>
                              )}
                              <MessageActions
                                className={cn(
                                  "-ml-2 mt-1 flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100",
                                  isLastMessage && "opacity-100"
                                )}
                              >
                                <MessageAction tooltip="Copy to clipboard" delayDuration={100}>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="size-8 rounded-full"
                                    onClick={() => handleCopy(message.content, index)}
                                  >
                                    <Copy
                                      className={cn("size-4", copiedId === index && "text-green-500")}
                                    />
                                  </Button>
                                </MessageAction>
                                {message.interactionId && (
                                  <>
                                    <MessageAction tooltip="Helpful" delayDuration={100}>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className={cn(
                                          "size-8 rounded-full",
                                          feedbackState[message.interactionId] === true
                                            ? "bg-green-100 text-green-500 dark:bg-green-900/30"
                                            : ""
                                        )}
                                        onClick={() => handleFeedbackClick(message.interactionId!, true)}
                                      >
                                        <ThumbsUp className="size-4" />
                                      </Button>
                                    </MessageAction>
                                    <MessageAction tooltip="Not helpful" delayDuration={100}>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className={cn(
                                          "size-8 rounded-full",
                                          feedbackState[message.interactionId] === false
                                            ? "bg-red-100 text-red-500 dark:bg-red-900/30"
                                            : ""
                                        )}
                                        onClick={() => handleFeedbackClick(message.interactionId!, false)}
                                      >
                                        <ThumbsDown className="size-4" />
                                      </Button>
                                    </MessageAction>
                                  </>
                                )}
                              </MessageActions>
                            </>
                          )}
                        </div>
                      ) : (
                        <div className="group flex flex-col items-end gap-1">
                          <MessageContent className="justify-end bg-muted text-primary w-fit rounded-3xl px-5 py-2.5">
                            {message.content}
                          </MessageContent>
                          <MessageActions className="flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                            <MessageAction tooltip="Copy to clipboard" delayDuration={100}>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="size-8 rounded-full"
                                onClick={() => handleCopy(message.content, index)}
                              >
                                <Copy
                                  className={cn("size-4", copiedId === index && "text-green-500")}
                                />
                              </Button>
                            </MessageAction>
                          </MessageActions>
                        </div>
                      )}
                    </Message>
                  )
                })
              )}
            </ChatContainerContent>
            <div className="absolute bottom-24 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
              <ScrollButton className="shadow-sm" />
            </div>
          </ChatContainerRoot>
        </div>

        <div className="bg-background z-10 shrink-0 px-3 pb-3 md:px-5 md:pb-5">
          <div className="mx-auto max-w-3xl">
            <PromptInput
              isLoading={isSending}
              value={inputValue}
              onValueChange={onInputChange}
              onSubmit={onSendMessage}
              className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
            >
              <div className="flex flex-col">
                <PromptInputTextarea
                  placeholder="Ask a question about your documents..."
                  className="min-h-[44px] pl-4 pt-3 text-base leading-[1.3]"
                />

                <PromptInputActions className="mt-5 flex w-full items-center justify-between gap-2 px-3 pb-3">
                  <div className="flex items-center gap-2">
                    <PromptInputAction tooltip="Upload PDF (Ctrl+U)">
                      <FileUploadTrigger asChild>
                        <Button variant="outline" size="icon" className="size-9 rounded-full">
                          <FileInput className="size-4" />
                        </Button>
                      </FileUploadTrigger>
                    </PromptInputAction>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files) {
                          onFilesAdded(Array.from(e.target.files))
                          e.target.value = ""
                        }
                      }}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="icon"
                      disabled={!inputValue.trim() || isSending}
                      onClick={onSendMessage}
                      className="size-9 rounded-full"
                    >
                      {isSending ? (
                        <span className="size-3 rounded-xs bg-white" />
                      ) : (
                        <ArrowUp className="size-4" />
                      )}
                    </Button>
                  </div>
                </PromptInputActions>
              </div>
            </PromptInput>
          </div>
        </div>
      </FileUpload>
    </main>
  )
}

function WelcomeScreen() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <h2 className="mb-2 text-xl font-medium">Welcome to InfolegAI</h2>
        <p className="text-muted-foreground">Sign in to start chatting with your documents</p>
      </div>
    </div>
  )
}

export function ChatPage() {
  const { user, logout, refetch } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { conversationId } = useParams<{ conversationId?: string }>()
  const navigate = useNavigate()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [debugMode, setDebugMode] = useState(false)

  const currentConversation = conversations.find((c) => c.id === conversationId)

  useEffect(() => {
    checkDebugMode().then(setDebugMode)
  }, [])

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations()
      setConversations(data.conversations)
    } catch (error) {
      console.error("Failed to load conversations:", error)
    }
  }, [])

  const loadMessages = useCallback(async (convId: string) => {
    setIsLoading(true)
    try {
      const data = await getConversationMessages(convId)
      setMessages(data)
    } catch (error) {
      console.error("Failed to load messages:", error)
      setMessages([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (user) {
      loadConversations()
    }
  }, [user, loadConversations])

  useEffect(() => {
    if (conversationId) {
      loadMessages(conversationId)
    } else {
      setMessages([])
    }
  }, [conversationId, loadMessages])

  const handleNewConversation = async () => {
    try {
      const conv = await createConversation()
      setConversations((prev) => [conv, ...prev])
      navigate(`/chat/${conv.id}`)
    } catch (error) {
      console.error("Failed to create conversation:", error)
    }
  }

  const handleSelectConversation = (id: string) => {
    navigate(`/chat/${id}`)
  }

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (conversationId === id) {
        navigate("/")
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error)
    }
  }

  const handleRenameConversation = async (id: string, title: string) => {
    try {
      const updated = await updateConversation(id, title)
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c)))
    } catch (error) {
      console.error("Failed to rename conversation:", error)
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending) return

    let activeConversationId = conversationId

    if (!activeConversationId) {
      try {
        const conv = await createConversation(inputValue.slice(0, 50))
        setConversations((prev) => [conv, ...prev])
        activeConversationId = conv.id
        navigate(`/chat/${conv.id}`, { replace: true })
      } catch (error) {
        console.error("Failed to create conversation:", error)
        return
      }
    }

    const userMessage: ChatMessage = { role: "user", content: inputValue }
    const loadingMessage: ChatMessage = {
      role: "assistant",
      content: "",
      isLoading: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setInputValue("")
    setIsSending(true)

    try {
      const response: MessageResponse = await sendMessage(activeConversationId, userMessage.content)

      setMessages((prev) => {
        const newMessages = prev.slice(0, -1)
        return [
          ...newMessages,
          {
            role: "assistant" as const,
            content: response.answer,
            interactionId: response.interaction_id,
            sourceDocuments: response.source_documents.map((d) => d.filename),
          },
        ]
      })
    } catch (error) {
      console.error("Failed to send message:", error)
      setMessages((prev) => {
        const newMessages = prev.slice(0, -1)
        return [
          ...newMessages,
          {
            role: "assistant" as const,
            content: "Sorry, an error occurred. Please try again.",
          },
        ]
      })
    } finally {
      setIsSending(false)
    }
  }

  const handleFeedback = async (interactionId: number, isPositive: boolean) => {
    try {
      await submitFeedback(interactionId, isPositive)
    } catch (error) {
      console.error("Failed to submit feedback:", error)
    }
  }

  const handleFilesAdded = async (files: File[]) => {
    const pdfFiles = files.filter((f) => f.type === "application/pdf")
    if (pdfFiles.length === 0) {
      alert("Only PDF files are supported")
      return
    }

    try {
      const result = await uploadDocuments(pdfFiles)
      if (result.successful_uploads.length > 0) {
        alert(`Uploaded ${result.successful_uploads.length} document(s)`)
      }
      if (result.failed_uploads.length > 0) {
        alert(`Failed to upload: ${result.failed_uploads.map((f) => f.filename).join(", ")}`)
      }
    } catch (error) {
      console.error("Upload failed:", error)
      alert("Upload failed")
    }
  }

  const handleGoogleSignIn = async () => {
    try {
      const authUrl = await getGoogleAuthUrl()
      window.location.href = authUrl
    } catch (error) {
      console.error("Failed to get auth URL:", error)
    }
  }

  const handleDebugLogin = async () => {
    try {
      await debugLogin()
      await refetch()
    } catch (error) {
      console.error("Debug login failed:", error)
    }
  }

  if (!user) {
    return (
      <SidebarProvider>
        <Sidebar>
          <SidebarHeader className="flex flex-row items-center gap-2 border-b px-4 py-4">
            <div className="bg-primary/10 size-8 rounded-md" />
            <div className="text-primary text-md font-medium tracking-tight">InfolegAI</div>
          </SidebarHeader>
        </Sidebar>
        <SidebarInset>
          <header className="bg-background z-10 flex h-14 w-full shrink-0 items-center justify-between gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={toggleTheme} className="size-9 p-0">
                {theme === "dark" ? "☀️" : "🌙"}
              </Button>
              {debugMode && (
                <Button variant="outline" size="sm" onClick={handleDebugLogin}>
                  Admin Login
                </Button>
              )}
              <Button size="sm" onClick={handleGoogleSignIn}>
                Sign in with Google
              </Button>
            </div>
          </header>
          <WelcomeScreen />
        </SidebarInset>
      </SidebarProvider>
    )
  }

  return (
    <SidebarProvider>
      <ChatSidebar
        conversations={conversations}
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
      />
      <SidebarInset>
        <ChatContent
          messages={messages}
          isLoading={isLoading}
          isSending={isSending}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSendMessage={handleSendMessage}
          onFeedback={handleFeedback}
          onFilesAdded={handleFilesAdded}
          conversationTitle={currentConversation?.title}
          user={user}
          onLogout={logout}
          onGoogleSignIn={handleGoogleSignIn}
          onDebugLogin={handleDebugLogin}
          debugMode={debugMode}
        />
      </SidebarInset>
    </SidebarProvider>
  )
}
