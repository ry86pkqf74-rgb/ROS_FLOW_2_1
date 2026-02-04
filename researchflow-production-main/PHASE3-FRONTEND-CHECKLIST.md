# ResearchFlow Phase 3A: React Web Application Deployment Checklist

**Date:** January 29, 2026  
**Service:** Web (services/web)  
**Framework:** React 18 + TypeScript + Vite  
**UI System:** shadcn/ui + Tailwind CSS  
**Status:** Ready for Deployment

---

## Overview

This checklist covers the React web application deployment for ResearchFlow. The application is a complex research workflow management system featuring real-time dashboards, collaborative editing, and governance controls.

**Key Stats:**
- **Build Tool:** Vite 6.2.0 (ES modules, fast HMR)
- **React Version:** 18.3.1
- **Bundle Strategy:** 14+ vendor chunks with granular caching
- **UI Components:** 80+ shadcn/ui + Radix UI primitives
- **Pages:** 30+ pages with advanced features

---

## Section 1: Frontend Configuration Verification

### 1.1 Vite Configuration Status

**File:** `/services/web/vite.config.ts`

- [x] Production plugins configured (gzip + brotli compression)
- [x] Bundle analysis plugin enabled (rollup-plugin-visualizer)
- [x] React plugin configured with proper JSX transformation
- [x] Path aliases configured (@/, @packages/core, @packages/design-system)
- [x] Development proxy configured (/api → localhost:3001)
- [x] Source maps disabled in production (security)
- [x] Esbuild minification configured
- [x] Console log stripping enabled for production
- [x] CSS code splitting enabled
- [x] Dynamic import support configured

**Chunk Size Warning Limit:** 500KB
**Target:** ES2020 (modern browsers)
**Output Directory:** dist/

### 1.2 TypeScript Configuration Status

**File:** `/services/web/tsconfig.json`

- [x] Target: ES2020
- [x] Module: ESNext (for tree-shaking)
- [x] Strict mode: Partially enabled
  - [x] noImplicitAny: true
  - [x] noFallthroughCasesInSwitch: true
  - [x] Full strict mode disabled (pragmatic legacy migration)
- [x] JSX: react-jsx (fast refresh compatible)
- [x] Module resolution: bundler
- [x] Path aliases configured:
  - @/* → ./src/*
  - @packages/core → ../../packages/core
  - @packages/core/* → ../../packages/core/*
- [x] skipLibCheck: true (faster compilation)
- [x] resolveJsonModule: true
- [x] isolatedModules: true

### 1.3 Package.json Dependencies Status

**File:** `/services/web/package.json`

**Core Dependencies (26 items):**
- [x] react@18.3.1
- [x] react-dom@18.3.1
- [x] @vitejs/plugin-react@4.3.1
- [x] vite@6.2.0
- [x] typescript@5.4.5

**UI & Components (35+ Radix UI packages):**
- [x] @radix-ui/react-* (complete accordion, dialog, dropdown, tabs, etc.)
- [x] lucide-react@0.400.0 (icon library)
- [x] class-variance-authority@0.7.0 (component variants)
- [x] clsx@2.1.1 (className utility)

**Styling:**
- [x] tailwindcss@3.4.4
- [x] @tailwindcss/forms@0.5.11
- [x] @tailwindcss/typography@0.5.19
- [x] tailwindcss-animate@1.0.7
- [x] postcss@8.4.38
- [x] autoprefixer@10.4.19

**Data & State Management:**
- [x] @tanstack/react-query@5.51.1 (data fetching with caching)
- [x] zustand@5.0.10 (state management)
- [x] axios@1.7.2 (HTTP client)

**Rich Text & Collaboration:**
- [x] prosemirror-view@1.37.2
- [x] prosemirror-model@1.24.2
- [x] y-prosemirror@1.2.15 (CRDT collaborative editing)
- [x] yjs@13.6.23
- [x] y-websocket@2.1.0

**Forms & Validation:**
- [x] react-hook-form@7.71.1
- [x] @hookform/resolvers@5.2.2
- [x] zod@3.23.8 (schema validation)

**Utilities:**
- [x] date-fns@4.1.0
- [x] framer-motion@12.27.3 (animations)
- [x] drizzle-orm@0.31.2 (optional - ORM utilities)
- [x] wouter@3.3.5 (routing)
- [x] reactflow@11.11.4 (diagram/flow visualization)
- [x] recharts@2.15.3 (charting library)
- [x] i18next@23.11.5 (internationalization)
- [x] cmdk@1.1.1 (command palette)

**Dev Dependencies (11 items):**
- [x] @typescript-eslint/* (linting)
- [x] eslint@9.39.2
- [x] vite-plugin-compression@0.5.1 (gzip/brotli)
- [x] rollup-plugin-visualizer@5.12.0 (bundle analysis)

---

## Section 2: Design System & UI Component Setup

### 2.1 Tailwind CSS Configuration Status

**File:** `/services/web/tailwind.config.js`

**Dark Mode:**
- [x] Class-based dark mode enabled

**Content Paths:**
- [x] ./index.html
- [x] ./src/**/*.{js,ts,jsx,tsx}
- [x] ../../packages/**/*.{js,ts,jsx,tsx}

**Theme Extensions:**

**Border Radius Tokens:**
- ds-sm: 4px
- ds-md: 8px
- ds-lg: 12px

**Typography Scale (Design System):**
- ds-display: 48px (700 weight)
- ds-h1: 32px (600 weight)
- ds-h2: 24px (600 weight)
- ds-h3: 20px (500 weight)
- ds-body: 16px (400 weight)
- ds-caption: 14px (400 weight)

**Spacing Scale:**
- ds-xs: 4px
- ds-sm: 8px
- ds-md: 16px
- ds-lg: 24px
- ds-xl: 32px
- ds-2xl: 48px

**Color System:**
- [x] Semantic colors (primary, secondary, muted, accent, destructive, ring)
- [x] Governance colors (red, yellow, green, blue)
- [x] ROS primary palette (primary, success, workflow, alert, neutral)
- [x] Design System colors:
  - Ocean Blue (#2B8DD6)
  - Success Green (#22C55E)
  - Creative Purple (#8B5CF6)
  - Warm Coral (#EF4444)
  - Golden Amber (#F97316)
- [x] Sidebar colors and variants
- [x] Chart colors (chart-1 through chart-5)
- [x] Status colors (online, away, busy, offline)

**Shadow Definitions:**
- ds-sm: 0 1px 2px rgba(0,0,0,0.05)
- ds-md: 0 4px 6px rgba(0,0,0,0.1)
- ds-lg: 0 10px 15px rgba(0,0,0,0.1)

**Plugins:**
- [x] tailwindcss-animate
- [x] @tailwindcss/typography

**Z-Index:**
- [x] safety-banner: 9999

### 2.2 PostCSS Configuration Status

**File:** `/services/web/postcss.config.js`

- [x] Tailwind CSS plugin configured
- [x] Autoprefixer configured for browser compatibility
- [x] Custom config path specified (./tailwind.config.js)

### 2.3 shadcn/ui Component Library Status

**Components Directory:** `/services/web/src/components/ui`

**Base Components (80+):**
- [x] Accordion
- [x] Alert & Alert Dialog
- [x] Avatar & Aspect Ratio
- [x] Badge
- [x] Breadcrumb
- [x] Button
- [x] Calendar
- [x] Card
- [x] Carousel
- [x] Checkbox
- [x] Collapsible
- [x] Command (command palette)
- [x] Context Menu
- [x] Dialog & Drawer
- [x] Dropdown Menu
- [x] Form
- [x] Hover Card
- [x] Input & Input OTP
- [x] Label
- [x] Menubar
- [x] Navigation Menu
- [x] Pagination
- [x] Popover
- [x] Progress & Progress Stepper
- [x] Radio Group
- [x] Resizable
- [x] Scroll Area
- [x] Select
- [x] Separator
- [x] Sheet (side panel)
- [x] Sidebar
- [x] Skeleton
- [x] Slider
- [x] Switch
- [x] Table
- [x] Tabs
- [x] Textarea
- [x] Toast & Toaster
- [x] Toggle & Toggle Group
- [x] Tooltip

**Custom Components (ResearchFlow-specific):**
- [x] Chart (Recharts integration)
- [x] Abstract Generator
- [x] AI Approval Gate & Modal
- [x] AI Consent Modal
- [x] Attestation Modal
- [x] Artifact Comparison
- [x] Cost Usage Panel
- [x] Dataset Status Card
- [x] Fairness Metrics
- [x] Fatigue Policy Banner
- [x] IRB Panel
- [x] Journal Selector
- [x] Manuscript Workspace
- [x] PHI Gate
- [x] Pipeline Status Card
- [x] Provenance Summary
- [x] Reproducibility Export
- [x] Research Brief
- [x] SAP Builder
- [x] Stage Output Viewer
- [x] Statistical Methods
- [x] Summary Charts
- [x] System Status Card
- [x] Theme Settings
- [x] Topic Brief Panel
- [x] Topic Card Recommendations
- [x] Topic Version Badge
- [x] Topic Version Diff
- [x] Conference Readiness

---

## Section 3: Bundle Optimization & Code Splitting

### 3.1 Vendor Chunk Strategy

**Configured in:** `vite.config.ts` - `rollupOptions.output.manualChunks`

**14 Vendor Chunks (Optimal Caching):**

1. **vendor-react**
   - react, react-dom
   - wouter (routing)
   - Libraries that change together with React

2. **vendor-ui**
   - @radix-ui/* (35+ components)
   - Provides stable UI primitives

3. **vendor-query**
   - @tanstack/react-query
   - axios
   - Shared data fetching layer

4. **vendor-editor**
   - @tiptap/* and ProseMirror libraries
   - Large specialized editor dependencies

5. **vendor-charts**
   - recharts
   - Large visualization library

6. **vendor-d3** (conditional)
   - d3 utilities if included

7. **vendor-date**
   - date-fns
   - react-day-picker
   - Common stable utilities

8. **vendor-collab**
   - yjs
   - y-websocket
   - y-prosemirror
   - Collaborative editing system

9. **vendor-flow**
   - reactflow
   - Specialized diagram library

10. **vendor-forms**
    - react-hook-form
    - Form state management

11. **vendor-validation**
    - zod
    - drizzle-zod
    - Schema validation

12. **vendor-anim**
    - framer-motion
    - Animation library

13. **vendor-utils**
    - class-variance-authority
    - clsx
    - classnames
    - Utility functions

14. **vendor-lodash** (if used)
    - lodash
    - General utilities

15. **vendor-common**
    - All other third-party libraries
    - Fallback for misc dependencies

### 3.2 Asset File Naming & Caching

**JavaScript:**
- Pattern: `js/[name]-[hash].js`
- Content-based hashing for cache busting

**Images:**
- Pattern: `assets/images/[name]-[hash][extname]`
- Supported: png, jpg, jpeg, gif, svg

**Fonts:**
- Pattern: `assets/fonts/[name]-[hash][extname]`
- Supported: woff, woff2, eot, ttf, otf

**Other Assets:**
- Pattern: `assets/[name]-[hash][extname]`

### 3.3 Compression Configuration

**Gzip Compression:**
- [x] Enabled
- [x] Threshold: 10KB (only compress files > 10KB)
- [x] Creates .gz files
- [x] Keeps original files

**Brotli Compression:**
- [x] Enabled
- [x] Threshold: 10KB
- [x] Better compression ratio than gzip
- [x] Creates .br files
- [x] Keeps original files

### 3.4 Build Optimization Settings

**Minification:**
- [x] esbuild minifier
- [x] Drop console logs in production
- [x] Drop debugger statements
- [x] Pure function marking for tree-shaking

**Tree-Shaking:**
- [x] ES modules enabled
- [x] Side effect analysis
- [x] Unused code elimination

**Chunk Size Warnings:**
- [x] Warning threshold: 500KB
- [x] Reports compressed size
- [x] Dynamic import support for route splitting

---

## Section 4: Development Setup

### 4.1 Development Server Configuration

**Vite Dev Server:**
- [x] Port: 5173
- [x] HMR (Hot Module Replacement) enabled
- [x] API proxy configured:
  - /api → http://localhost:3001
  - changeOrigin: true
  - secure: false (for local development)

### 4.2 Environment Variables

**Expected Files:**
- [ ] .env.local (development overrides - not in repo)
- [ ] .env.development (development defaults)
- [ ] .env.production (production config)
- [ ] .example.env (template for developers)

**Example File:** `/services/web/.env.example`

**Common Variables to Configure:**
- VITE_API_URL (orchestrator service URL)
- VITE_WS_URL (WebSocket URL for real-time events)
- VITE_SENTRY_DSN (error tracking - optional)
- VITE_ANALYTICS_ID (analytics tracking)
- VITE_AUTH_DOMAIN (authentication provider)
- VITE_AUTH_CLIENT_ID
- VITE_APP_ENV (development|staging|production)

### 4.3 Build Commands

**Available Scripts (from package.json):**

```bash
# Development server with HMR
npm run dev

# Production build
npm run build

# Build with bundle analysis (opens stats.html)
npm run build:analyze

# Preview production build locally
npm run preview

# Lint TypeScript and TSX files
npm run lint
```

### 4.4 Code Quality Configuration

**ESLint Configuration:** `/services/web/eslint.config.js`

**Enabled Rules:**
- [x] TypeScript linting (@typescript-eslint)
- [x] Import organization (eslint-plugin-import)
- [x] React best practices (eslint-plugin-react)
- [x] React Hooks linting (eslint-plugin-react-hooks)
- [x] Unused disable directives detection
- [x] Max warnings: 0 (strict mode)

---

## Section 5: Docker & Deployment Configuration

### 5.1 Docker Configuration Status

**Files:**
- [x] `/services/web/Dockerfile` - Container image definition
- [x] `/services/web/.dockerignore` - Build context optimization
- [x] `/services/web/nginx.conf` - Web server configuration

**Nginx Configuration Includes:**
- [x] SPA routing (try_files with fallback to index.html)
- [x] API proxy to orchestrator service
- [x] Security headers:
  - X-Frame-Options: SAMEORIGIN
  - Content-Security-Policy
  - X-Content-Type-Options: nosniff
- [x] Gzip compression
- [x] Browser caching with Cache-Control headers
- [x] Brotli support for modern browsers

### 5.2 Vercel Configuration (Optional)

**File:** `/services/web/vercel.json`

**Purpose:** Configuration for Vercel deployment (if used)

### 5.3 Deployment Platforms

**Supported Platforms:**
- [x] Docker (primary - orchestrated via docker-compose)
- [x] Vercel (via vercel.json)
- [x] Any Node.js server (static SPA)

---

## Section 6: API Integration

### 6.1 API Client Setup

**Files:**
- `/services/web/src/api/client.ts` - Centralized API client
- `/services/web/src/api/insights-api.ts` - Insights-specific endpoints
- `/services/web/src/lib/api-client.ts` - API utilities

**Features:**
- [x] Axios-based HTTP client
- [x] Authentication header injection
- [x] Error handling middleware
- [x] Request/response interceptors
- [x] Base URL configuration from env

### 6.2 TanStack Query Integration

**Configuration:**
- [x] @tanstack/react-query@5.51.1 installed
- [x] Query client configured in `/services/web/src/lib/queryClient.ts`
- [x] Global error handling
- [x] Cache invalidation strategies
- [x] Stale-while-revalidate patterns

**Usage Patterns:**
- [x] useQuery for data fetching
- [x] useMutation for mutations
- [x] useInfiniteQuery for pagination
- [x] Suspense support ready

### 6.3 Real-time WebSocket Integration

**Libraries:**
- [x] y-websocket@2.1.0 (CRDT sync)
- [x] Direct WebSocket API for run events

**Features:**
- [x] Collaborative document editing
- [x] Real-time run status updates
- [x] Event subscription patterns
- [x] Automatic reconnection

---

## Section 7: Feature-Specific Checks

### 7.1 Rich Text Editor

**Technology:** ProseMirror + Yjs

**Files:**
- `/services/web/src/components/editor/` (editor components)
- `/services/web/src/components/ui/manuscript-workspace.tsx`

**Status:**
- [x] Rich text editing with formatting
- [x] Collaborative editing support
- [x] Auto-save capability
- [x] Version history

### 7.2 Insights Dashboard

**Components:**
- `/services/web/src/components/insights/` (insight visualizations)
- `/services/web/src/api/insights-api.ts` (API client)

**Status:**
- [x] Real-time data visualization
- [x] WebSocket-connected streams
- [x] Metric charts (Recharts)
- [x] Event timeline display
- [x] Alert system

### 7.3 Governance & Compliance

**Components:**
- `/services/web/src/pages/governance-console.tsx`
- `/services/web/src/pages/governance.tsx`
- `/services/web/src/components/governance/` (governance UI)

**Features:**
- [x] Approval workflow UI
- [x] Audit log viewer
- [x] Access control display
- [x] Compliance status tracking
- [x] AI activity panel

### 7.4 Manuscript System

**Components:**
- `/services/web/src/pages/manuscript-editor.tsx`
- `/services/web/src/components/ui/manuscript-workspace.tsx`

**Features:**
- [x] IRB form (6-tab interface)
- [x] Lay summary editor with validation
- [x] AI/ML disclosure
- [x] Multi-institutional templates
- [x] Progress tracking (0-100%)
- [x] Auto-save with debouncing

### 7.5 Workflow Builder

**Components:**
- `/services/web/src/pages/workflow-builder.tsx`
- `/services/web/src/pages/workflow.tsx`
- `/services/web/src/workflow/` (workflow logic)

**Features:**
- [x] Visual workflow stage builder
- [x] Drag-and-drop interface
- [x] Stage configuration
- [x] 20-stage research pipeline
- [x] Input/output mapping

### 7.6 Search Functionality

**Files:**
- `/services/web/src/pages/search.tsx`
- `/services/web/src/components/search/`
- `/services/web/src/api/search.ts`

**Status:**
- [x] Full-text search
- [x] Faceted filtering
- [x] Real-time results
- [x] Result previews

---

## Section 8: Security Checklist

### 8.1 Build-Time Security

- [x] Source maps disabled in production (vite.config.ts)
- [x] Console logs stripped in production
- [x] Debugger statements removed
- [x] Environment variables isolated (no secrets in code)

### 8.2 CSP & Headers

**Configured in:** `/services/web/nginx.conf`

- [x] Content-Security-Policy header
- [x] X-Frame-Options: SAMEORIGIN
- [x] X-Content-Type-Options: nosniff
- [x] Referrer-Policy configured

### 8.3 Data Validation

- [x] Zod schema validation for all API data
- [x] Form validation with react-hook-form
- [x] Type-safe API responses (TypeScript)

### 8.4 Authentication

- [x] Auth context setup (`/services/web/src/contexts/AuthContext.tsx`)
- [x] Protected routes support
- [x] Token refresh logic
- [x] Logout handling

### 8.5 PHI Protection

**Features:**
- [x] PHI gate components (`/services/web/src/components/ui/phi-gate.tsx`)
- [x] PHI indicator in mode banner
- [x] Data masking support
- [x] Audit logging for access

---

## Section 9: Performance Checklist

### 9.1 Code Splitting

- [x] Route-based code splitting ready
- [x] Dynamic imports configured
- [x] 14+ vendor chunks for granular caching
- [x] CSS code splitting enabled

### 9.2 Image Optimization

**Library:** Custom implementation in `/services/web/src/lib/image-optimization.ts`

- [x] Lazy loading support
- [x] WebP format support
- [x] Responsive image sizing
- [x] Format negotiation

### 9.3 Bundle Size Management

**Current Strategy:**
- [x] Gzip compression (10KB threshold)
- [x] Brotli compression (10KB threshold)
- [x] Tree-shaking enabled
- [x] Minification aggressive
- [x] Chunk size warnings at 500KB
- [x] Bundle analyzer included (npm run build:analyze)

### 9.4 Rendering Performance

- [x] Concurrent React features available
- [x] Suspense support configured
- [x] Error boundaries in place
- [x] Memo and lazy optimizations available

### 9.5 Query Performance

- [x] TanStack Query caching
- [x] Stale-while-revalidate patterns
- [x] Request deduplication
- [x] Background refetch strategies

---

## Section 10: Testing Readiness

### 10.1 Test File Patterns

**Excluded from TypeScript compilation:**
- **/*.test.ts
- **/*.test.tsx
- **/*.spec.ts
- **/*.spec.tsx

**Recommended Testing Setup:**
- [ ] Jest configuration (if not present)
- [ ] React Testing Library setup
- [ ] Test utilities for hooks, components
- [ ] Snapshot testing where appropriate
- [ ] E2E tests (Cypress or Playwright)

### 10.2 Component Testing

**Testable Components:**
- [ ] shadcn/ui components (behavior + styling)
- [ ] Custom ResearchFlow components
- [ ] API client error handling
- [ ] Form validation
- [ ] Navigation routing

---

## Section 11: Accessibility (a11y) Checklist

### 11.1 Semantic HTML

- [x] Radix UI components provide semantic HTML
- [x] ARIA attributes configured in Radix
- [x] Form labels properly associated
- [x] Heading hierarchy maintained

### 11.2 Keyboard Navigation

- [x] Tab order in components
- [x] Focus management (Dialog, etc.)
- [x] Command palette (⌘K) for keyboard power users
- [x] Keyboard shortcuts defined

### 11.3 Screen Reader Support

- [x] ARIA labels in Radix components
- [x] Alternative text for images
- [x] Status announcements (Toast, etc.)
- [x] Live regions for dynamic updates

### 11.4 Visual Accessibility

- [x] Color contrast ratios (WCAG AA standard)
- [x] Font sizing accessible
- [x] High contrast mode support
- [x] Dark mode support

---

## Section 12: Internationalization (i18n)

### 12.1 i18next Configuration

**Files:**
- `/services/web/src/i18n/index.ts` - Configuration
- `/services/web/src/i18n/locales/` - Translation files

**Features:**
- [x] i18next@23.11.5 installed
- [x] react-i18next@14.1.2 installed
- [x] Language auto-detection enabled
- [x] Browser language detection support
- [x] Translation key structure ready

**Supported Features:**
- [x] Multiple language support
- [x] Language switching
- [x] Translation fallbacks
- [x] Lazy loading of language files

---

## Section 13: Monitoring & Analytics

### 13.1 Error Tracking

**Library:** Sentry (optional, configured in vite.config.ts)

- [ ] VITE_SENTRY_DSN environment variable
- [ ] Error capture configured
- [ ] Source map upload (if enabled)
- [ ] User context tracking

**Files:**
- `/services/web/src/lib/sentry.ts` (error tracking setup)

### 13.2 Analytics

**Configuration:**
- [ ] VITE_ANALYTICS_ID environment variable
- [ ] Page view tracking
- [ ] Event tracking
- [ ] User session tracking

**Files:**
- `/services/web/src/lib/analytics.ts` (analytics client)

### 13.3 Consent Management

**Features:**
- [x] Analytics consent banner component
- [x] Consent store with Zustand
- [x] Cookie banner support
- [ ] GDPR/CCPA compliance

**Components:**
- `/services/web/src/components/AnalyticsConsentBanner.tsx`

---

## Section 14: Deployment Checklist

### 14.1 Pre-Deployment Verification

- [ ] All environment variables configured
- [ ] API endpoints correct for target environment
- [ ] WebSocket URL configured
- [ ] Build completes without errors
- [ ] Bundle analysis reviewed (npm run build:analyze)
- [ ] No console errors or warnings
- [ ] Performance benchmarks acceptable

### 14.2 Build Process

```bash
# Step 1: Install dependencies
npm ci  # Preferred over npm install in CI

# Step 2: Lint code
npm run lint

# Step 3: Build for production
NODE_ENV=production npm run build

# Step 4: Verify build output
ls -lh dist/
# Should see:
# - js/ (app chunks)
# - assets/ (images, fonts)
# - *.html (including stats.html from visualizer)
# - .gz and .br files (compressed variants)
```

### 14.3 Docker Deployment

**Build Docker Image:**
```bash
cd services/web
docker build -t researchflow-web:latest .
docker tag researchflow-web:latest researchflow-web:1.0.0
```

**Push to Registry:**
```bash
docker push researchflow-web:latest
docker push researchflow-web:1.0.0
```

**Run Container:**
```bash
docker run -p 80:80 \
  -e ORCHESTRATOR_URL=http://orchestrator:3001 \
  -e WS_URL=ws://orchestrator:3001 \
  researchflow-web:latest
```

### 14.4 Nginx Configuration Verification

**Check Points:**
- [x] SPA routing (try_files configured)
- [x] API proxy (/api routes)
- [x] Compression enabled (gzip, brotli)
- [x] Security headers set
- [x] Cache-Control headers configured
- [x] CORS headers if needed

### 14.5 Health Checks

**URL Endpoints to Verify:**
- [ ] GET / (index.html loads, JavaScript executes)
- [ ] GET /api (proxied to orchestrator)
- [ ] WebSocket upgrade (ws:// protocol)
- [ ] Asset serving (css, js, fonts, images)
- [ ] 404 handling (returns index.html for SPA)

### 14.6 Post-Deployment Validation

- [ ] Website loads without errors
- [ ] JavaScript bundles download and execute
- [ ] API calls work (check Network tab)
- [ ] WebSocket connections establish
- [ ] Real-time features work (insights, notifications)
- [ ] Authentication flows work
- [ ] Form submissions work
- [ ] File uploads work
- [ ] Mobile responsiveness verified
- [ ] Dark mode toggle works
- [ ] Command palette (⌘K) works
- [ ] Search functionality works
- [ ] Navigation between pages works

---

## Section 15: Troubleshooting Guide

### Common Build Issues

**Issue:** TypeScript compilation errors
```bash
# Solution: Check tsconfig.json and specific file issues
npm run lint
# Fix errors reported
npm run build
```

**Issue:** Module not found errors
```bash
# Solution: Verify path aliases in tsconfig.json and vite.config.ts
# Check import paths use @ or @packages/ correctly
grep -r "import.*from" src/ | grep -v node_modules | head -20
```

**Issue:** Chunk size exceeds warning threshold
```bash
# Solution: Analyze bundle
npm run build:analyze
# Open dist/stats.html in browser
# Identify large libraries, consider code splitting
```

**Issue:** Slow build times
```bash
# Solution: Check for plugins in vite.config.ts
# Disable compression plugins during development:
NODE_ENV=development npm run dev
```

### Common Runtime Issues

**Issue:** API calls fail with CORS errors
```
Solution: Verify orchestrator service is running
Check VITE_API_URL environment variable
Review nginx proxy configuration
```

**Issue:** WebSocket connections fail
```
Solution: Verify WS_URL environment variable points to correct orchestrator
Check firewall allows WebSocket upgrade
Review browser console for connection logs
```

**Issue:** Components don't render (white screen)
```
Solution: Check browser console for errors
Verify React suspense boundaries
Check authentication status
Review Network tab for failed requests
```

---

## Section 16: Maintenance & Updates

### 16.1 Dependency Management

**Regular Tasks:**
- [ ] Run `npm audit` monthly to check for vulnerabilities
- [ ] Update dependencies quarterly: `npm update`
- [ ] Check for breaking changes in major releases
- [ ] Test updates in development before production

**Critical Dependencies to Monitor:**
- React (framework)
- Vite (build tool)
- TypeScript (type checking)
- TanStack Query (data fetching)
- Radix UI (component primitives)

### 16.2 Performance Monitoring

**Metrics to Track:**
- [ ] Page load time (Largest Contentful Paint)
- [ ] Time to Interactive (TTI)
- [ ] Core Web Vitals (CLS, FID, LCP)
- [ ] Bundle size trends
- [ ] API response times

### 16.3 Error Tracking

- [ ] Set up Sentry or similar service
- [ ] Monitor error rates by page
- [ ] Track user-reported issues
- [ ] Set up alerts for error spikes

---

## Deployment Readiness Summary

| Category | Status | Notes |
|----------|--------|-------|
| **Vite Config** | ✅ Ready | Production optimizations configured |
| **TypeScript** | ✅ Ready | Strict mode pragmatic, path aliases set |
| **Dependencies** | ✅ Ready | All major dependencies installed |
| **Tailwind CSS** | ✅ Ready | Design system tokens defined |
| **shadcn/ui** | ✅ Ready | 80+ components configured |
| **Bundle Strategy** | ✅ Ready | 14+ vendor chunks for caching |
| **Compression** | ✅ Ready | Gzip + Brotli configured |
| **Docker** | ✅ Ready | Dockerfile + Nginx config present |
| **API Integration** | ✅ Ready | Axios + TanStack Query ready |
| **Real-time** | ✅ Ready | WebSocket + Yjs configured |
| **Security** | ✅ Ready | Source maps disabled, headers set |
| **Performance** | ✅ Ready | Code splitting, lazy loading enabled |
| **Accessibility** | ✅ Ready | Radix UI provides ARIA support |
| **i18n** | ✅ Ready | i18next configured |
| **Testing** | ⚠️ Needs Setup | Test framework and tests needed |
| **E2E Tests** | ⚠️ Needs Setup | Cypress/Playwright configuration needed |
| **Error Tracking** | ⚠️ Optional | Sentry optional, configure if needed |
| **Analytics** | ⚠️ Optional | Analytics optional, configure if needed |

---

## Final Pre-Deployment Steps

```bash
# 1. Install dependencies
npm ci

# 2. Run linter
npm run lint

# 3. Build for production
npm run build

# 4. Analyze bundle (optional but recommended)
npm run build:analyze

# 5. Preview production build locally
npm run preview

# 6. Visit http://localhost:4173 and verify:
#    - Page loads without errors
#    - All major features work
#    - Console is clean (no errors/warnings)

# 7. Build Docker image
docker build -t researchflow-web:$(date +%Y%m%d-%H%M%S) .

# 8. Run container and test
docker run -p 8080:80 -e ORCHESTRATOR_URL=http://host.docker.internal:3001 researchflow-web:latest

# 9. Visit http://localhost:8080 and verify
```

---

**Document Version:** 1.0  
**Last Updated:** January 29, 2026  
**Created By:** ResearchFlow Track 3A - React Web Application Analysis  
**Status:** Ready for Production Deployment
