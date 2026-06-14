import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--bg-canvas)',
        elevated: 'var(--bg-elevated)',
        overlay: 'var(--bg-overlay)',
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          dim: 'var(--accent-dim)',
        },
        text: {
          primary: 'var(--text-primary)',
          muted: 'var(--text-muted)',
          subtle: 'var(--text-subtle)',
        },
        divider: 'var(--divider)',
        'focus-ring': 'var(--focus-ring)',
      },
      spacing: {
        1: 'var(--space-1)',
        2: 'var(--space-2)',
        3: 'var(--space-3)',
        4: 'var(--space-4)',
        5: 'var(--space-5)',
        6: 'var(--space-6)',
        7: 'var(--space-7)',
        8: 'var(--space-8)',
        9: 'var(--space-9)',
        10: 'var(--space-10)',
      },
      maxWidth: {
        prose: 'var(--width-prose)',
        content: 'var(--width-content)',
        wide: 'var(--width-wide)',
        edge: 'var(--width-edge)',
      },
      fontFamily: {
        display: 'var(--font-display)',
        body: 'var(--font-body)',
      },
      fontSize: {
        'display-xl': ['2.75rem', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        'display-lg': ['2.25rem', { lineHeight: '1.1', letterSpacing: '-0.015em' }],
        'display-md': ['1.75rem', { lineHeight: '1.15', letterSpacing: '-0.01em' }],
        'title-lg': ['1.375rem', { lineHeight: '1.3' }],
        'title-md': ['1.125rem', { lineHeight: '1.35' }],
        'body-lg': ['1.0625rem', { lineHeight: '1.6' }],
        'body-md': ['1rem', { lineHeight: '1.6' }],
        'body-sm': ['0.875rem', { lineHeight: '1.55' }],
        label: ['0.75rem', { lineHeight: '1.4', letterSpacing: '0.15em' }],
        'label-sm': ['0.6875rem', { lineHeight: '1.4', letterSpacing: '0.18em' }],
      },
      borderRadius: {
        none: '0',
        sm: '2px',
        md: '4px',
        full: '9999px',
      },
      transitionDuration: {
        fast: '120ms',
        base: '200ms',
        slow: '360ms',
        glacial: '600ms',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
        entry: 'cubic-bezier(0.16, 1, 0.3, 1)',
        exit: 'cubic-bezier(0.4, 0, 1, 1)',
      },
    },
  },
  plugins: [],
};

export default config;
