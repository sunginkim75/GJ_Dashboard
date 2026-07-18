// Global State & Elements
let googleClientId = null;
let sessionToken = localStorage.getItem("gj_session_token");
let searchTimeout = null;

const loadingEl = document.getElementById("loading");
const toastEl = document.getElementById("toast");
const loginPage = document.getElementById("login-page");
const appPage = document.getElementById("app-page");

// Initialize Application
window.addEventListener("DOMContentLoaded", async () => {
    showLoading(true);
    try {
        // 1. Fetch Google Client ID from Backend
        const res = await fetch("/api/auth/config");
        const data = await res.json();
        googleClientId = data.google_client_id;
        
        // 2. Setup Form Select Element Listeners
        initSelectEditable("form-event-select", "form-event");
        initSelectEditable("form-who-select", "form-who");
        
        // 3. Format Amount Input Real-time
        setupAmountInputFormatter("form-amount");

        // 4. Check user authentication session
        if (sessionToken) {
            const authOk = await checkSession();
            if (authOk) {
                initDashboard();
            } else {
                showLoginPage();
            }
        } else {
            showLoginPage();
        }
    } catch (err) {
        showToast("서버 통신 실패. 페이지를 새로고침 하세요.", "error");
        console.error(err);
    } finally {
        showLoading(false);
    }
});

// Select Option & Input field synchronization (Editable Select box)
function initSelectEditable(selectId, inputId) {
    const select = document.getElementById(selectId);
    const input = document.getElementById(inputId);
    
    if (select && input) {
        select.addEventListener("change", (e) => {
            if (e.target.value) {
                input.value = e.target.value;
            } else {
                input.value = "";
            }
        });
        
        // Input 변경 시 select 리셋
        input.addEventListener("input", () => {
            select.value = "";
        });
    }
}

// Format number with commas on input event
function setupAmountInputFormatter(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.addEventListener("input", (e) => {
            // Remove non-numeric characters
            let val = e.target.value.replace(/[^0-9]/g, "");
            if (val) {
                e.target.value = Number(val).toLocaleString("ko-KR");
            } else {
                e.target.value = "";
            }
        });
    }
}

// Session Validation
async function checkSession() {
    try {
        const res = await fetch("/api/auth/me", {
            headers: {
                "Authorization": `Bearer ${sessionToken}`
            }
        });
        
        if (res.status === 200) {
            const data = await res.json();
            if (data.success) {
                updateUserInfoUI(data.user);
                return true;
            }
        }
        // Session invalid
        localStorage.removeItem("gj_session_token");
        sessionToken = null;
        return false;
    } catch (err) {
        console.error("Session verification failed", err);
        return false;
    }
}

// Show Login Page
function showLoginPage() {
    loginPage.classList.remove("hidden");
    appPage.classList.add("hidden");
    
    // Initialize Google Identity Services
    if (window.google && googleClientId) {
        window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: handleCredentialResponse
        });
        window.google.accounts.id.renderButton(
            document.getElementById("google-login-btn"),
            { theme: "outline", size: "large", width: "300" }
        );
        window.google.accounts.id.prompt(); // One Tap prompt
    } else {
        setTimeout(showLoginPage, 500); // SDK가 아직 안 불렸으면 재시도
    }
}

// Handle Google ID Token response
async function handleCredentialResponse(response) {
    showLoading(true);
    try {
        const loginRes = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: response.credential })
        });
        
        const loginData = await loginRes.json();
        
        if (loginRes.ok && loginData.success) {
            sessionToken = loginData.token;
            localStorage.setItem("gj_session_token", sessionToken);
            updateUserInfoUI(loginData.user);
            initDashboard();
            showToast("성공적으로 로그인되었습니다.", "success");
        } else {
            showToast(loginData.detail || "로그인 권한이 없습니다.", "error");
        }
    } catch (err) {
        showToast("서버 연결 실패", "error");
        console.error(err);
    } finally {
        showLoading(false);
    }
}

// Update User info header UI
function updateUserInfoUI(user) {
    document.getElementById("user-name").textContent = user.name;
    const avatar = document.getElementById("user-avatar");
    if (user.picture) {
        avatar.src = user.picture;
    } else {
        avatar.src = "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y";
    }
}

// Initialize Dashboard
function initDashboard() {
    loginPage.classList.add("hidden");
    appPage.classList.remove("hidden");
    
    // Reset Form Dates to Today
    resetFormDefaultDate();
    
    // Tab switching event setup
    setupTabs();
    
    // Search event setup
    setupSearch();
    
    // Form submission setup
    setupFormSubmission();
    
    // Logout button setup
    document.getElementById("btn-logout").addEventListener("click", logout);
}

// Reset Default Date for the form
function resetFormDefaultDate() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    document.getElementById("form-date").value = `${yyyy}-${mm}-${dd}`;
}

// Tab Switching
function setupTabs() {
    const navItems = document.querySelectorAll(".nav-item");
    const panels = document.querySelectorAll(".tab-panel");
    
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tabName = item.getAttribute("data-tab");
            
            navItems.forEach(nav => nav.classList.remove("active"));
            panels.forEach(p => p.classList.remove("active"));
            
            item.classList.add("active");
            document.getElementById(`tab-${tabName}`).classList.add("active");
            
            if (tabName === "search") {
                // 검색어 포커싱 및 딜레이 조회
                document.getElementById("search-input").focus();
            } else if (tabName === "add") {
                resetFormDefaultDate();
            }
        });
    });
}

// Search Logic
function setupSearch() {
    const searchInput = document.getElementById("search-input");
    const clearBtn = document.getElementById("btn-clear-search");
    
    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        
        if (query) {
            clearBtn.classList.remove("hidden");
        } else {
            clearBtn.classList.add("hidden");
        }
        
        // Debounce search (300ms)
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    clearBtn.addEventListener("click", () => {
        searchInput.value = "";
        clearBtn.classList.add("hidden");
        performSearch("");
        searchInput.focus();
    });
}

async function performSearch(query) {
    const listEl = document.getElementById("results-list");
    const countEl = document.getElementById("results-count");
    
    if (!query) {
        listEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔎</div>
                <p>이름을 입력해 검색을 시작해 보세요.</p>
            </div>
        `;
        countEl.textContent = "0";
        return;
    }
    
    try {
        const res = await fetch(`/api/events/search?query=${encodeURIComponent(query)}`, {
            headers: {
                "Authorization": `Bearer ${sessionToken}`
            }
        });
        
        if (res.status === 401) {
            // Expired session
            logout();
            return;
        }
        
        const data = await res.json();
        if (data.success) {
            renderSearchResults(data.data);
        } else {
            showToast("검색 로드 실패", "error");
        }
    } catch (err) {
        showToast("네트워크 에러 발생", "error");
        console.error(err);
    }
}

function renderSearchResults(items) {
    const listEl = document.getElementById("results-list");
    const countEl = document.getElementById("results-count");
    
    countEl.textContent = items.length;
    
    if (!items || items.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">😅</div>
                <p>일치하는 경조사 내역이 없습니다.</p>
            </div>
        `;
        return;
    }
    
    // Sort desc (newest date first)
    const sorted = [...items].sort((a, b) => {
        const dateA = a.날짜 || "0000-00-00";
        const dateB = b.날짜 || "0000-00-00";
        return dateB.localeCompare(dateA);
    });
    
    listEl.innerHTML = sorted.map(item => {
        const isDeposit = item.입출금 === "입금";
        const typeClass = isDeposit ? "deposit" : "withdraw";
        const typeLabel = isDeposit ? "받음" : "보냄";
        const amount = typeof item.축의금 === "number" ? item.축의금.toLocaleString("ko-KR") : item.축의금;
        
        return `
            <div class="event-card ${typeClass}">
                <div class="card-header">
                    <div class="card-title-group">
                        <span class="card-name">${item.이름 || '미기재'}</span>
                        <span class="card-tag">${typeLabel}</span>
                    </div>
                    <span class="card-date">${item.날짜 || '날짜미상'}</span>
                </div>
                <div class="card-body">
                    <div class="card-details">
                        <div class="detail-item">
                            <span class="detail-label">경조사:</span>
                            <span>${item.경조사명 || '미기재'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">소속:</span>
                            <span>${item.회사 || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">대상:</span>
                            <span>${item.누구 || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">방법:</span>
                            <span>${item.입출금방법 || '-'}</span>
                        </div>
                    </div>
                    <div class="card-amount-group">
                        <div class="card-amount-label">금액</div>
                        <div class="card-amount">${amount}원</div>
                    </div>
                    ${item.Remark ? `
                        <div class="card-remark">
                            <span>📝 비고: ${item.Remark}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join("");
}

// Form Submission (Add Record)
function setupFormSubmission() {
    const form = document.getElementById("event-form");
    const toggleContainer = form.querySelector(".toggle-container");
    const toggleButtons = toggleContainer.querySelectorAll(".toggle-btn");
    
    // 입출금 라디오 토글 이벤트 핸들러
    toggleButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            toggleButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            // 축의금 라벨 변경 등 스타일 동적 변경
            const type = btn.querySelector("input").value;
            const amountLabel = form.querySelector("label[for='form-amount']");
            if (type === "입금") {
                amountLabel.innerHTML = '축의금 / 부조금 <span class="required">*</span>';
            } else {
                amountLabel.innerHTML = '경조사 비용 <span class="required">*</span>';
            }
        });
    });

    // 참석 라디오 토글 이벤트 핸들러
    const attendContainer = form.querySelector(".toggle-container-simple");
    const attendButtons = attendContainer.querySelectorAll(".toggle-btn");
    attendButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            attendButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
        });
    });
    
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        // 폼 유효성 체크
        const date = document.getElementById("form-date").value;
        const name = document.getElementById("form-name").value.trim();
        const event = document.getElementById("form-event").value.trim();
        const amountStr = document.getElementById("form-amount").value.trim();
        const who = document.getElementById("form-who").value.trim();
        
        if (!date || !name || !event || !amountStr || !who) {
            showToast("필수 항목(*)을 모두 입력해 주세요.", "error");
            return;
        }
        
        // 전송 객체 구성
        const formData = new FormData(form);
        const submitData = {};
        formData.forEach((value, key) => {
            submitData[key] = value;
        });
        
        // 이름, 경조사명, 누구 트림
        submitData["이름"] = name;
        submitData["경조사명"] = event;
        submitData["누구"] = who;
        
        // 금액 콤마 제거 후 정수값으로
        const cleanAmount = amountStr.replace(/,/g, "");
        submitData["축의금"] = cleanAmount;
        
        showLoading(true);
        try {
            const res = await fetch("/api/events/add", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${sessionToken}`
                },
                body: JSON.stringify(submitData)
            });
            
            if (res.status === 401) {
                logout();
                return;
            }
            
            const data = await res.json();
            if (res.ok && data.success) {
                showToast("경조사가 스프레드시트에 정상 기록되었습니다.", "success");
                
                // 폼 리셋
                form.reset();
                resetFormDefaultDate();
                
                // 라디오 초기 상태로 복구
                toggleButtons.forEach(b => b.classList.remove("active"));
                toggleButtons[0].classList.add("active");
                attendButtons.forEach(b => b.classList.remove("active"));
                attendButtons[0].classList.add("active");
                
                // 조회 탭으로 강제 이동
                document.querySelector("[data-tab='search']").click();
                
                // 방금 등록한 이름으로 즉시 조회 수행
                document.getElementById("search-input").value = name;
                document.getElementById("btn-clear-search").classList.remove("hidden");
                performSearch(name);
            } else {
                showToast(data.detail || "경조사 등록 실패", "error");
            }
        } catch (err) {
            showToast("네트워크 통신 오류", "error");
            console.error(err);
        } finally {
            showLoading(false);
        }
    });
}

// User Logout
async function logout() {
    showLoading(true);
    try {
        await fetch("/api/auth/logout", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${sessionToken}`
            }
        });
    } catch (err) {
        console.error("Logout request failed", err);
    } finally {
        localStorage.removeItem("gj_session_token");
        window.location.reload();
    }
}

// Utility: Show Toast notification
function showToast(message, type = "info") {
    toastEl.textContent = message;
    toastEl.className = `toast-container ${type}`;
    toastEl.classList.remove("hidden");
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        toastEl.classList.add("hidden");
    }, 3000);
}

// Utility: Show Loading Overlay
function showLoading(show) {
    if (show) {
        loadingEl.classList.remove("hidden");
    } else {
        loadingEl.classList.add("hidden");
    }
}
