
## Getting Started

First, set the client token environmental variable:

```bash
export UNTITLEDAI_CLIENT_TOKEN=your-client-token
```

Optionally, set the google maps token if you want maps to work:

```bash
export NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-maps-token
```

Then, install the dependencies:

```bash
yarn install
# or
npm install
# or
pnpm install
# or
bun install
```


Then, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) 

IMPORTANT: Currently the webapp just passes the token for authentication there is no way to log in so do not expose this to the internet!