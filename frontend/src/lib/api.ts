export interface PredictionResult {
    original_text: string;
    cleaned_text: string;
    prediction: "Real" | "Fake";
    confidence: number;
    is_fake: boolean;
}

// Interface for handling API errors consistently
export interface ApiError {
    status: "error";
    message: string;
}

const API_BASE_URL = 'http://localhost:1000';

/**
 * Checks a single news headline.
 * @param text The headline to check.
 * @returns A promise that resolves to a PredictionResult or an ApiError.
 */
export async function checkSingleNews(text: string): Promise<PredictionResult | ApiError> {
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        const data = await response.json();

        if (!response.ok) {
            return { status: "error", message: data.detail || `Server error: ${response.statusText}` };
        }

        return data as PredictionResult;
    } catch (error) {
        console.error("API Error (single):", error);
        return { status: "error", message: "Failed to connect to the prediction server." };
    }
}

/**
 * Checks a batch of news headlines.
 * @param texts An array of headlines to check.
 * @returns A promise that resolves to an array of PredictionResult or a single ApiError.
 */
export async function checkBulkNews(texts: string[]): Promise<PredictionResult[] | ApiError> {
    try {
        const response = await fetch(`${API_BASE_URL}/predict_bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texts }),
        });

        const data = await response.json();

        if (!response.ok) {
            return { status: "error", message: data.detail || `Server error: ${response.statusText}` };
        }

        return data as PredictionResult[];
    } catch (error) {
        console.error("API Error (bulk):", error);
        return { status: "error", message: "Failed to connect to the prediction server." };
    }
}

/**
 * Uploads an image file to the server for OCR + prediction.
 */
export async function checkImageUpload(file: File): Promise<PredictionResult | ApiError> {
    try {
        const form = new FormData();
        form.append('file', file);

        const response = await fetch(`${API_BASE_URL}/predict_image_upload`, {
            method: 'POST',
            body: form,
        });

        const data = await response.json();

        if (!response.ok) {
            return { status: "error", message: data.detail || `Server error: ${response.statusText}` };
        }

        return data as PredictionResult;
    } catch (error) {
        console.error("API Error (image upload):", error);
        return { status: "error", message: "Failed to connect to the prediction server." };
    }
}

/**
 * Sends an image URL to the server for OCR + prediction.
 */
export async function checkImageURL(url: string): Promise<PredictionResult | ApiError> {
    try {
        const response = await fetch(`${API_BASE_URL}/predict_image_url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        const data = await response.json();

        if (!response.ok) {
            return { status: "error", message: data.detail || `Server error: ${response.statusText}` };
        }

        return data as PredictionResult;
    } catch (error) {
        console.error("API Error (image url):", error);
        return { status: "error", message: "Failed to connect to the prediction server." };
    }
}
