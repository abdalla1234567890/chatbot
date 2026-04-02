"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface User {
  code: string;
  name: string;
  phone: string;
  is_admin: number;
  locations?: Location[];
}

interface Location {
  id: number;
  name: string;
}

interface UserLocationData {
  userCode: string;
  userLocations: Location[];
}

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUser, setNewUser] = useState({ code: "", name: "", phone: "" });
  const [showUpdateForm, setShowUpdateForm] = useState(false);
  const [updateUser, setUpdateUser] = useState({ code: "", field: "", value: "" });
  const [showAddLocationForm, setShowAddLocationForm] = useState(false);
  const [newLocation, setNewLocation] = useState("");
  const [showUserLocationsModal, setShowUserLocationsModal] = useState(false);
  const [selectedUserLocations, setSelectedUserLocations] = useState<UserLocationData | null>(null);
  const router = useRouter();

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (!userData) {
      router.push("/");
      return;
    }

    const user = JSON.parse(userData);
    if (user.is_admin !== 1) {
      router.push("/chat");
      return;
    }

    loadUsers();
    loadLocations();
  }, [router]);

  const loadUsers = async () => {
    try {
      const data = await api.get("/admin/users");
      setUsers(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadLocations = async () => {
    try {
      const data = await api.get("/locations");
      setLocations(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/admin/users", newUser);
      alert("✅ تم إضافة المستخدم بنجاح");
      setNewUser({ code: "", name: "", phone: "" });
      setShowAddForm(false);
      loadUsers();
    } catch (err: any) {
      alert(err.message || "❌ خطأ في الإضافة");
    }
  };

  const handleDeleteUser = async (code: string) => {
    if (!confirm(`هل أنت متأكد من حذف المستخدم ${code}؟`)) return;
    try {
      await api.delete(`/admin/users/${code}`);
      alert("✅ تم الحذف");
      loadUsers();
    } catch (err: any) {
      alert(err.message || "❌ خطأ في الحذف");
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Updated to match PUT /admin/users/{user_code}
      await api.put(`/admin/users/${updateUser.code}`, {
        [updateUser.field]: updateUser.value
      });
      alert("✅ تم التعديل بنجاح");
      setUpdateUser({ code: "", field: "", value: "" });
      setShowUpdateForm(false);
      loadUsers();
    } catch (err: any) {
      alert(err.message || "❌ خطأ في التعديل");
    }
  };

  const startUpdateUser = (user: User) => {
    setUpdateUser({ code: user.code, field: "name", value: user.name });
    setShowUpdateForm(true);
    setShowAddForm(false);
  };

  const handleAddLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/locations", { name: newLocation });
      alert("✅ تم إضافة الموقع بنجاح");
      setNewLocation("");
      setShowAddLocationForm(false);
      loadLocations();
    } catch (err: any) {
      alert(err.message || "❌ خطأ في الإضافة");
    }
  };

  const handleDeleteLocation = async (locationId: number) => {
    try {
      await api.delete(`/locations/${locationId}`);
      alert("✅ تم الحذف");
      loadLocations();
    } catch (err: any) {
      alert(err.message || "❌ خطأ في الحذف");
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push("/");
  };

  const maskUserCode = (code: string) => {
    if (!code) return "";
    if (code.length <= 2) return "*".repeat(code.length);
    return `${"*".repeat(code.length - 2)}${code.slice(-2)}`;
  };

  const handleOpenUserLocationsModal = async (userCode: string) => {
    // Current user's locations can be fetched or derived. 
    // For simplicity, we find the user in our local state.
    const targetUser = users.find(u => u.code === userCode);
    if (!targetUser) return;
    
    // Note: In the refactored backend, we might need an endpoint to get another user's locations,
    // but for now, if the 'read_users' includes locations (relationship load), we are good.
    // Assuming users don't have locations pre-loaded for now from admin/users broad call.
    setSelectedUserLocations({ userCode, userLocations: targetUser.locations || [] }); // Start with user's locations empty if none
    setShowUserLocationsModal(true);
  };

  const handleUpdateUserLocations = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserLocations) return;

    const selectedLocationIds = locations
      .filter(loc => {
        const checkbox = document.getElementById(`location-${loc.id}`) as HTMLInputElement;
        return checkbox?.checked;
      })
      .map(loc => loc.id);

    try {
      await api.post(`/locations/user/${selectedUserLocations.userCode}`, {
        location_ids: selectedLocationIds
      });
      alert("✅ تم تحديث مواقع المستخدم بنجاح");
      setShowUserLocationsModal(false);
      setSelectedUserLocations(null);
      loadUsers(); // Reload to get updated user locations
    } catch (err: any) {
      alert(err.message || "❌ خطأ في الحفظ");
    }
  };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900 flex items-center justify-center">
                <div className="text-white text-xl">جاري التحميل...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900 font-sans" dir="rtl">
            <div className="bg-white/10 backdrop-blur-lg border-b border-white/20 p-4 shadow-lg sticky top-0 z-10 transition-all">
                <div className="max-w-6xl mx-auto flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <img src="/alamuria-logo.png" alt="Logo" className="h-10 w-auto object-contain drop-shadow-md" />
                        <div>
                            <h1 className="text-xl font-bold text-white flex items-center gap-2">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                                لوحة التحكم الإدارية
                            </h1>
                            <p className="text-sm text-gray-300">إدارة النظام - شركة العامورية</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="px-6 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-100 rounded-xl transition-all border border-red-500/20 font-bold"
                    >
                        تسجيل الخروج
                    </button>
                </div>
            </div>

            <div className="max-w-6xl mx-auto p-6 space-y-10">
                <div className="animate-in fade-in slide-in-from-right duration-500">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-3 bg-teal-500/20 rounded-2xl">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        </div>
                        <h2 className="text-3xl font-black text-white">إدارة المستخدمين</h2>
                    </div>

                    <div className="mb-8">
                        <button
                            onClick={() => setShowAddForm(!showAddForm)}
                            className="group relative px-8 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-2xl shadow-[0_4px_15px_rgba(16,185,129,0.3)] transition-all flex items-center gap-2 overflow-hidden"
                        >
                            <span className="relative z-10">{showAddForm ? "إلغاء العملية" : "إضافة مستخدم جديد"}</span>
                            {!showAddForm && (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 relative z-10 group-hover:rotate-90 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 4v16m8-8H4" />
                                </svg>
                            )}
                        </button>
                    </div>

                    {showAddForm && (
                        <div className="mb-8 p-8 bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl animate-in zoom-in-95 duration-300">
                            <h3 className="text-xl font-bold text-white mb-6">📝 بيانات الحساب الجديد</h3>
                            <form onSubmit={handleAddUser} className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div>
                                    <label className="block text-sm font-bold text-gray-200 mb-2">كود الدخول (8 خانات)</label>
                                    <input
                                        type="text"
                                        value={newUser.code}
                                        onChange={(e) => setNewUser({ ...newUser, code: e.target.value })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-teal-500 transition-all font-mono"
                                        required
                                        maxLength={8}
                                        minLength={8}
                                    />
                                </div>
                                <div className="md:col-span-1">
                                    <label className="block text-sm font-bold text-gray-200 mb-2">اسم المندوب</label>
                                    <input
                                        type="text"
                                        value={newUser.name}
                                        onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-teal-500 transition-all"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-200 mb-2">رقم الجوال</label>
                                    <input
                                        type="text"
                                        value={newUser.phone}
                                        onChange={(e) => setNewUser({ ...newUser, phone: e.target.value })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-teal-500 transition-all font-mono"
                                        required
                                        placeholder="05XXXXXXXX"
                                        pattern="05[0-9]{8}"
                                        maxLength={10}
                                        minLength={10}
                                        inputMode="numeric"
                                    />
                                </div>
                                <div className="md:col-span-3">
                                    <button
                                        type="submit"
                                        className="w-full py-4 bg-teal-600 hover:bg-teal-500 text-white font-bold rounded-xl shadow-lg transition-all transform active:scale-95"
                                    >
                                        إتمام الإضافة
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {showUpdateForm && (
                        <div className="mb-8 p-8 bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl animate-in zoom-in-95 duration-300">
                            <h3 className="text-xl font-bold text-white mb-6">✏️ تعديل بيانات المستخدم</h3>
                            <form onSubmit={handleUpdateUser} className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div>
                                    <label className="block text-sm font-bold text-gray-200 mb-2">رقم المستخدم (مخفي)</label>
                                    <input
                                        type="text"
                                        value={maskUserCode(updateUser.code)}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-gray-300 font-mono"
                                        disabled
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-200 mb-2">الحقل المراد تعديله</label>
                                    <select
                                        value={updateUser.field}
                                        onChange={(e) => setUpdateUser({ ...updateUser, field: e.target.value, value: "" })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-teal-500 transition-all"
                                        required
                                    >
                                        <option value="name">الاسم</option>
                                        <option value="phone">رقم الجوال</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-200 mb-2">القيمة الجديدة</label>
                                    <input
                                        type="text"
                                        value={updateUser.value}
                                        onChange={(e) => setUpdateUser({ ...updateUser, value: e.target.value })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-teal-500 transition-all font-mono"
                                        required
                                        placeholder={updateUser.field === "phone" ? "05XXXXXXXX" : "اكتب الاسم الجديد"}
                                        pattern={updateUser.field === "phone" ? "05[0-9]{8}" : undefined}
                                        maxLength={updateUser.field === "phone" ? 10 : undefined}
                                        minLength={updateUser.field === "phone" ? 10 : undefined}
                                        inputMode={updateUser.field === "phone" ? "numeric" : "text"}
                                    />
                                </div>
                                <div className="md:col-span-3 flex gap-3">
                                    <button
                                        type="submit"
                                        className="flex-1 py-4 bg-teal-600 hover:bg-teal-500 text-white font-bold rounded-xl shadow-lg transition-all transform active:scale-95"
                                    >
                                        حفظ التعديل
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowUpdateForm(false);
                                            setUpdateUser({ code: "", field: "", value: "" });
                                        }}
                                        className="px-6 py-4 bg-gray-500/20 hover:bg-gray-500/30 text-gray-200 rounded-xl transition-all"
                                    >
                                        إلغاء
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="bg-white/5 backdrop-blur-lg rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-right">
                                <thead>
                                    <tr className="bg-white/10">
                                        <th className="px-6 py-5 text-gray-200 font-black">المندوب</th>
                                        <th className="px-6 py-5 text-gray-200 font-black">الكود (مخفي)</th>
                                        <th className="px-6 py-5 text-gray-200 font-black">الجوال</th>
                                        <th className="px-6 py-5 text-gray-200 font-black">المستوى</th>
                                        <th className="px-6 py-5 text-gray-200 font-black">الإجراءات</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {users.map((user) => (
                                        <tr key={user.code} className="hover:bg-white/5 transition-all group">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-full bg-teal-600/20 flex items-center justify-center text-teal-400 font-bold border border-teal-500/20">
                                                        {user.name[0]}
                                                    </div>
                                                    <span className="text-white font-bold">{user.name}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-teal-300 font-mono">{maskUserCode(user.code)}</td>
                                            <td className="px-6 py-4 text-gray-300 font-mono">{user.phone}</td>
                                            <td className="px-6 py-4">
                                                <span className={`px-4 py-1 rounded-full text-xs font-black tracking-wide ${user.is_admin ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30" : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"}`}>
                                                    {user.is_admin ? "مدير نظام" : "مندوب"}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => startUpdateUser(user)}
                                                        className="p-2 bg-blue-500/20 hover:bg-blue-500/40 text-blue-300 rounded-lg transition-all"
                                                        title="تعديل"
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => handleOpenUserLocationsModal(user.code)}
                                                        className="p-2 bg-purple-500/20 hover:bg-purple-500/40 text-purple-300 rounded-lg transition-all"
                                                        title="المواقع"
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                                                        </svg>
                                                    </button>
                                                    {user.name !== "Main Admin" && (
                                                        <button
                                                            onClick={() => handleDeleteUser(user.code)}
                                                            className="p-2 bg-red-500/20 hover:bg-red-500/40 text-red-300 rounded-lg transition-all"
                                                            title="حذف"
                                                        >
                                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                                        </svg>
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div className="animate-in fade-in slide-in-from-right duration-700 delay-100">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-3 bg-emerald-500/20 rounded-2xl">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </div>
                        <h2 className="text-3xl font-black text-white">إدارة المناطق والمواقع</h2>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div>
                            <button
                                onClick={() => setShowAddLocationForm(!showAddLocationForm)}
                                className="w-full py-5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-3xl text-white font-bold transition-all flex items-center justify-center gap-3"
                            >
                                <span className={showAddLocationForm ? "text-red-400" : "text-emerald-400"}>
                                    {showAddLocationForm ? "إلغاء الإضافة" : "➕ تسجيل منطقة جديدة"}
                                </span>
                            </button>

                            {showAddLocationForm && (
                                <div className="mt-6 p-8 bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl animate-in fade-in duration-300">
                                    <form onSubmit={handleAddLocation} className="space-y-4">
                                        <label className="block text-sm font-bold text-gray-200">اسم المنطقة (مثل: حي العليا، الرياض)</label>
                                        <input
                                            type="text"
                                            value={newLocation}
                                            onChange={(e) => setNewLocation(e.target.value)}
                                            className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-emerald-500"
                                            required
                                        />
                                        <button type="submit" className="w-full py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-black rounded-xl">تأكيد الحفظ</button>
                                    </form>
                                </div>
                            )}
                        </div>

                        <div className="bg-white/5 backdrop-blur-lg rounded-3xl border border-white/10 p-8">
                            <h3 className="text-xl font-bold text-white mb-6">المناطق النشطة حالياً</h3>
                            <div className="grid grid-cols-1 gap-3">
                                {locations.map((location) => (
                                    <div key={location.id} className="flex items-center justify-between p-4 bg-white/5 rounded-2xl border border-white/5 hover:bg-white/10 transition-all">
                                        <span className="text-white font-medium flex items-center gap-2">
                                            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                                            {location.name}
                                        </span>
                                        <button onClick={() => handleDeleteLocation(location.id)} className="text-red-400 hover:text-red-300 transition-colors p-2 underline text-sm">حذف</button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {showUserLocationsModal && selectedUserLocations && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
                    <div className="bg-slate-900 rounded-[32px] border border-white/20 max-w-xl w-full max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
                        <div className="p-6 border-b border-white/10 flex justify-between items-center bg-white/5">
                            <h3 className="text-2xl font-black text-white">تخصيص النطاق الجغرافي</h3>
                            <button onClick={() => setShowUserLocationsModal(false)} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <form onSubmit={handleUpdateUserLocations} className="p-6 space-y-4">
                            <div className="mb-4">
                                <p className="text-gray-300 mb-4">اختر المواقع المتاحة للمستخدم <span className="font-bold text-white">{selectedUserLocations.userCode}</span></p>
                                <div className="space-y-3 max-h-64 overflow-y-auto">
                                    {(() => {
                                        const takenLocationIds = new Set(
                                            users
                                                .filter(u => u.code !== selectedUserLocations.userCode)
                                                .flatMap(u => u.locations?.map(l => l.id) || [])
                                        );
                                        const availableLocations = locations.filter(loc => !takenLocationIds.has(loc.id));
                                        
                                        if (availableLocations.length === 0) {
                                            return <p className="text-center text-gray-400 p-4">لا توجد مواقع متاحة لتخصيصها لهذا المستخدم</p>;
                                        }

                                        return availableLocations.map((location) => {
                                            const isSelected = selectedUserLocations.userLocations?.some(loc => loc.id === location.id);
                                            return (
                                                <label key={location.id} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 transition cursor-pointer">
                                                    <input
                                                        id={`location-${location.id}`}
                                                        type="checkbox"
                                                        defaultChecked={isSelected}
                                                        className="w-4 h-4 rounded border-gray-400 text-teal-600 cursor-pointer"
                                                    />
                                                    <span className="text-white flex-1">{location.name}</span>
                                                    {isSelected && <span className="text-teal-400 text-sm">✓ محدد</span>}
                                                </label>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>

                            <div className="flex gap-2 sticky bottom-0 bg-white/10 backdrop-blur-lg p-4 border-t border-white/20">
                                <button
                                    type="submit"
                                    className="flex-1 py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transition"
                                >
                                    حفظ التغييرات
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowUserLocationsModal(false)}
                                    className="px-6 py-3 bg-gray-500/20 hover:bg-gray-500/30 text-gray-200 rounded-lg transition"
                                >
                                    إلغاء
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
