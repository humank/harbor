# Harbor — Frontend Coding Standards

All frontend code in `frontend/src/` MUST follow these standards.

---

## Tech Stack

- **React 18+** with functional components only. No class components.
- **TypeScript** strict mode. No `any` type unless absolutely necessary.
- **Tailwind CSS** for styling. No CSS modules, no styled-components, no inline styles.
- **React Router v6** for routing.
- **Fetch API** (native) or a thin wrapper for API calls. No axios.
- **Vite** for build tooling.

## Project Structure

```
frontend/src/
├── components/          # Shared, reusable UI components
│   ├── ui/              # Primitives (Button, Badge, Card, Modal, Table, Input)
│   └── layout/          # Layout components (Sidebar, Header, PageContainer)
├── pages/               # One file per route/page
│   ├── Dashboard.tsx
│   ├── AgentCatalog.tsx
│   ├── AgentDetail.tsx
│   ├── RegisterAgent.tsx
│   ├── Discovery.tsx
│   ├── DependencyGraph.tsx
│   ├── AuditLog.tsx
│   └── Settings.tsx
├── hooks/               # Custom React hooks
│   ├── useAgents.ts     # Agent CRUD operations
│   ├── useDiscovery.ts  # Discovery queries
│   └── useHealth.ts     # Health status
├── api/                 # API client layer
│   └── client.ts        # Typed fetch wrapper, base URL config
├── types/               # TypeScript type definitions
│   └── agent.ts         # AgentRecord, AgentSkill, etc. (mirrors backend models)
├── App.tsx              # Router + layout
└── main.tsx             # Entry point
```

## Component Rules

- One component per file. File name = component name (PascalCase).
- Props defined as TypeScript interface, exported from same file.
- Use `React.FC` is NOT required. Just type props directly.
- Shared components in `components/`. Page-specific components co-located in `pages/`.
- No prop drilling beyond 2 levels — use context or composition.

```tsx
// Good
interface AgentCardProps {
  agent: AgentRecord;
  onSelect: (id: string) => void;
}

export function AgentCard({ agent, onSelect }: AgentCardProps) {
  return <div>...</div>;
}
```

## Styling Rules

- Use Tailwind utility classes directly in JSX.
- For repeated patterns, extract to a component (not a CSS class).
- Color palette and design tokens defined via `tailwind.config.js`.
- Dark mode support via Tailwind `dark:` prefix (design system will define).
- Responsive: mobile-first. Use `sm:`, `md:`, `lg:` breakpoints.

## State Management

- Local state: `useState` / `useReducer`.
- Server state: custom hooks with `fetch` + `useEffect` (or React Query if added later).
- No Redux. No Zustand. Keep it simple until complexity demands it.
- API responses cached in hook state. Refetch on mutation.

## API Client

- Single `api/client.ts` file with typed functions.
- Base URL from environment variable (`VITE_API_BASE_URL`).
- All functions return typed responses matching backend Pydantic models.
- Handle errors consistently: throw on non-2xx, catch in hooks.

```typescript
// api/client.ts
const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function getAgents(status?: string): Promise<AgentRecord[]> {
  const url = status ? `${BASE}/agents?status=${status}` : `${BASE}/agents`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch agents: ${res.status}`);
  return res.json();
}
```

## TypeScript Rules

- Strict mode enabled in `tsconfig.json`.
- No `any`. Use `unknown` + type guards if type is uncertain.
- Interfaces for object shapes. Types for unions/intersections.
- Enums as `const` objects (not TypeScript `enum`).

```typescript
// Good
export const AgentStatus = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  DEPRECATED: 'deprecated',
  MAINTENANCE: 'maintenance',
} as const;

export type AgentStatus = typeof AgentStatus[keyof typeof AgentStatus];
```

## Build & Deploy

- Build: `npm run build` → outputs to `frontend/dist/`.
- Deploy: S3 sync + CloudFront invalidation (via CDK or script).
- Environment variables via `.env` files (Vite `VITE_` prefix).
- No server-side rendering. Pure static SPA.
