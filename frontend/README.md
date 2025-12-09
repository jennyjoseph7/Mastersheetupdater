# Frontend - AutoBot Agents

A modern Next.js frontend application built with React, TypeScript, and Tailwind CSS. This project uses **Bun** as the package manager and runtime for optimal performance.

## Prerequisites

- **Bun** (v1.0 or later) - [Install Bun](https://bun.sh)
- **Node.js** (v18 or later) - for compatibility

## Quick Start

### 1. Install Dependencies

```bash
bun install
```

### 2. Start Development Server

```bash
bun run dev
```

The application will be available at `http://localhost:3000`

## Available Scripts

### Development

```bash
# Start development server with hot reload
bun run dev
```

### Production Build

```bash
# Build the project for production
bun run build

# Start production server
bun run start
```

### Linting

```bash
# Run ESLint
bun run lint
```

## Project Structure

```
frontend/
├── app/                    # Next.js app directory (pages and layouts)
├── components/            # Reusable React components
├── hooks/                 # Custom React hooks
├── lib/                   # Utility functions and helpers
├── styles/                # Global styles and CSS modules
├── types/                 # TypeScript type definitions
├── utils/                 # Utility functions
├── public/                # Static assets
├── package.json          # Dependencies and scripts
└── tsconfig.json         # TypeScript configuration
```

## Key Dependencies

- **Next.js 14+** - React framework for production
- **React 18+** - UI library
- **TypeScript** - Static typing
- **Tailwind CSS** - Utility-first CSS framework
- **Radix UI** - Accessible component library
- **React Hook Form** - Efficient form handling
- **TanStack Table** - Powerful data tables
- **Framer Motion** - Animation library
- **D3** - Data visualization

## Environment Setup

Create a `.env.local` file in the frontend directory for environment variables:

```bash
# Example .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Building and Deployment

### Development Mode

```bash
bun run dev
```

### Production Build

```bash
bun run build
bun run start
```

### Using Bun Runtime

Bun can also be used to run the production server directly:

```bash
# Build first
bun run build

# Run with Bun
bun start
```

## Troubleshooting

### Clear Cache and Reinstall

```bash
# Remove dependencies and lock file
rm -rf node_modules bun.lockb

# Reinstall with Bun
bun install
```

### Port Already in Use

If port 3000 is already in use, you can specify a different port:

```bash
bun run dev -- -p 3001
```

### Module Resolution Issues

Ensure `tsconfig.json` is properly configured and run:

```bash
bun install
```

## Performance Tips

- **Bun is fast**: Use Bun for quicker builds and dependency installation
- **Tree-shaking**: Unused code is automatically removed in production builds
- **Image Optimization**: Next.js automatically optimizes images
- **Code Splitting**: Automatic route-based code splitting

## Contributing

When making changes to the frontend:

1. Create a new branch
2. Make your changes
3. Run `bun run lint` to ensure code quality
4. Test locally with `bun run dev`
5. Build for production with `bun run build`

## Documentation

- [Next.js Documentation](https://nextjs.org/docs)
- [Bun Documentation](https://bun.sh/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Radix UI Documentation](https://www.radix-ui.com/docs/primitives/overview/introduction)

## License

Private Project
