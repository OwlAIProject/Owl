async function fetchFromBackend(url, options) {
    const token = process.env.OWL_USER_CLIENT_TOKEN;
    const incomingUrl = new URL(url);
    const newPathname = incomingUrl.pathname.replace(/^\/api/, '');

    if (newPathname === '/tokens') {
        return new Response(JSON.stringify({
            OWL_USER_CLIENT_TOKEN: token,
            GOOGLE_MAPS_API_KEY: process.env.GOOGLE_MAPS_API_KEY
        }), {
            status: 200,
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    const backendBaseUrl = process.env.OWL_API_URL || 'http://127.0.0.1:8000';
    const backendUrl = new URL(newPathname, backendBaseUrl);

    const backendOptions = {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers,
        },
    };

    const backendResponse = await fetch(backendUrl.toString(), backendOptions);
    const data = await backendResponse.json();

    return new Response(JSON.stringify(data), {
        status: backendResponse.status,
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