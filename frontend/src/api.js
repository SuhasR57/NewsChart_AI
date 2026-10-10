const API_BASE_URL = "http://127.0.0.1:8000";

function errorMessage(detail) {
    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail?.errors)) {
        return detail.errors.join("\n");
    }

    // FastAPI's request-validation errors.
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const field = item.loc?.slice(1).join(".") || "Request";
                return `${field}: ${item.msg || "Invalid value"}`;
            })
            .join("\n");
    }

    return "The request could not be completed.";
}

async function request(path, options = {}) {
    let response;

    try {
        response = await fetch(`${API_BASE_URL}${path}`, options);
    } catch (error) {
        if (error.name === "AbortError") {
            throw error;
        }

        throw new Error(
            "Cannot connect to the API. Check that the backend is running."
        );
    }

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error(
            `The API returned an unreadable response (${response.status}).`
        );
    }

    if (!response.ok) {
        throw new Error(errorMessage(result.detail));
    }

    return result;
}

export function previewCSV(file, signal) {
    const form = new FormData();
    form.append("file", file);

    return request("/preview", {
        method: "POST",
        body: form,
        signal,
    });
}

export function analyzeCSV(file, settings, signal) {
    const form = new FormData();
    form.append("file", file);

    for (const [name, value] of Object.entries(settings)) {
        form.append(name, value);
    }

    return request("/analyze", {
        method: "POST",
        body: form,
        signal,
    });
}

export function retryReport(analysisId, signal) {
    return request(
        `/analysis/${encodeURIComponent(analysisId)}/report/retry`,
        {
            method: "POST",
            signal,
        }
    );
}