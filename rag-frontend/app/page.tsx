"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Paperclip, FileText, Bot, User, Loader2, Sun, Moon, Trash2, RefreshCcw } from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import axiosInstance from "@/lib/axios"

interface Message {
  id: string
  type: "user" | "bot" | "system"
  content: string
  timestamp: Date
}

interface UploadResponse {
  message: string
}

interface QueryResponse {
  answer: string
}

type UploadedDoc = {
  doc_id: string
  filename: string
  uploaded_at?: number
  chunk_count?: number
}

export default function ChatInterface() {
  const { theme, toggleTheme } = useTheme()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "system",
      content: "Welcome! Upload a PDF document to get started, then ask me questions about it.",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [docs, setDocs] = useState<UploadedDoc[]>([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const refreshDocs = async () => {
    setDocsLoading(true)
    try {
      const res = await axiosInstance.get<{ documents: UploadedDoc[] }>("/rag/documents")
      setDocs(res.data.documents ?? [])
    } catch (e) {
      console.error(e)
    } finally {
      setDocsLoading(false)
    }
  }

  useEffect(() => {
    refreshDocs()
  }, [])

  const addMessage = (type: "user" | "bot" | "system", content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, newMessage])
  }


  const handleFileUpload = async (file: File) => {
    if (!file || file.type !== "application/pdf") {
      addMessage("system", "Please select a valid PDF file.")
      return
    }

    setIsUploading(true)
    addMessage("user", `📄 Uploading: ${file.name}`)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await axiosInstance.post<UploadResponse>("/rag/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })

      addMessage(
        "bot",
        `✅ Document "${file.name}" has been uploaded and processed successfully! You can now ask questions about its content.`,
      )
      refreshDocs()
    } catch (error) {
      console.error(error)
      addMessage("bot", "❌ Failed to upload document. Please try again.")
    } finally {
      setIsUploading(false)
    }
  }

  const handleDeleteDoc = async (doc: UploadedDoc) => {
    setDeletingDocId(doc.doc_id)
    try {
      await axiosInstance.delete(`/rag/documents/${encodeURIComponent(doc.doc_id)}`)
      setDocs((prev) => prev.filter((d) => d.doc_id !== doc.doc_id))
      addMessage("system", `🗑️ Deleted "${doc.filename}"`)
    } catch (e) {
      console.error(e)
      addMessage("system", `❌ Failed to delete "${doc.filename}"`)
    } finally {
      setDeletingDocId(null)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileUpload(file)
    }
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return
  
    const userMessage = input.trim()
    setInput("")
    addMessage("user", userMessage)
    setIsLoading(true)
  
    try {
      const formData = new FormData()
      formData.append("query", userMessage)
  
      const response = await axiosInstance.post<QueryResponse>("/rag/query", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })
  
      addMessage("bot", response.data.answer)
    } catch (error) {
      console.error(error)
      addMessage("bot", "Sorry, I encountered an error processing your question. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className={`flex h-screen ${theme === "dark" ? "bg-[#151515]" : "bg-gray-50"}`}>
      {/* Left Sidebar */}
      <div
        className={`w-[320px] shrink-0 border-r ${theme === "dark" ? "border-gray-800 bg-[#121212]" : "border-gray-200 bg-white"
          }`}
      >
        <div className="px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className={`text-sm font-semibold tracking-wide ${theme === "dark" ? "text-gray-100" : "text-gray-900"}`}>
                Documents
              </div>
              <div className={`text-xs mt-1 ${theme === "dark" ? "text-gray-400" : "text-gray-500"}`}>
                Stored in Pinecone • {docs.length} total
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={refreshDocs}
              disabled={docsLoading}
              className={`${theme === "dark" ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
            >
              <RefreshCcw className={`w-4 h-4 ${docsLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>

        <ScrollArea className="h-[calc(100vh-88px)] px-3 pb-5">
          <div className="space-y-2">
            {docs.length === 0 ? (
              <div className={`px-3 py-6 text-sm ${theme === "dark" ? "text-gray-400" : "text-gray-600"}`}>
                No documents yet. Upload a PDF to populate this list.
              </div>
            ) : (
              docs.map((doc) => {
                const when = doc.uploaded_at ? new Date(doc.uploaded_at * 1000) : null
                return (
                  <div
                    key={doc.doc_id}
                    className={`group rounded-xl border p-3 ${theme === "dark"
                        ? "border-gray-800 bg-gradient-to-b from-[#171717] to-[#121212]"
                        : "border-gray-200 bg-gradient-to-b from-white to-gray-50"
                      }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div
                            className={`h-8 w-8 rounded-lg flex items-center justify-center ${theme === "dark" ? "bg-gray-800" : "bg-gray-100"
                              }`}
                          >
                            <FileText className={`w-4 h-4 ${theme === "dark" ? "text-gray-200" : "text-gray-700"}`} />
                          </div>
                          <div className="min-w-0">
                            <div
                              className={`text-sm font-medium truncate ${theme === "dark" ? "text-gray-100" : "text-gray-900"}`}
                              title={doc.filename}
                            >
                              {doc.filename}
                            </div>
                            <div className={`text-[11px] mt-0.5 ${theme === "dark" ? "text-gray-400" : "text-gray-500"}`}>
                              {doc.chunk_count ? `${doc.chunk_count} chunks` : "—"}{when ? ` • ${when.toLocaleString()}` : ""}
                            </div>
                          </div>
                        </div>
                      </div>

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteDoc(doc)}
                        disabled={deletingDocId === doc.doc_id}
                        className={`opacity-100 md:opacity-0 md:group-hover:opacity-100 transition ${theme === "dark"
                            ? "text-gray-400 hover:text-red-300 hover:bg-red-950/30"
                            : "text-gray-500 hover:text-red-600 hover:bg-red-50"
                          }`}
                        title="Delete document"
                      >
                        {deletingDocId === doc.doc_id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Main Column */}
      <div className="flex flex-col flex-1">
      {/* Header */}
      <div
        className={`border-b px-6 py-4 ${theme === "dark" ? "bg-[#1a1a1a] border-gray-700" : "bg-white border-gray-200"
          }`}
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-xl font-semibold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
              RAG Chatbot
            </h1>
            <p className={`text-sm ${theme === "dark" ? "text-gray-400" : "text-gray-500"}`}>
              Upload documents and ask questions about their content
            </p>
          </div>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className={`${theme === "dark"
                ? "text-gray-300 hover:text-white hover:bg-gray-700"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
          >
            {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </Button>
        </div>
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 px-4 py-6" ref={scrollAreaRef}>
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`flex max-w-[80%] gap-3 ${message.type === "user" ? "flex-row-reverse" : "flex-row"}`}>
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.type === "user"
                      ? "bg-blue-500"
                      : message.type === "bot"
                        ? (theme === "dark" ? "bg-gray-600" : "bg-gray-700")
                        : "bg-green-500"
                    }`}
                >
                  {message.type === "user" ? (
                    <User className="w-4 h-4 text-white" />
                  ) : message.type === "bot" ? (
                    <Bot className="w-4 h-4 text-white" />
                  ) : (
                    <FileText className="w-4 h-4 text-white" />
                  )}
                </div>

                {/* Message Content */}
                <div
                  className={`rounded-lg px-4 py-2 ${message.type === "user"
                      ? "bg-blue-500 text-white"
                      : message.type === "bot"
                        ? (
                          theme === "dark"
                            ? "bg-[#2a2a2a] border border-gray-600 text-gray-100"
                            : "bg-white border border-gray-200 text-gray-900 shadow-sm"
                        )
                        : (
                          theme === "dark"
                            ? "bg-green-900/30 border border-green-700 text-green-200"
                            : "bg-green-50 border border-green-200 text-green-800"
                        )
                    }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p
                    className={`text-xs mt-1 ${message.type === "user"
                        ? "text-blue-100"
                        : message.type === "bot"
                          ? (theme === "dark" ? "text-gray-400" : "text-gray-500")
                          : (theme === "dark" ? "text-green-300" : "text-green-600")
                      }`}
                  >
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex gap-3">
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${theme === "dark" ? "bg-gray-600" : "bg-gray-700"
                    }`}
                >
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div
                  className={`rounded-lg px-4 py-2 ${theme === "dark"
                      ? "bg-[#2a2a2a] border border-gray-600"
                      : "bg-white border border-gray-200 shadow-sm"
                    }`}
                >
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className={`text-sm ${theme === "dark" ? "text-gray-300" : "text-gray-600"}`}>
                      Thinking...
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div
        className={`border-t px-4 py-4 ${theme === "dark" ? "bg-[#1a1a1a] border-gray-700" : "bg-white border-gray-200"
          }`}
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-2">
            {/* File Upload Button */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className={`flex-shrink-0 ${theme === "dark"
                  ? "border-gray-600 bg-[#2a2a2a] text-gray-300 hover:bg-gray-700 hover:text-white"
                  : "border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
                }`}
            >
              {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
            </Button>

            {/* Message Input */}
            <div className="flex-1">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your documents..."
                disabled={isLoading}
                className={`resize-none ${theme === "dark"
                    ? "border-gray-600 bg-[#2a2a2a] text-gray-100 placeholder:text-gray-400 focus:border-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder:text-gray-500"
                  }`}
              />
            </div>

            {/* Send Button */}
            <Button
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="flex-shrink-0 bg-blue-500 hover:bg-blue-600 text-white"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>

          {/* Hidden file input */}
          <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelect} className="hidden" />
        </div>
      </div>
      </div>
    </div>
  )
}
