/**
 * Enhanced Classroom Feedback System - Frontend
 * Features: Input validation, sanitization, anonymous submissions, and analytics
 */

const API_BASE = "http://localhost:5000";

// State management
let currentCourse = "CS101";
let backendHealthy = false;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener("DOMContentLoaded", function() {
    checkBackendHealth();
    setupEventListeners();
    loadStoredStudent();
    toggleStudentId();
    loadStoredCourse();
});

function setupEventListeners() {
    const form = document.getElementById("feedbackForm");
    if (form) {
        form.addEventListener("submit", handleFeedbackSubmit);
    }
}

// ============================================
// UI FUNCTIONS
// ============================================

function showTab(tabName, button) {
    // Hide all tabs
    document.querySelectorAll(".tab-section").forEach(tab => {
        tab.classList.remove("active");
    });

    // Show selected tab
    const activeTab = document.getElementById(tabName);
    if (activeTab) {
        activeTab.classList.add("active");
    }

    // Update button states
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
    });
    if (button) {
        button.classList.add("active");
    }

    // Load data for specific tabs
    if (tabName === "dashboard") {
        loadAnalytics();
    } else if (tabName === "profile") {
        loadProfileData();
    }
}

function toggleStudentId() {
    const anonymous = document.getElementById("anonymous").checked;
    const studentIdGroup = document.getElementById("studentIdGroup");
    const studentInput = document.getElementById("studentId");

    if (anonymous) {
        studentIdGroup.style.display = "none";
        studentInput.required = false;
        studentInput.value = "";
    } else {
        studentIdGroup.style.display = "block";
        studentInput.required = true;
    }
}

// ============================================
// VALIDATION & SANITIZATION
// ============================================

/**
 * Sanitize user input to prevent XSS
 */
function sanitizeInput(input) {
    const div = document.createElement("div");
    div.textContent = input;
    return div.innerHTML;
}

/**
 * Validate student ID format
 */
function validateStudentId(studentId) {
    const pattern = /^[A-Za-z0-9]{3,20}$/;
    return pattern.test(studentId);
}

/**
 * Validate text length
 */
function validateTextLength(text, min, max) {
    const cleanText = text.trim();
    return cleanText.length >= min && cleanText.length <= max;
}

/**
 * Comprehensive form validation
 */
function validateForm() {
    const anonymous = document.getElementById("anonymous").checked;
    const courseId = document.getElementById("courseId").value;
    const studentId = document.getElementById("studentId").value.trim();

    // Validate course selection
    if (!courseId) {
        showNotification("? Please select a course", "error");
        return false;
    }

    // Validate student ID if not anonymous
    if (!anonymous) {
        if (!studentId) {
            showNotification("? Please enter your student ID or select anonymous", "error");
            return false;
        }
        if (!validateStudentId(studentId)) {
            showNotification("? Student ID must be 3-20 alphanumeric characters", "error");
            return false;
        }
    }

    // Validate all required radio buttons
    const requiredRadios = ["clarity", "pace", "difficulty", "participation"];
    for (const name of requiredRadios) {
        const selected = document.querySelector(`input[name="${name}"]:checked`);
        if (!selected) {
            showNotification(`? Please answer: ${name}`, "error");
            return false;
        }
    }

    // Validate selects
    const materials = document.querySelector("select[name='materials']");
    const support = document.querySelector("select[name='support']");
    const encouragement = document.querySelector("select[name='encouragement']");
    const overall = document.querySelector("select[name='overall']");
    if (!materials || !materials.value) {
        showNotification("? Please select course materials helpfulness", "error");
        return false;
    }
    if (!support || !support.value) {
        showNotification("? Please select instructor responsiveness", "error");
        return false;
    }
    if (!encouragement || !encouragement.value) {
        showNotification("? Please select whether the instructor encouraged participation", "error");
        return false;
    }
    if (!overall || !overall.value) {
        showNotification("? Please select your overall satisfaction", "error");
        return false;
    }

    // Validate textareas
    const keyLearning = document.getElementById("keyLearning").value.trim();
    const suggestions = document.getElementById("suggestions").value.trim();
    const recommendation = document.querySelector("input[name='recommendation']:checked");

    if (!validateTextLength(keyLearning, 10, 500)) {
        showNotification("? Key learning must be 10-500 characters", "error");
        return false;
    }
    if (!validateTextLength(suggestions, 10, 1000)) {
        showNotification("? Suggestions must be 10-1000 characters", "error");
        return false;
    }
    if (!recommendation) {
        showNotification("? Please answer recommendation question", "error");
        return false;
    }

    return true;
}

// ============================================
// FORM SUBMISSION & API CALLS
// ============================================

async function handleFeedbackSubmit(event) {
    event.preventDefault();

    // Validate form
    if (!validateForm()) {
        return;
    }

    const submitBtn = event.target.querySelector("button[type='submit']");
    if (submitBtn) {
        submitBtn.disabled = true;
    }

    try {
        // Collect form data
        const anonymous = document.getElementById("anonymous").checked;
        const courseId = document.getElementById("courseId").value;
        const studentId = anonymous ? null : sanitizeInput(document.getElementById("studentId").value.trim());

        // Collect all responses
        const resolutionMap = {
            5: 'excellent',
            4: 'good',
            3: 'average',
            2: 'poor',
            1: 'no_support'
        };

        const participationValue = document.querySelector("input[name='participation']:checked").value;
        const participationLabels = {
            5: 'very_active',
            4: 'active',
            3: 'neutral',
            2: 'passive',
            1: 'inactive'
        };

        const feedbackData = {
            course_id: courseId,
            student_id: studentId,
            anonymous: anonymous,
            feedback: {
                teaching_quality: {
                    clarity: parseInt(document.querySelector("input[name='clarity']:checked").value),
                    pace: parseInt(document.querySelector("input[name='pace']:checked").value),
                    explanation: parseInt(document.querySelector("select[name='materials']").value)
                },
                student_engagement: {
                    interaction: parseInt(participationValue),
                    participation: participationLabels[participationValue],
                    encouragement: parseInt(document.querySelector("select[name='encouragement']").value)
                },
                content_understanding: {
                    difficulty: parseInt(document.querySelector("input[name='difficulty']:checked").value),
                    clarity: parseInt(document.querySelector("select[name='materials']").value)
                },
                doubt_support: {
                    resolution: resolutionMap[parseInt(document.querySelector("select[name='support']").value)]
                },
                overall_experience: {
                    rating: parseInt(document.querySelector("select[name='overall']").value),
                    text: sanitizeInput(document.getElementById("suggestions").value)
                }
            },
            timestamp: new Date().toISOString()
        };

        const response = await fetch(`${API_BASE}/submit-feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(feedbackData)
        });

        if (response.ok) {
            saveCourseId(courseId);
            saveStudentId(studentId);
            showNotification("? Thank you! Your feedback has been submitted successfully.", "success");
            document.getElementById("feedbackForm").reset();
            toggleStudentId(); // Reset student ID visibility
        } else {
            const error = await response.json();
            showNotification(`? ${error.error || "Failed to submit feedback"}`, "error");
        }
    } catch (error) {
        console.error("Submission error:", error);
        showNotification("? Network error. Please check your connection and try again.", "error");
    } finally {
        submitBtn.disabled = false;
    }
}

// ============================================
// NOTIFICATIONS
// ============================================

function showNotification(message, type = "success") {
    const notification = document.getElementById("notification");
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = "block";

    setTimeout(() => {
        notification.style.display = "none";
    }, 5000);
}

// ============================================
// LOCAL STORAGE
// ============================================

function loadStoredStudent() {
    const stored = localStorage.getItem("studentId");
    if (stored && !document.getElementById("anonymous").checked) {
        document.getElementById("studentId").value = stored;
    }
}

function saveStudentId(studentId) {
    if (studentId && !document.getElementById("anonymous").checked) {
        localStorage.setItem("studentId", studentId);
    }
}

function loadStoredCourse() {
    const storedCourse = localStorage.getItem("lastCourseId");
    const selector = document.getElementById("courseSelector");
    if (storedCourse && selector) {
        const optionExists = Array.from(selector.options).some(opt => opt.value === storedCourse);
        if (optionExists) {
            selector.value = storedCourse;
            currentCourse = storedCourse;
        }
    }
}

function saveCourseId(courseId) {
    if (courseId) {
        localStorage.setItem("lastCourseId", courseId);
    }
}

// ============================================
// DASHBOARD & ANALYTICS
// ============================================

async function loadAnalytics(fallbackToAnyCourse = true) {
    const courseId = document.getElementById("courseSelector")?.value || currentCourse;

    const fallbackData = {
        total_feedbacks: 30,
        avg_overall_rating: 4.3,
        sentiment_distribution: { positive: 18, neutral: 7, negative: 5 },
        activity_stats: { submission_trends: { "Day 1": 4, "Day 2": 6, "Day 3": 8, "Day 4": 5, "Day 5": 7 } }
    };

    try {
        const response = await fetch(`${API_BASE}/api/analytics/course/${courseId}`);
        if (!response.ok) {
            if (response.status === 404 && fallbackToAnyCourse) {
                const listResponse = await fetch(`${API_BASE}/api/feedback/list`);
                if (listResponse.ok) {
                    const listData = await listResponse.json();
                    const availableCourses = Array.from(new Set(
                        (listData.feedbacks || []).map(item => item.course_id).filter(Boolean)
                    ));

                    if (availableCourses.length && availableCourses[0] !== courseId) {
                        document.getElementById("courseSelector").value = availableCourses[0];
                        showNotification(`No analytics for ${courseId}. Showing data for ${availableCourses[0]}.`, "warning");
                        return loadAnalytics(false);
                    }
                }
            }

            showNotification("Could not load analytics from server, showing sample data.", "warning");
            updateAnalyticsCards(fallbackData);
            createCharts(fallbackData);
            return;
        }

        const data = await response.json();
        updateAnalyticsCards(data);
        createCharts(data);
    } catch (error) {
        console.error("Analytics error:", error);
        showNotification("Unable to fetch analytics, displaying sample data.", "warning");
        updateAnalyticsCards(fallbackData);
        createCharts(fallbackData);
    }
}

function updateAnalyticsCards(data) {
    const sentiment = data.sentiment_distribution || {};
    const total = data.total_feedbacks || 0;
    const positive = sentiment.positive || 0;
    const neutral = sentiment.neutral || 0;
    const negative = sentiment.negative || 0;
    const positivePercent = total ? Math.round((positive / total) * 100) : 0;
    const neutralPercent = total ? Math.round((neutral / total) * 100) : 0;
    const negativePercent = total ? Math.round((negative / total) * 100) : 0;

    document.getElementById("averageRating").textContent = data.avg_overall_rating !== undefined ? data.avg_overall_rating : "--";
    document.getElementById("averageRating").dataset.count = total;
    document.getElementById("averageRating").dataset.positive = positivePercent;
    document.getElementById("averageRating").dataset.neutral = neutralPercent;
    document.getElementById("averageRating").dataset.negative = negativePercent;
}

function createCharts(data) {
    const sentiment = data.sentiment_distribution || {};
    const total = data.total_feedbacks || 0;
    const positive = sentiment.positive || 0;
    const neutral = sentiment.neutral || 0;
    const negative = sentiment.negative || 0;
    const positivePercent = total ? Math.round((positive / total) * 100) : 0;
    const neutralPercent = total ? Math.round((neutral / total) * 100) : 0;
    const negativePercent = total ? Math.round((negative / total) * 100) : 0;

    // Sentiment chart
    const sentimentCtx = document.getElementById("sentimentChart");
    if (sentimentCtx && sentimentCtx.chart) {
        sentimentCtx.chart.destroy();
    }

    if (sentimentCtx) {
        const doughData = total ? [positivePercent, neutralPercent, negativePercent] : [20, 20, 20];

        const chart = new Chart(sentimentCtx, {
            type: "doughnut",
            data: {
                labels: ["Positive", "Neutral", "Negative"],
                datasets: [{
                    data: doughData,
                    backgroundColor: ["#22c55e", "#facc15", "#fb7185"],
                    borderColor: ["#0f172a", "#0f172a", "#0f172a"],
                    borderWidth: 2,
                    hoverOffset: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: context => `${context.label}: ${context.parsed}%`
                        }
                    }
                }
            }
        });
        sentimentCtx.chart = chart;
    }

    const trendsCtx = document.getElementById("trendsChart");
    if (trendsCtx && trendsCtx.chart) {
        trendsCtx.chart.destroy();
    }

    if (trendsCtx) {
        const submissions = (data.activity_stats && data.activity_stats.submission_trends) || {};
        const trendLabels = Object.keys(submissions);
        const trendValues = Object.values(submissions);

        const chart = new Chart(trendsCtx, {
            type: "line",
            data: {
                labels: trendLabels,
                datasets: [{
                    label: "Submissions",
                    data: trendValues,
                    borderColor: "#38bdf8",
                    backgroundColor: "rgba(56, 189, 248, 0.25)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 5,
                    pointBackgroundColor: "#f472b6",
                    pointBorderColor: "#ffffff",
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        ticks: { color: "#cbd5e1" },
                        grid: { color: "rgba(148, 163, 184, 0.12)" }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: "#cbd5e1" },
                        grid: { color: "rgba(148, 163, 184, 0.12)" }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        trendsCtx.chart = chart;
    }
}

function onCourseChange() {
    currentCourse = document.getElementById("courseSelector").value;
    saveCourseId(currentCourse);
    loadAnalytics();
}

// ============================================
// PROFILE PAGE
// ============================================

function loadProfileData() {
    const studentId = localStorage.getItem("studentId");
    document.getElementById("profileStudentId").textContent = studentId || "Not provided (Anonymous)";
}

// ============================================
// BACKEND HEALTH CHECK
// ============================================

async function checkBackendHealth() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    try {
        const response = await fetch(`${API_BASE}/health`, { signal: controller.signal });
        backendHealthy = response.ok;
        console.log("? Backend is healthy");
    } catch (error) {
        backendHealthy = false;
        console.warn("?? Backend not available - using offline mode", error);
    } finally {
        clearTimeout(timeoutId);
    }
}
