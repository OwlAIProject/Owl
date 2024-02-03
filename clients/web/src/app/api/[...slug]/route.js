export async function GET(request) {
	const token = process.env.UNTITLEDAI_CLIENT_TOKEN;
    const incomingUrl = new URL(request.url);
    const newPathname = incomingUrl.pathname.replace(/^\/api/, '');
    const backendUrl = new URL(incomingUrl);
    backendUrl.pathname = newPathname;
    backendUrl.protocol = 'http'; 
    backendUrl.hostname = '127.0.0.1';
    backendUrl.port = '8000';
    const backendResponse = await fetch(backendUrl.toString(), {
        method: 'GET', 
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
    });

    const data = await backendResponse.json();

    return new Response(JSON.stringify(data), {
        status: backendResponse.status,
        headers: {
            'Content-Type': 'application/json',
        },
    });
}