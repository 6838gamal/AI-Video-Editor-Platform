/* =========================================================
   AI Video Editor
   Upload & YouTube Import
   ========================================================= */

(function () {
    "use strict";

    /* =====================================================
       CONFIG
    ===================================================== */

    const API_BASE = "/api";

    const ENDPOINTS = {
        upload: `${API_BASE}/videos/upload`,
        youtube: `${API_BASE}/videos/youtube`,
        videos: `${API_BASE}/videos`,
    };


    /* =====================================================
       ELEMENTS
    ===================================================== */

    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");

    const uploadProgress = document.getElementById("upload-progress");
    const barFill = document.getElementById("bar-fill");
    const uploadStatus = document.getElementById("upload-status");
    const uploadPercent = document.getElementById("upload-percent");
    const uploadError = document.getElementById("upload-error");

    const ytUrl = document.getElementById("yt-url");
    const ytDownloadBtn = document.getElementById("yt-download-btn");
    const ytError = document.getElementById("yt-error");
    const ytInfo = document.getElementById("yt-info");

    const videosList = document.getElementById("videos-list");
    const refreshVideos = document.getElementById("refresh-videos");

    const systemIndicator =
        document.getElementById("system-indicator");


    /* =====================================================
       STATE
    ===================================================== */

    let uploading = false;
    let downloadingYoutube = false;


    /* =====================================================
       HELPERS
    ===================================================== */

    function escapeHtml(value) {
        if (value === null || value === undefined) {
            return "";
        }

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    function setText(element, text) {
        if (element) {
            element.textContent = text || "";
        }
    }


    function showElement(element) {
        if (element) {
            element.classList.remove("hidden");
        }
    }


    function hideElement(element) {
        if (element) {
            element.classList.add("hidden");
        }
    }


    function setUploadProgress(percent, status) {
        const safePercent = Math.max(
            0,
            Math.min(100, Number(percent) || 0)
        );

        if (barFill) {
            barFill.style.width = `${safePercent}%`;
        }

        if (uploadPercent) {
            uploadPercent.textContent =
                `${Math.round(safePercent)}%`;
        }

        if (uploadStatus && status) {
            uploadStatus.textContent = status;
        }
    }


    function clearUploadError() {
        setText(uploadError, "");
    }


    function clearYoutubeMessages() {
        setText(ytError, "");
        setText(ytInfo, "");
    }


    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0) {
            return "0 B";
        }

        const units = [
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        ];

        const index = Math.min(
            Math.floor(Math.log(bytes) / Math.log(1024)),
            units.length - 1
        );

        const value =
            bytes / Math.pow(1024, index);

        return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
    }


    function formatDuration(seconds) {
        if (
            seconds === null ||
            seconds === undefined ||
            isNaN(seconds)
        ) {
            return "";
        }

        seconds = Math.max(0, Math.floor(seconds));

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor(
            (seconds % 3600) / 60
        );
        const secs = seconds % 60;

        if (hours > 0) {
            return [
                hours,
                String(minutes).padStart(2, "0"),
                String(secs).padStart(2, "0"),
            ].join(":");
        }

        return [
            minutes,
            String(secs).padStart(2, "0"),
        ].join(":");
    }


    async function parseResponse(response) {
        const contentType =
            response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            return await response.json();
        }

        const text = await response.text();

        return {
            detail: text,
        };
    }


    function getErrorMessage(data, fallback) {
        if (!data) {
            return fallback;
        }

        if (typeof data === "string") {
            return data;
        }

        if (data.detail) {

            if (Array.isArray(data.detail)) {
                return data.detail
                    .map(item => {
                        if (typeof item === "string") {
                            return item;
                        }

                        return (
                            item.msg ||
                            item.message ||
                            JSON.stringify(item)
                        );
                    })
                    .join("، ");
            }

            if (typeof data.detail === "object") {
                return (
                    data.detail.message ||
                    data.detail.msg ||
                    JSON.stringify(data.detail)
                );
            }

            return String(data.detail);
        }

        return (
            data.message ||
            data.error ||
            fallback
        );
    }


    function setButtonLoading(
        button,
        loading,
        loadingText,
        normalText
    ) {
        if (!button) {
            return;
        }

        if (loading) {
            button.disabled = true;
            button.dataset.originalText =
                button.innerHTML;

            button.innerHTML = `
                <span class="btn-spinner" aria-hidden="true"></span>
                <span>${escapeHtml(loadingText)}</span>
            `;
        } else {
            button.disabled = false;

            button.innerHTML =
                button.dataset.originalText ||
                normalText ||
                button.innerHTML;
        }
    }


    /* =====================================================
       SYSTEM STATUS
    ===================================================== */

    function updateSystemIndicator(available) {
        if (!systemIndicator) {
            return;
        }

        if (available) {
            systemIndicator.innerHTML = `
                <span
                    class="sys-dot"
                    style="background:#22c55e"
                ></span>
                <span>النظام يعمل بشكل طبيعي</span>
            `;
        } else {
            systemIndicator.innerHTML = `
                <span
                    class="sys-dot"
                    style="background:#f59e0b"
                ></span>
                <span>الوضع المتدني — قاعدة البيانات غير متاحة</span>
            `;
        }
    }


    async function checkSystemStatus() {
        try {
            const response = await fetch(
                `${API_BASE}/system/status`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json",
                    },
                    credentials: "include",
                }
            );

            if (!response.ok) {
                updateSystemIndicator(false);
                return false;
            }

            const data = await parseResponse(response);

            const available =
                data.available !== false &&
                data.database_available !== false &&
                data.database !== false;

            updateSystemIndicator(available);

            return available;

        } catch (error) {

            console.warn(
                "System status check failed:",
                error
            );

            updateSystemIndicator(false);

            return false;
        }
    }


    /* =====================================================
       FILE VALIDATION
    ===================================================== */

    function validateVideoFile(file) {
        if (!file) {
            return {
                valid: false,
                message: "لم يتم اختيار أي ملف."
            };
        }

        const maxSize =
            2 * 1024 * 1024 * 1024;

        if (file.size > maxSize) {
            return {
                valid: false,
                message:
                    "حجم الفيديو أكبر من الحد المسموح به (2GB)."
            };
        }

        const allowedExtensions = [
            "mp4",
            "mov",
            "mkv",
            "webm",
            "avi",
            "m4v",
            "mpeg",
            "mpg",
        ];

        const name =
            file.name.toLowerCase();

        const extension =
            name.includes(".")
                ? name.split(".").pop()
                : "";

        const isVideo =
            file.type.startsWith("video/") ||
            allowedExtensions.includes(extension);

        if (!isVideo) {
            return {
                valid: false,
                message:
                    "الملف المحدد ليس ملف فيديو مدعومًا."
            };
        }

        return {
            valid: true,
        };
    }


    /* =====================================================
       UPLOAD VIDEO
    ===================================================== */

    function uploadVideo(file) {

        return new Promise((resolve, reject) => {

            const validation =
                validateVideoFile(file);

            if (!validation.valid) {
                reject(
                    new Error(validation.message)
                );
                return;
            }


            const xhr = new XMLHttpRequest();

            const formData =
                new FormData();

            formData.append(
                "file",
                file,
                file.name
            );


            xhr.open(
                "POST",
                ENDPOINTS.upload,
                true
            );


            xhr.setRequestHeader(
                "Accept",
                "application/json"
            );


            xhr.withCredentials = true;


            xhr.upload.addEventListener(
                "progress",
                function (event) {

                    if (!event.lengthComputable) {
                        setUploadProgress(
                            0,
                            "جارٍ رفع الفيديو…"
                        );

                        return;
                    }

                    const percent =
                        (event.loaded / event.total) * 100;

                    setUploadProgress(
                        percent,
                        `جارٍ رفع ${file.name}…`
                    );

                }
            );


            xhr.addEventListener(
                "load",
                function () {

                    let data = null;

                    try {
                        data = xhr.responseText
                            ? JSON.parse(xhr.responseText)
                            : {};
                    } catch (_) {
                        data = {
                            detail: xhr.responseText
                        };
                    }


                    if (
                        xhr.status >= 200 &&
                        xhr.status < 300
                    ) {

                        resolve(data);

                    } else {

                        reject(
                            new Error(
                                getErrorMessage(
                                    data,
                                    `فشل رفع الفيديو (${xhr.status}).`
                                )
                            )
                        );

                    }

                }
            );


            xhr.addEventListener(
                "error",
                function () {

                    reject(
                        new Error(
                            "تعذر الاتصال بالخادم أثناء رفع الفيديو."
                        )
                    );

                }
            );


            xhr.addEventListener(
                "abort",
                function () {

                    reject(
                        new Error(
                            "تم إلغاء رفع الفيديو."
                        )
                    );

                }
            );


            xhr.addEventListener(
                "timeout",
                function () {

                    reject(
                        new Error(
                            "انتهت مهلة رفع الفيديو."
                        )
                    );

                }
            );


            xhr.timeout =
                30 * 60 * 1000;


            xhr.send(formData);

        });
    }


    async function handleFileUpload(file) {

        if (uploading) {
            return;
        }

        clearUploadError();

        const validation =
            validateVideoFile(file);

        if (!validation.valid) {
            setText(
                uploadError,
                validation.message
            );

            return;
        }


        uploading = true;

        showElement(uploadProgress);

        setUploadProgress(
            0,
            `جارٍ تجهيز ${file.name}…`
        );


        try {

            const result =
                await uploadVideo(file);


            setUploadProgress(
                100,
                "تم رفع الفيديو بنجاح ✓"
            );


            if (result && result.message) {
                setUploadProgress(
                    100,
                    result.message
                );
            }


            await loadVideos();


            setTimeout(
                function () {
                    hideElement(uploadProgress);
                },
                2500
            );


        } catch (error) {

            console.error(
                "Video upload failed:",
                error
            );

            setText(
                uploadError,
                error.message ||
                "فشل رفع الفيديو."
            );

            setUploadProgress(
                0,
                "فشل رفع الفيديو"
            );

        } finally {

            uploading = false;

            if (fileInput) {
                fileInput.value = "";
            }

        }
    }


    /* =====================================================
       DROPZONE
    ===================================================== */

    function setupDropzone() {

        if (!dropzone || !fileInput) {
            return;
        }


        dropzone.addEventListener(
            "click",
            function () {

                if (!uploading) {
                    fileInput.click();
                }

            }
        );


        dropzone.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter" ||
                    event.key === " "
                ) {

                    event.preventDefault();

                    if (!uploading) {
                        fileInput.click();
                    }

                }

            }
        );


        fileInput.addEventListener(
            "change",
            function () {

                const file =
                    fileInput.files &&
                    fileInput.files[0];

                if (file) {
                    handleFileUpload(file);
                }

            }
        );


        [
            "dragenter",
            "dragover",
        ].forEach(
            function (eventName) {

                dropzone.addEventListener(
                    eventName,
                    function (event) {

                        event.preventDefault();
                        event.stopPropagation();

                        if (!uploading) {
                            dropzone.classList.add(
                                "dragover"
                            );
                        }

                    }
                );

            }
        );


        [
            "dragleave",
            "dragend",
            "drop",
        ].forEach(
            function (eventName) {

                dropzone.addEventListener(
                    eventName,
                    function (event) {

                        event.preventDefault();
                        event.stopPropagation();

                        dropzone.classList.remove(
                            "dragover"
                        );

                    }
                );

            }
        );


        dropzone.addEventListener(
            "drop",
            function (event) {

                if (uploading) {
                    return;
                }

                const files =
                    event.dataTransfer &&
                    event.dataTransfer.files;

                if (!files || !files.length) {
                    return;
                }

                handleFileUpload(files[0]);

            }
        );

    }


    /* =====================================================
       YOUTUBE
    ===================================================== */

    function validateYoutubeUrl(value) {

        if (!value) {
            return {
                valid: false,
                message:
                    "يرجى إدخال رابط فيديو YouTube."
            };
        }


        let url;

        try {
            url = new URL(value);
        } catch (_) {
            return {
                valid: false,
                message:
                    "رابط YouTube غير صالح."
            };
        }


        const hostname =
            url.hostname.toLowerCase()
                .replace(/^www\./, "");


        const validHosts = [
            "youtube.com",
            "m.youtube.com",
            "youtu.be",
            "youtube-nocookie.com",
        ];


        const valid =
            validHosts.some(
                host =>
                    hostname === host ||
                    hostname.endsWith(`.${host}`)
            );


        if (!valid) {
            return {
                valid: false,
                message:
                    "يرجى إدخال رابط من YouTube فقط."
            };
        }


        return {
            valid: true,
        };
    }


    async function downloadYoutube() {

        if (downloadingYoutube) {
            return;
        }


        clearYoutubeMessages();


        const value =
            ytUrl
                ? ytUrl.value.trim()
                : "";


        const validation =
            validateYoutubeUrl(value);


        if (!validation.valid) {

            setText(
                ytError,
                validation.message
            );

            if (ytUrl) {
                ytUrl.focus();
            }

            return;
        }


        downloadingYoutube = true;


        setButtonLoading(
            ytDownloadBtn,
            true,
            "جارٍ التحميل…",
            "تحميل"
        );


        setText(
            ytInfo,
            "جارٍ معالجة رابط YouTube…"
        );


        try {

            const response =
                await fetch(
                    ENDPOINTS.youtube,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json",
                        },

                        credentials:
                            "include",

                        body: JSON.stringify({
                            url: value,
                        }),
                    }
                );


            const data =
                await parseResponse(response);


            if (!response.ok) {

                throw new Error(
                    getErrorMessage(
                        data,
                        `فشل تحميل الفيديو (${response.status}).`
                    )
                );

            }


            setText(
                ytInfo,
                data.message ||
                "تم إرسال الفيديو للمعالجة بنجاح ✓"
            );


            if (ytUrl) {
                ytUrl.value = "";
            }


            await loadVideos();


        } catch (error) {

            console.error(
                "YouTube download failed:",
                error
            );


            setText(
                ytError,
                error.message ||
                "تعذر تحميل فيديو YouTube."
            );


        } finally {

            downloadingYoutube = false;


            setButtonLoading(
                ytDownloadBtn,
                false,
                "جارٍ التحميل…",
                "تحميل"
            );

        }
    }


    function setupYoutube() {

        if (!ytDownloadBtn) {
            return;
        }


        ytDownloadBtn.addEventListener(
            "click",
            downloadYoutube
        );


        if (ytUrl) {

            ytUrl.addEventListener(
                "keydown",
                function (event) {

                    if (
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        downloadYoutube();

                    }

                }
            );

        }

    }


    /* =====================================================
       VIDEOS
    ===================================================== */

    function getVideoId(video) {
        return (
            video.id ||
            video.video_id ||
            video.uuid ||
            ""
        );
    }


    function getVideoTitle(video) {
        return (
            video.title ||
            video.name ||
            video.filename ||
            video.file_name ||
            "فيديو بدون عنوان"
        );
    }


    function getVideoStatus(video) {
        return (
            video.status ||
            video.state ||
            "جاهز"
        );
    }


    function getVideoUrl(video) {

        return (
            video.url ||
            video.file_url ||
            video.video_url ||
            video.download_url ||
            ""
        );
    }


    function getStatusLabel(status) {

        const labels = {
            ready: "جاهز",
            completed: "مكتمل",
            complete: "مكتمل",
            processing: "قيد المعالجة",
            pending: "قيد الانتظار",
            uploading: "جارٍ الرفع",
            failed: "فشل",
            error: "خطأ",
        };

        return (
            labels[String(status).toLowerCase()] ||
            status ||
            "جاهز"
        );
    }


    function renderVideos(videos) {

        if (!videosList) {
            return;
        }


        if (!Array.isArray(videos)) {
            videos = [];
        }


        if (videos.length === 0) {

            videosList.innerHTML = `
                <div class="empty-state">

                    <div class="empty-state-icon">
                        🎞️
                    </div>

                    <p class="empty-state-title">
                        لا توجد فيديوهات بعد
                    </p>

                    <p class="empty-state-text">
                        ارفع فيديو أو أضف رابط YouTube للبدء.
                    </p>

                </div>
            `;

            return;
        }


        videosList.innerHTML =
            videos.map(
                function (video) {

                    const id =
                        escapeHtml(
                            getVideoId(video)
                        );

                    const title =
                        escapeHtml(
                            getVideoTitle(video)
                        );

                    const status =
                        escapeHtml(
                            getVideoStatus(video)
                        );

                    const statusLabel =
                        escapeHtml(
                            getStatusLabel(status)
                        );

                    const url =
                        escapeHtml(
                            getVideoUrl(video)
                        );

                    const size =
                        video.file_size
                            ? formatFileSize(
                                video.file_size
                            )
                            : "";

                    const duration =
                        video.duration
                            ? formatDuration(
                                video.duration
                            )
                            : "";


                    return `
                        <article
                            class="video-item"
                            data-video-id="${id}"
                        >

                            <div class="video-thumb">
                                ${
                                    video.thumbnail_url
                                        ? `
                                            <img
                                                src="${escapeHtml(video.thumbnail_url)}"
                                                alt="${title}"
                                                loading="lazy"
                                            >
                                        `
                                        : `
                                            <span>
                                                🎬
                                            </span>
                                        `
                                }
                            </div>


                            <div class="video-info">

                                <h3 class="video-title">
                                    ${title}
                                </h3>

                                <div class="video-meta">

                                    ${
                                        size
                                            ? `<span>${escapeHtml(size)}</span>`
                                            : ""
                                    }

                                    ${
                                        duration
                                            ? `<span>${escapeHtml(duration)}</span>`
                                            : ""
                                    }

                                    <span
                                        class="video-status"
                                        data-status="${escapeHtml(status)}"
                                    >
                                        ${statusLabel}
                                    </span>

                                </div>

                            </div>


                            ${
                                url
                                    ? `
                                        <a
                                            href="${url}"
                                            class="btn btn-ghost btn-sm"
                                            target="_blank"
                                            rel="noopener"
                                        >
                                            فتح
                                        </a>
                                    `
                                    : ""
                            }

                        </article>
                    `;
                }
            ).join("");
    }


    function extractVideos(data) {

        if (Array.isArray(data)) {
            return data;
        }


        if (data && Array.isArray(data.videos)) {
            return data.videos;
        }


        if (data && Array.isArray(data.items)) {
            return data.items;
        }


        if (data && Array.isArray(data.results)) {
            return data.results;
        }


        return [];
    }


    async function loadVideos() {

        if (!videosList) {
            return;
        }


        try {

            if (refreshVideos) {
                refreshVideos.disabled = true;
            }


            const response =
                await fetch(
                    ENDPOINTS.videos,
                    {
                        method: "GET",

                        headers: {
                            "Accept":
                                "application/json",
                        },

                        credentials:
                            "include",
                    }
                );


            const data =
                await parseResponse(response);


            if (!response.ok) {

                /*
                 * عدم توفر قاعدة البيانات أو endpoint
                 * لا يجب أن يكسر الصفحة.
                 */

                if (
                    response.status === 404 ||
                    response.status === 503
                ) {

                    renderVideos([]);

                    return;
                }


                throw new Error(
                    getErrorMessage(
                        data,
                        "تعذر تحميل الفيديوهات."
                    )
                );
            }


            const videos =
                extractVideos(data);


            renderVideos(videos);


        } catch (error) {

            console.warn(
                "Loading videos failed:",
                error
            );


            /*
             * الوضع المتدني:
             * لا نعرض خطأ قاتل للمستخدم.
             */

            renderVideos([]);


        } finally {

            if (refreshVideos) {
                refreshVideos.disabled = false;
            }

        }
    }


    function setupRefresh() {

        if (!refreshVideos) {
            return;
        }


        refreshVideos.addEventListener(
            "click",
            async function () {

                const original =
                    refreshVideos.innerHTML;


                refreshVideos.disabled = true;

                refreshVideos.innerHTML = `
                    <span class="refresh-icon">
                        ↻
                    </span>
                    <span>
                        جارٍ التحديث…
                    </span>
                `;


                try {
                    await loadVideos();
                } finally {

                    refreshVideos.disabled = false;

                    refreshVideos.innerHTML =
                        original;

                }

            }
        );

    }


    /* =====================================================
       EXTRA CSS FOR JS STATES
    ===================================================== */

    function injectRuntimeStyles() {

        if (
            document.getElementById(
                "upload-runtime-styles"
            )
        ) {
            return;
        }


        const style =
            document.createElement("style");


        style.id =
            "upload-runtime-styles";


        style.textContent = `
            .btn-spinner {
                width: 14px;
                height: 14px;

                border: 2px solid
                    currentColor;

                border-right-color:
                    transparent;

                border-radius: 50%;

                display: inline-block;

                animation:
                    upload-spin
                    .7s linear infinite;
            }

            @keyframes upload-spin {
                to {
                    transform: rotate(360deg);
                }
            }

            .video-item {
                display: flex;
                align-items: center;

                gap: 12px;

                padding: 12px 0;

                border-bottom:
                    1px solid var(--border);
            }

            .video-item:last-child {
                border-bottom: 0;
            }

            .video-thumb {
                width: 78px;
                height: 52px;

                flex: 0 0 78px;

                overflow: hidden;

                display: flex;
                align-items: center;
                justify-content: center;

                border-radius: 8px;

                background:
                    #f3f4f6;

                font-size: 20px;
            }

            .video-thumb img {
                width: 100%;
                height: 100%;

                object-fit: cover;
            }

            .video-info {
                flex: 1;
                min-width: 0;
            }

            .video-title {
                margin: 0 0 5px;

                font-size: 13px;
                font-weight: 700;

                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .video-meta {
                display: flex;
                align-items: center;
                flex-wrap: wrap;

                gap: 7px;

                color:
                    var(--text-secondary);

                font-size: 10px;
            }

            .video-status {
                padding: 2px 6px;

                border-radius: 5px;

                background:
                    #f3f4f6;
            }

            @media (max-width: 480px) {

                .video-item {
                    gap: 9px;
                }

                .video-thumb {
                    width: 62px;
                    height: 44px;

                    flex-basis: 62px;
                }

                .video-title {
                    font-size: 11px;
                }

                .video-meta {
                    font-size: 9px;
                }

            }

            @media (max-width: 360px) {

                .video-thumb {
                    width: 54px;
                    height: 40px;

                    flex-basis: 54px;
                }

                .video-item .btn {
                    padding:
                        5px 7px;

                    min-height: 32px;
                }

            }
        `;


        document.head.appendChild(style);

    }


    /* =====================================================
       INITIALIZATION
    ===================================================== */

    async function initialize() {

        injectRuntimeStyles();

        setupDropzone();

        setupYoutube();

        setupRefresh();

        /*
         * لا نمنع تحميل الصفحة بسبب فشل API.
         */

        checkSystemStatus();

        loadVideos();

    }


    if (
        document.readyState === "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initialize
        );

    } else {

        initialize();

    }


    /* =====================================================
       PUBLIC API
       مفيد إذا احتاج app.js أو صفحات أخرى
       إعادة تحميل الفيديوهات.
    ===================================================== */

    window.VideoUploader = {
        upload: handleFileUpload,
        loadVideos: loadVideos,
        checkSystemStatus:
            checkSystemStatus,
    };

})();
