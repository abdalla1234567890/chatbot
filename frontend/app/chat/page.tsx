"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface Location {
  id: number;
  name: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showLocations, setShowLocations] = useState(false);
  const [locations, setLocations] = useState<Location[]>([]);
  const [user, setUser] = useState<any>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const router = useRouter();

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (!userData) {
      router.push("/");
      return;
    }

    const parsedUser = JSON.parse(userData);
    setUser(parsedUser);
    setMessages([{
      role: "assistant",
      content: `أهلاً بك ${parsedUser.name} في شات بوت شركة العامورية`
    }]);

    loadLocations();
  }, [router]);

  const loadLocations = async () => {
    try {
      const data = await api.get("/locations/my-locations");
      setLocations(data);
    } catch (err) {
      console.error("Error loading locations:", err);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "inherit";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 140)}px`;
    }
  }, [input]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMessage: ChatMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setShowLocations(false);

    try {
      const history = messages.map(m =>
        m.role === "user" ? `العميل: ${m.content}` : `البائع: ${m.content}`
      );

      const data = await api.post("/chat/", {
        message: text,
        history
      });

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: data.reply
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (data.reply.includes("ASK_LOCATION")) {
        setShowLocations(true);
      }
    } catch (err: any) {
      console.error("❌ خطأ:", err);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `❌ خطأ في الاتصال بالخادم: ${err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

    const handleLogout = () => {
        setMessages([]);
        localStorage.clear();
        router.push("/");
    };

    if (!user) return null;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900 flex flex-col" dir="rtl">
            <div className="bg-white/10 backdrop-blur-lg border-b border-white/20 p-4 shadow-lg sticky top-0 z-10 font-sans">
                <div className="max-w-4xl mx-auto flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <img src="/alamuria-logo.png" alt="شركة العامورية" className="h-12 w-auto" />
                        <div>
                            <h1 className="text-xl font-bold text-white">شات بوت شركة العامورية</h1>
                            <p className="text-sm text-gray-300">مرحباً {user.name}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-100 rounded-lg transition-all border border-red-500/30"
                    >
                        تسجيل الخروج
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                <div className="max-w-4xl mx-auto space-y-6">
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex items-end gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                        >
                      {/* Avatar */}
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg overflow-hidden border-2 border-white/10 ${
                          msg.role === "user" 
                          ? "bg-teal-500" 
                          : "bg-teal-900/40"
                      }`}>
                          {msg.role === "user" ? (
                              <img src="/user-avatar-v2.png" alt="User" className="w-full h-full object-cover" />
                          ) : (
                              <img src="/bot-avatar.png" alt="Bot Logo" className="w-full h-full object-cover" />
                          )}
                      </div>

                      <div
                          className={`max-w-[80%] p-4 rounded-2xl shadow-xl transform transition-all hover:scale-[1.01] ${
                              msg.role === "user"
                              ? "bg-gradient-to-r from-teal-600 to-teal-500 text-white rounded-bl-none"
                              : "bg-white/10 backdrop-blur-lg text-gray-100 border border-white/20 rounded-br-none"
                          }`}
                      >
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content.replace(/#*ASK_LOCATION#*/g, "")}</p>
                      </div>
                  </div>
              ))}
              {loading && (
                  <div className="flex items-end gap-3 flex-row animate-in fade-in slide-in-from-bottom-2 duration-300">
                       <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-white/20 border border-white/20 overflow-hidden">
                          <img src="/bot-avatar.png" alt="Bot Logo" className="w-full h-full object-cover opacity-70 animate-pulse" />
                      </div>
                      <div className="bg-white/10 backdrop-blur-lg p-4 rounded-2xl border border-white/20 rounded-br-none">
                          <div className="flex gap-2">
                              <div className="w-2.5 h-2.5 bg-teal-400 rounded-full animate-bounce"></div>
                              <div className="w-2.5 h-2.5 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }}></div>
                              <div className="w-2.5 h-2.5 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }}></div>
                          </div>
                      </div>
                  </div>
              )}
              <div ref={messagesEndRef} />
          </div>
      </div>

      {showLocations && (
          <div className="bg-white/5 backdrop-blur-xl border-t border-white/10 p-6 animate-in slide-in-from-bottom duration-500">
              <div className="max-w-4xl mx-auto">
                  <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 bg-teal-500/20 rounded-lg">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                      </div>
                      <p className="text-white text-lg font-bold">📍 اختر الموقع:</p>
                  </div>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                      {locations.map((loc) => (
                          <button
                              key={loc.id}
                              onClick={() => sendMessage(loc.name)}
                              className="group relative overflow-hidden px-4 py-3 bg-white/5 hover:bg-teal-600 border border-white/10 hover:border-teal-400 rounded-xl transition-all duration-300"
                          >
                              <span className="relative z-10 text-white font-medium group-hover:scale-110 transition-transform inline-block">
                                  {loc.name}
                              </span>
                              <div className="absolute inset-0 bg-gradient-to-r from-teal-600 to-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                      ))}
                  </div>
              </div>
          </div>
      )}

      <div className="bg-white/5 backdrop-blur-xl border-t border-white/10 p-4 sticky bottom-0">
          <div className="max-w-4xl mx-auto">
              <form
                  onSubmit={(e) => {
                      e.preventDefault();
                      sendMessage(input);
                  }}
                  className="space-y-3"
              >
                  <div className="flex gap-2">
                      <div className="flex-1 relative group">
                          <textarea
                              ref={textareaRef}
                              value={input}
                              onChange={(e) => setInput(e.target.value)}
                              onKeyDown={(e) => {
                                  if (e.key === "Enter" && !e.shiftKey) {
                                      e.preventDefault();
                                      sendMessage(input);
                                  }
                              }}
                              placeholder={showLocations ? "اختر الموقع من الأزرار أعلاه..." : "اكتب طلبك هنا..."}
                              className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-2xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50 resize-none overflow-y-auto min-h-[56px] max-h-[140px] shadow-inner transition-all group-hover:bg-white/[0.15]"
                              disabled={loading || showLocations}
                              rows={1}
                              autoFocus
                          />
                      </div>
                      <button
                          type="submit"
                          disabled={loading || showLocations || !input.trim()}
                          className="px-6 bg-gradient-to-tr from-teal-600 to-emerald-500 hover:from-teal-500 hover:to-emerald-400 text-white rounded-2xl shadow-[0_4px_15px_rgba(20,184,166,0.3)] hover:shadow-[0_8px_25px_rgba(20,184,166,0.5)] transition-all duration-300 disabled:opacity-50 disabled:scale-100 flex items-center gap-2 transform active:scale-95"
                      >
                          <span className="font-bold hidden sm:inline">إرسال</span>
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 rotate-[-45deg] group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform">
                              <path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" />
                          </svg>
                      </button>
                  </div>
              </form>
          </div>
      </div>
        </div>
    );
}
