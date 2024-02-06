// Utility function to handle fetching to the backend
async function fetchFromBackend(url, options) {
    const token = process.env.NEXT_PUBLIC_UNTITLEDAI_CLIENT_TOKEN; 
    const incomingUrl = new URL(url);
    const newPathname = incomingUrl.pathname.replace(/^\/api/, '');
    const backendUrl = new URL(incomingUrl);
    backendUrl.pathname = newPathname;
    backendUrl.protocol = 'http';
    backendUrl.hostname = '127.0.0.1';
    backendUrl.port = '8000';

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
