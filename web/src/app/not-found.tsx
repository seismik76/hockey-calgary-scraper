'use client';

import { Body1, Button, LargeTitle, makeStyles, tokens } from '@fluentui/react-components';
import Link from 'next/link';

const useStyles = makeStyles({
  wrap: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    padding: tokens.spacingHorizontalXXL,
    backgroundColor: tokens.colorNeutralBackground2,
  },
  card: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    boxShadow: tokens.shadow8,
    padding: `${tokens.spacingVerticalXXL} ${tokens.spacingHorizontalXXL}`,
    maxWidth: '480px',
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalL,
    textAlign: 'center',
  },
  glyph: {
    fontSize: '48px',
    fontWeight: tokens.fontWeightBold,
    color: tokens.colorBrandForeground1,
    letterSpacing: '-0.04em',
  },
  message: {
    color: tokens.colorNeutralForeground2,
  },
  actions: {
    display: 'flex',
    gap: tokens.spacingHorizontalM,
    justifyContent: 'center',
  },
});

export default function NotFound() {
  const s = useStyles();
  return (
    <div className={s.wrap}>
      <div className={s.card}>
        <div className={s.glyph}>404</div>
        <LargeTitle as="h1">Page not found</LargeTitle>
        <Body1 className={s.message}>
          That route doesn&apos;t exist. The app has two pages — Analytics and Tier 1
          Dilution.
        </Body1>
        <div className={s.actions}>
          <Link href="/">
            <Button appearance="primary">Analytics</Button>
          </Link>
          <Link href="/dilution">
            <Button appearance="secondary">Tier 1 Dilution</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
