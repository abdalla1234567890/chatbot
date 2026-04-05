"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Home() {
  const [code, setCode] = useState("");
  const [otp, setOtp] = useState("");
  const [otpRequired, setOtpRequired] = useState(false);
  const [otpSecondsLeft, setOtpSecondsLeft] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!otpRequired || otpSecondsLeft <= 0) return;
    const timer = setInterval(() => {
      setOtpSecondsLeft((prev) => Math.max(prev - 1, 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [otpRequired, otpSecondsLeft]);

  const formatOtpCountdown = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.post("/login_json", { code });
      
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      localStorage.removeItem("code");

      if (data.user.is_admin === 1) {
        router.push("/admin");
      } else {
        router.push("/chat");
      }
    } catch (err: any) {
      if ((err.message || "").includes("Admin OTP required")) {
        try {
          await api.post("/admin/login/start", { code });
          setOtpRequired(true);
          setOtpSecondsLeft(300);
          setError("تم إرسال كود التحقق إلى بريد الأدمن.");
        } catch (otpErr: any) {
          setError(`❌ ${otpErr.message || "فشل إرسال كود التحقق"}`);
        }
      } else {
        setError(`❌ ${err.message || "كود خاطئ. حاول مرة أخرى."}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post("/admin/login/verify", { code, otp });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      router.push("/admin");
    } catch (err: any) {
      setError(`❌ ${err.message || "كود التحقق غير صحيح"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setError("");
    setLoading(true);
    try {
      await api.post("/admin/login/start", { code });
      setOtpSecondsLeft(300);
      setError("تم إعادة إرسال كود التحقق.");
    } catch (err: any) {
      setError(`❌ ${err.message || "فشل إعادة إرسال كود التحقق"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900" dir="rtl">
      <div className="w-full max-w-md p-8 bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 font-sans">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <img src="/alamuria-logo.png" alt="شركة العامورية" className="h-20 w-auto drop-shadow-md" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">شات بوت شركة العامورية</h1>
          <p className="text-gray-300 font-medium">نظام تقديم الطلبات</p>
        </div>

        <form onSubmit={otpRequired ? handleVerifyOtp : handleLogin} className="space-y-6">
          <div className="relative">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 bg-teal-500/20 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-teal-400">
                  <path fillRule="evenodd" d="M12 1.5a5.25 5.25 0 0 0-5.25 5.25v3a3 3 0 0 0-3 3v6.75a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3v-6.75a3 3 0 0 0-3-3v-3A5.25 5.25 0 0 0 12 1.5Zm-3.75 5.25a3.75 3.75 0 1 1 7.5 0v3h-7.5v-3Z" clipRule="evenodd" />
                </svg>
              </div>
              <label className="text-sm font-bold text-gray-200">
                {otpRequired ? "كود التحقق (OTP)" : "كود الدخول السري"}
              </label>
            </div>
            <div className="relative">
              <input
                type={showCode ? "text" : "password"}
                value={otpRequired ? otp : code}
                onChange={(e) => otpRequired ? setOtp(e.target.value) : setCode(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition pr-12"
                placeholder={otpRequired ? "أدخل كود التحقق المرسل للإيميل" : "أدخل الكود السري"}
                required
              />
              <button
                type="button"
                onClick={() => setShowCode(!showCode)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-white transition"
              >
                {showCode ? (
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200 text-sm">
              {error}
            </div>
          )}
          {otpRequired && (
            <div className="p-3 bg-teal-500/10 border border-teal-500/40 rounded-lg text-teal-200 text-sm">
              مدة صلاحية الكود: {formatOtpCountdown(otpSecondsLeft)}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transform transition hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "جاري التحقق..." : otpRequired ? "تأكيد OTP" : "دخول"}
          </button>
          {otpRequired && (
            <>
              <button
                type="button"
                onClick={handleResendOtp}
                disabled={loading}
                className="w-full py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 rounded-lg transition disabled:opacity-50"
              >
                إعادة إرسال OTP
              </button>
              <button
                type="button"
                onClick={() => {
                  setOtpRequired(false);
                  setOtp("");
                  setError("");
                  setOtpSecondsLeft(0);
                }}
                className="w-full py-2 bg-white/10 hover:bg-white/20 text-gray-200 rounded-lg transition"
              >
                رجوع
              </button>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
