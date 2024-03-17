async function fetchFromBackend(url, options) {
    const token = process.env.OWL_USER_CLIENT_TOKEN;
    const incomingUrl = new URL(url);
    const newPathname = incomingUrl.pathname.replace(/^\/api/, '');

    if (newPathname === '/tokens') {
        return new Response(JSON.stringify({
            OWL_USER_CLIENT_TOKEN: token,
            OWL_GOOGLE_MAPS_API_KEY: process.env.OWL_GOOGLE_MAPS_API_KEY
        }), {
            status: 200,
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    const apiBaseUrl = process.env.OWL_WEB_API_BASE_URL || 'http://localhost:8000';
    const apiUrl = new URL(newPathname, apiBaseUrl);

    const apiOptions = {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers,
        },
    };

    const apiResponse = await fetch(apiUrl.toString(), apiOptions);
    const data = await apiResponse.json();

    return new Response(JSON.stringify(data), {
        status: apiResponse.status,
        headers: {
            'Content-Type': 'application/json',
        },
    });
}

export async function GET(request) {
    return fetchFromBackend(request.url, { method: 'GET' });
}

export async function POST(request) {
    const body = await request.json();
    return fetchFromBackend(request.url, {
        method: 'POST',
        body: JSON.stringify(body),
    });
}