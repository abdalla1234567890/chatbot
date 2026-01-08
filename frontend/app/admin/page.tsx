"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface User {
    code: string;
    name: string;
    phone: string;
    is_admin: number;
    id_hash: string;
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
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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
        const token = localStorage.getItem("token");
        const userData = localStorage.getItem("user");

        if (!token || !userData) {
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
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/users`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            } else if (res.status === 401) {
                handleLogout();
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const loadLocations = async () => {
        try {
            const res = await fetch(`${API_URL}/locations`);
            const data = await res.json();
            setLocations(data);
        } catch (err) {
            console.error(err);
        }
    };

    const handleAddUser = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/users`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(newUser),
            });

            if (res.ok) {
                alert("✅ تم إضافة المستخدم بنجاح");
                setNewUser({ code: "", name: "", phone: "" });
                setShowAddForm(false);
                loadUsers();
            } else {
                const data = await res.json();
                alert(data.detail);
            }
        } catch (err) {
            alert("❌ خطأ في الاتصال");
        }
    };

    const handleDeleteUser = async (code: string) => {
        if (!confirm(`هل أنت متأكد من حذف المستخدم ${code}؟`)) return;

        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/users/${code}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                alert("✅ تم الحذف");
                loadUsers();
            } else {
                const data = await res.json();
                alert(data.detail);
            }
        } catch (err) {
            alert("❌ خطأ في الاتصال");
        }
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/users`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(updateUser),
            });

            if (res.ok) {
                alert("✅ تم التعديل بنجاح");
                setUpdateUser({ code: "", field: "", value: "" });
                setShowUpdateForm(false);
                loadUsers();
            } else {
                const data = await res.json();
                alert(data.detail);
            }
        } catch (err) {
            alert("❌ خطأ في الاتصال");
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
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/locations`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ name: newLocation }),
            });

            if (res.ok) {
                alert("✅ تم إضافة الموقع بنجاح");
                setNewLocation("");
                setShowAddLocationForm(false);
                loadLocations();
            } else {
                const data = await res.json();
                alert(data.detail);
            }
        } catch (err) {
            alert("❌ خطأ في الاتصال");
        }
    };

    const handleDeleteLocation = async (locationId: number) => {
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/locations/${locationId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                alert("✅ تم الحذف");
                loadLocations();
            } else {
                const data = await res.json();
                alert(data.detail || "❌ خطأ في الحذف");
            }
        } catch (err) {
            console.error("Delete error:", err);
            alert("❌ خطأ في الاتصال");
        }
    };

    const handleLogout = () => {
        localStorage.clear();
        router.push("/");
    };

    const handleOpenUserLocationsModal = async (userCode: string) => {
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/user-locations?user_code=${encodeURIComponent(userCode)}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to fetch locations");
            const data = await res.json();

            // Safety check
            const locations = Array.isArray(data) ? data : [];

            setSelectedUserLocations({ userCode, userLocations: locations });
            setShowUserLocationsModal(true);
        } catch (err) {
            console.error(err);
            alert("❌ خطأ في جلب مواقع المستخدم");
        }
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
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_URL}/admin/user-locations?user_code=${encodeURIComponent(selectedUserLocations.userCode)}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ location_ids: selectedLocationIds }),
            });

            if (res.ok) {
                alert("✅ تم تحديث مواقع المستخدم بنجاح");
                setShowUserLocationsModal(false);
                setSelectedUserLocations(null);
            } else {
                const data = await res.json();
                alert(data.detail);
            }
        } catch (err) {
            alert("❌ خطأ في الاتصال");
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
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900">
            <div className="bg-white/10 backdrop-blur-lg border-b border-white/20 p-4 shadow-lg">
                <div className="max-w-6xl mx-auto flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <img src="/alamuria-logo.png" alt="شركة العامورية" className="h-12 w-auto" />
                        <div>
                            <h1 className="text-xl font-bold text-white">👑 لوحة التحكم</h1>
                            <p className="text-sm text-gray-300">إدارة المستخدمين والمواقع - شركة العامورية</p>
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

            <div className="max-w-6xl mx-auto p-6 space-y-8">
                <div>
                    <h2 className="text-2xl font-bold text-white mb-4">👥 إدارة المستخدمين</h2>

                    <div className="mb-6">
                        <button
                            onClick={() => setShowAddForm(!showAddForm)}
                            className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-lg shadow-lg transition"
                        >
                            {showAddForm ? "إلغاء" : "➕ إضافة مستخدم جديد"}
                        </button>
                    </div>

                    {showAddForm && (
                        <div className="mb-6 p-6 bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20">
                            <h3 className="text-xl font-bold text-white mb-4">إضافة مستخدم جديد</h3>
                            <form onSubmit={handleAddUser} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">الكود (8 أحرف/أرقام)</label>
                                    <input
                                        type="text"
                                        value={newUser.code}
                                        onChange={(e) => setNewUser({ ...newUser, code: e.target.value })}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                                        required
                                        maxLength={8}
                                        minLength={8}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">الاسم</label>
                                    <input
                                        type="text"
                                        value={newUser.name}
                                        onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                                        required
                                        maxLength={100}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">رقم الهاتف (10 أرقام، يبدأ بـ 05)</label>
                                    <input
                                        type="text"
                                        value={newUser.phone}
                                        onChange={(e) => setNewUser({ ...newUser, phone: e.target.value })}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                                        required
                                        pattern="05[0-9]{8}"
                                        maxLength={10}
                                    />
                                </div>
                                <button
                                    type="submit"
                                    className="w-full py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transition"
                                >
                                    إضافة
                                </button>
                            </form>
                        </div>
                    )}

                    {showUpdateForm && (
                        <div className="mb-6 p-6 bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20">
                            <h3 className="text-xl font-bold text-white mb-4">تعديل بيانات المستخدم</h3>
                            <form onSubmit={handleUpdateUser} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">كود المستخدم</label>
                                    <input
                                        type="text"
                                        value={updateUser.code}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-gray-400 cursor-not-allowed"
                                        disabled
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">الحقل المراد تعديله</label>
                                    <select
                                        value={updateUser.field}
                                        onChange={(e) => setUpdateUser({ ...updateUser, field: e.target.value, value: "" })}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                                        required
                                    >
                                        <option value="name" className="text-black">الاسم</option>
                                        <option value="phone" className="text-black">رقم الهاتف</option>
                                        <option value="code" className="text-black">الكود</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">
                                        القيمة الجديدة
                                        {updateUser.field === "phone" && " (10 أرقام، يبدأ بـ 05)"}
                                        {updateUser.field === "code" && " (8 أحرف/أرقام)"}
                                    </label>
                                    <input
                                        type="text"
                                        value={updateUser.value}
                                        onChange={(e) => setUpdateUser({ ...updateUser, value: e.target.value })}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                                        required
                                        maxLength={updateUser.field === "name" ? 100 : updateUser.field === "phone" ? 10 : 8}
                                        minLength={updateUser.field === "code" ? 8 : updateUser.field === "phone" ? 10 : undefined}
                                        pattern={updateUser.field === "phone" ? "05[0-9]{8}" : undefined}
                                    />
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        type="submit"
                                        className="flex-1 py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transition"
                                    >
                                        تحديث
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setShowUpdateForm(false)}
                                        className="px-6 py-3 bg-gray-500/20 hover:bg-gray-500/30 text-gray-200 rounded-lg transition"
                                    >
                                        إلغاء
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-white/5">
                                    <tr>
                                        <th className="px-6 py-4 text-right text-sm font-semibold text-gray-200">الكود</th>
                                        <th className="px-6 py-4 text-right text-sm font-semibold text-gray-200">الاسم</th>
                                        <th className="px-6 py-4 text-right text-sm font-semibold text-gray-200">الهاتف</th>
                                        <th className="px-6 py-4 text-right text-sm font-semibold text-gray-200">الصلاحية</th>
                                        <th className="px-6 py-4 text-right text-sm font-semibold text-gray-200">الإجراءات</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/10">
                                    {users.map((user) => (
                                        <tr key={user.code} className="hover:bg-white/5 transition">
                                            <td className="px-6 py-4 text-white font-mono">{user.code}</td>
                                            <td className="px-6 py-4 text-white">{user.name}</td>
                                            <td className="px-6 py-4 text-white">{user.phone}</td>
                                            <td className="px-6 py-4">
                                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${user.is_admin ? "bg-yellow-500/20 text-yellow-200" : "bg-blue-500/20 text-blue-200"}`}>
                                                    {user.is_admin ? "👑 أدمن" : "👤 مستخدم"}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex gap-2 flex-wrap">
                                                    <button
                                                        onClick={() => startUpdateUser({ ...user, code: user.id_hash || user.code })}
                                                        className="px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 rounded-lg transition text-sm"
                                                    >
                                                        تعديل
                                                    </button>
                                                    <button
                                                        onClick={() => handleOpenUserLocationsModal(user.id_hash)}
                                                        className="px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 rounded-lg transition text-sm"
                                                    >
                                                        📍 مواقع
                                                    </button>
                                                    {user.name !== "Main Admin" && (
                                                        <button
                                                            onClick={() => handleDeleteUser(user.id_hash)}
                                                            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-lg transition text-sm"
                                                        >
                                                            حذف
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

                    <div className="mt-4 text-center text-gray-400 text-sm">
                        إجمالي المستخدمين: {users.length}
                    </div>
                </div>

                <div>
                    <h2 className="text-2xl font-bold text-white mb-4">📍 إدارة المواقع</h2>

                    <div className="mb-6">
                        <button
                            onClick={() => setShowAddLocationForm(!showAddLocationForm)}
                            className="px-6 py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transition"
                        >
                            {showAddLocationForm ? "إلغاء" : "➕ إضافة موقع جديد"}
                        </button>
                    </div>

                    {showAddLocationForm && (
                        <div className="mb-6 p-6 bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20">
                            <h3 className="text-xl font-bold text-white mb-4">إضافة موقع جديد</h3>
                            <form onSubmit={handleAddLocation} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-200 mb-2">اسم الموقع</label>
                                    <input
                                        type="text"
                                        value={newLocation}
                                        onChange={(e) => setNewLocation(e.target.value)}
                                        className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                                        required
                                        maxLength={100}
                                        placeholder="مثال: الرياض"
                                    />
                                </div>
                                <button
                                    type="submit"
                                    className="w-full py-3 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white font-semibold rounded-lg shadow-lg transition"
                                >
                                    إضافة
                                </button>
                            </form>
                        </div>
                    )}

                    <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">المواقع الحالية ({locations.length})</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {locations.map((location) => (
                                <div
                                    key={location.id}
                                    className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition"
                                >
                                    <span className="text-white">{location.name}</span>
                                    <button
                                        onClick={() => handleDeleteLocation(location.id)}
                                        className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded text-sm transition"
                                    >
                                        حذف
                                    </button>
                                </div>
                            ))}
                        </div>
                        {locations.length === 0 && (
                            <p className="text-center text-gray-400 py-4">لا توجد مواقع مضافة</p>
                        )}
                    </div>
                </div>
            </div>

            {showUserLocationsModal && selectedUserLocations && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
                    <div className="bg-gradient-to-br from-slate-900 via-teal-900 to-slate-900 rounded-2xl border border-white/20 max-w-2xl w-full max-h-96 overflow-y-auto shadow-2xl">
                        <div className="sticky top-0 bg-white/10 backdrop-blur-lg border-b border-white/20 p-4 flex justify-between items-center">
                            <h3 className="text-xl font-bold text-white">تعديل مواقع المستخدم</h3>
                            <button
                                onClick={() => setShowUserLocationsModal(false)}
                                className="text-gray-400 hover:text-white text-2xl"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleUpdateUserLocations} className="p-6 space-y-4">
                            <div className="mb-4">
                                <p className="text-gray-300 mb-4">اختر المواقع المتاحة للمستخدم <span className="font-bold text-white">{selectedUserLocations.userCode}</span></p>
                                <div className="space-y-3 max-h-64 overflow-y-auto">
                                    {locations.map((location) => {
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
                                    })}
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
