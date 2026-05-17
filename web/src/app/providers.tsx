'use client';

import { useState } from 'react';
import { useServerInsertedHTML } from 'next/navigation';
import {
  FluentProvider,
  RendererProvider,
  SSRProvider,
  createDOMRenderer,
  renderToStyleElements,
  webLightTheme,
  type Theme,
} from '@fluentui/react-components';

const fontStack =
  'var(--font-inter), -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", system-ui, sans-serif';
const monoStack = 'var(--font-jetbrains-mono), ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace';

const appTheme: Theme = {
  ...webLightTheme,
  fontFamilyBase: fontStack,
  fontFamilyMonospace: monoStack,
  fontFamilyNumeric: fontStack,
};

export function Providers({ children }: { children: React.ReactNode }) {
  const [renderer] = useState(() => createDOMRenderer());

  useServerInsertedHTML(() => <>{renderToStyleElements(renderer)}</>);

  return (
    <RendererProvider renderer={renderer}>
      <SSRProvider>
        <FluentProvider theme={appTheme}>{children}</FluentProvider>
      </SSRProvider>
    </RendererProvider>
  );
}
