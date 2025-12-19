"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface Message {
    role: "user" | "assistant";
    content: string;
}

interface Location {
    id: number;
    name: string;
}



export default function ChatPage() {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [showLocations, setShowLocations] = useState(false);
    const [locations, setLocations] = useState<Location[]>([]);
    const [user, setUser] = useState<any>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    useEffect(() => {
        const code = localStorage.getItem("code");
        const userData = localStorage.getItem("user");

        if (!code || !userData) {
            router.push("/");
            return;
        }

        setUser(JSON.parse(userData));
        setMessages([{
            role: "assistant",
            content: `✅ هلا بك ${JSON.parse(userData).name}!\nجاهز استقبل طلباتك.`
        }]);

        // جلب المواقع من API
        loadLocations();
    }, [router]);

    const loadLocations = async () => {
        try {
            const code = localStorage.getItem("code");
            const res = await fetch(`${API_URL}/user-locations?code=${code}`);
            const data = await res.json();
            setLocations(data);
        } catch (err) {
            console.error("Error loading locations:", err);
        }
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async (text: string) => {
        if (!text.trim() || loading) return;

        console.log("📤 إرسال رسالة:", text);

        const userMessage: Message = { role: "user", content: text };
        setMessages(prev => [...prev, userMessage]);
        setInput("");
        setLoading(true);
        setShowLocations(false);

        try {
            const code = localStorage.getItem("code");
            console.log("🔑 كود المستخدم:", code);

            if (!code) {
                throw new Error("لا يوجد كود في localStorage");
            }

            const history = messages.map(m =>
                m.role === "user" ? `العميل: ${m.content}` : `البائع: ${m.content}`
            );

            console.log("📡 إرسال إلى:", `${API_URL}/chat`);


            const res = await fetch(`${API_URL}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code,
                    message: text,
                    history
                }),
            });

            console.log("📨 حالة الاستجابة:", res.status);

            if (!res.ok) {
                throw new Error(`خطأ في الخادم: ${res.status}`);
            }

            const data = await res.json();
            console.log("✅ البيانات المستقبلة:", data);

            const assistantMessage: Message = {
                role: "assistant",
                content: data.reply
            };

            setMessages(prev => [...prev, assistantMessage]);

            // Clear uploaded images after sending
            if (data.order_placed) {
                console.log("✅ تم تسجيل الطلب");
            }

            // Check if asking for location
            if (data.reply.includes("###ASK_LOCATION###")) {
                console.log("📍 طلب اختيار موقع");
                setShowLocations(true);
            }
        } catch (err) {
            console.error("❌ خطأ:", err);
            setMessages(prev => [...prev, {
                role: "assistant",
                content: `❌ خطأ في الاتصال بالخادم: ${err}`
            }]);
        } finally {
            setLoading(false);
        }
    };



    const handleLogout = () => {
        // مسح جميع البيانات عند الخروج
        // مسح جميع البيانات عند الخروج
        setMessages([]);
        localStorage.clear();
        router.push("/");
    };

    if (!user) return null;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900 flex flex-col">
            {/* Header */}
            <div className="bg-white/10 backdrop-blur-lg border-b border-white/20 p-4 shadow-lg">
                <div className="max-w-4xl mx-auto flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <img src="/alamuria-logo.png" alt="شركة العامورية" className="h-12 w-auto" />
                        <div>
                            <h1 className="text-xl font-bold text-white">شات بوت مواد البناء</h1>
                            <p className="text-sm text-gray-300">مرحباً {user.name}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-lg transition"
                    >
                        تسجيل الخروج
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-4xl mx-auto space-y-4">
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex ${msg.role === "user" ? "justify-start" : "justify-end"}`}
                        >
                            <div
                                className={`max-w-[80%] p-4 rounded-2xl shadow-lg ${msg.role === "user"
                                    ? "bg-teal-600 text-white"
                                    : "bg-white/10 backdrop-blur-lg text-gray-100 border border-white/20"
                                    }`}
                            >
                                <p className="whitespace-pre-wrap">{msg.content.replace("###ASK_LOCATION###", "")}</p>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex justify-end">
                            <div className="bg-white/10 backdrop-blur-lg p-4 rounded-2xl border border-white/20">
                                <div className="flex gap-2">
                                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Location Selector */}
            {showLocations && (
                <div className="bg-white/10 backdrop-blur-lg border-t border-white/20 p-4">
                    <div className="max-w-4xl mx-auto">
                        <p className="text-white mb-3 font-semibold">📍 اختر الموقع:</p>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            {locations.map((loc) => (
                                <button
                                    key={loc.id}
                                    onClick={() => sendMessage(loc.name)}
                                    className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition transform hover:scale-105"
                                >
                                    {loc.name}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}



            {/* Input */}
            <div className="bg-white/10 backdrop-blur-lg border-t border-white/20 p-4">
                <div className="max-w-4xl mx-auto">
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            sendMessage(input);
                        }}
                        className="space-y-3"
                    >
                        <div className="flex gap-1">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && e.ctrlKey) {
                                        e.preventDefault();
                                        sendMessage(input);
                                    }
                                }}
                                placeholder={showLocations ? "اختر الموقع من الأزرار أعلاه..." : "اكتب طلبك هنا..."}
                                className="flex-1 px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50 resize-none overflow-y-auto"
                                disabled={loading || showLocations}
                                rows={1}
                                autoFocus
                            />
                            <button
                                type="submit"
                                disabled={loading || showLocations || !input.trim()}
                                className="px-4 py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                إرسال
                            </button>
                        </div>

                    </form>
                </div>
            </div >
        </div >
    );
}
