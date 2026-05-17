'use client';

import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Badge,
  Body1Strong,
  Button,
  Combobox,
  Dropdown,
  Field,
  Option,
  Radio,
  RadioGroup,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import {
  ArrowResetRegular,
  CalendarLtr20Regular,
  Filter20Regular,
  Home20Regular,
  Search20Regular,
} from '@fluentui/react-icons';
import {
  filterByDivision,
  type Division,
} from '@/lib/analytics/communities';
import { type TierLabel } from '@/lib/analytics/tiering';

// -----------------------------------------------------------------------------
// Generic filter shell shared by /analytics and /dilution. Each consumer holds
// its own state and adapts to the grouped-props API below — no shared state
// type, so the two pages can keep their own metric label enums.
// -----------------------------------------------------------------------------

export type FieldGroup<T extends string> = {
  values: T[];
  options: readonly T[];
  onChange: (next: T[]) => void;
};

export type MetricGroup = {
  /** Display label above the dropdown. Defaults to "Metric". */
  label?: string;
  value: string;
  options: readonly string[];
  onChange: (next: string) => void;
};

export type FilterShellProps = {
  metric: MetricGroup;
  seasons: FieldGroup<string>;
  types: FieldGroup<string>;
  ages: FieldGroup<string>;
  tiers: FieldGroup<TierLabel>;
  division: {
    value: Division;
    onChange: (next: Division) => void;
    /** Full list of communities — used to recompute the community selection
     *  when division changes (so the user doesn't end up with N selected
     *  communities that are no longer in the visible pool). */
    allCommunities: readonly string[];
  };
  communities: FieldGroup<string>;
  /** When provided, a third "Refine" accordion section appears with these
   *  filters. Pages that don't use it (e.g. dilution) just omit it. */
  refine?: {
    leagues: FieldGroup<string>;
    teams: FieldGroup<string>;
  };
  /** Number of filters that differ from the page's defaults. Drives the
   *  inline count badge + visibility of the Reset button. */
  activeCount: number;
  onReset: () => void;
};

const useStyles = makeStyles({
  aside: {
    background: `linear-gradient(180deg, ${tokens.colorNeutralBackground3} 0%, ${tokens.colorNeutralBackground2} 100%)`,
    borderRight: `1px solid ${tokens.colorNeutralStroke2}`,
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalM}`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
    overflowY: 'auto',
    height: '100%',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: tokens.spacingHorizontalS,
    paddingBottom: tokens.spacingVerticalXS,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalXS,
    color: tokens.colorNeutralForeground2,
  },
  countBadge: {
    fontVariantNumeric: 'tabular-nums',
  },
  metricRow: {
    paddingTop: tokens.spacingVerticalXS,
    paddingBottom: tokens.spacingVerticalS,
  },
  hairline: {
    height: '1px',
    backgroundColor: tokens.colorNeutralStroke2,
    flexShrink: 0,
  },
  accordionHeader: {
    fontWeight: tokens.fontWeightSemibold,
  },
  panel: {
    paddingTop: tokens.spacingVerticalXS,
    paddingBottom: tokens.spacingVerticalS,
    paddingLeft: 0,
    paddingRight: 0,
  },
  group: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
  },
});

function ComboMulti<T extends string>({
  label,
  group,
  placeholder,
}: {
  label: string;
  group: FieldGroup<T>;
  placeholder?: string;
}) {
  const { values, options, onChange } = group;
  return (
    <Field label={label}>
      <Combobox
        size="small"
        multiselect
        selectedOptions={values}
        value={
          values.length === 0
            ? ''
            : values.length === 1
              ? values[0]
              : `${values.length} selected`
        }
        onOptionSelect={(_, data) =>
          onChange(data.selectedOptions as T[])
        }
        placeholder={placeholder ?? `Select ${label.toLowerCase()}`}
      >
        {options.map((o) => (
          <Option key={o} value={o}>
            {o}
          </Option>
        ))}
      </Combobox>
    </Field>
  );
}

function ScopeSection({
  ages,
  tiers,
  division,
  communities,
}: Pick<FilterShellProps, 'ages' | 'tiers' | 'division' | 'communities'>) {
  const visibleCommunities = filterByDivision(
    [...division.allCommunities],
    division.value,
  );
  return (
    <>
      <ComboMulti label="Age category" group={ages} />
      <ComboMulti label="Tier" group={tiers} />
      <Field label="Hockey Calgary division">
        <RadioGroup
          layout="horizontal"
          value={division.value}
          onChange={(_, data) => {
            const next = data.value as Division;
            const allCs = [...division.allCommunities];
            const nextVisible = filterByDivision(allCs, next);
            // If user has the full default set selected (all communities), or
            // narrowing the division would leave zero matches, snap to the new
            // division's complete list. Otherwise intersect their current
            // selection with the new visible set.
            const intersected = nextVisible.filter((c) =>
              communities.values.includes(c),
            );
            communities.onChange(
              communities.values.length === allCs.length || intersected.length === 0
                ? nextVisible
                : intersected,
            );
            division.onChange(next);
          }}
        >
          <Radio value="All" label="All" />
          <Radio value="North" label="North" />
          <Radio value="South" label="South" />
        </RadioGroup>
      </Field>
      <ComboMulti
        label="Communities"
        group={{
          ...communities,
          options: visibleCommunities,
        }}
      />
    </>
  );
}

export function FilterShell(props: FilterShellProps) {
  const s = useStyles();
  const { metric, seasons, types, ages, tiers, division, communities, refine, activeCount, onReset } = props;

  return (
    <aside className={s.aside}>
      <div className={s.header}>
        <div className={s.headerLeft}>
          <Filter20Regular />
          <Body1Strong>Filters</Body1Strong>
          {activeCount > 0 && (
            <Badge appearance="filled" color="brand" size="small" className={s.countBadge}>
              {activeCount}
            </Badge>
          )}
        </div>
        {activeCount > 0 && (
          <Button
            appearance="subtle"
            size="small"
            icon={<ArrowResetRegular />}
            onClick={onReset}
            title="Reset all filters to defaults"
          >
            Reset
          </Button>
        )}
      </div>

      <div className={s.metricRow}>
        <Field label={metric.label ?? 'Metric'}>
          <Dropdown
            size="small"
            value={metric.value}
            selectedOptions={[metric.value]}
            onOptionSelect={(_, data) => {
              if (data.optionValue) metric.onChange(data.optionValue);
            }}
          >
            {metric.options.map((m) => (
              <Option key={m} value={m}>
                {m}
              </Option>
            ))}
          </Dropdown>
        </Field>
      </div>

      <div className={s.hairline} />

      <Accordion multiple collapsible defaultOpenItems={['time', 'scope']}>
        <AccordionItem value="time">
          <AccordionHeader
            expandIconPosition="end"
            icon={<CalendarLtr20Regular />}
            className={s.accordionHeader}
            size="small"
          >
            Time
          </AccordionHeader>
          <AccordionPanel className={s.panel}>
            <div className={s.group}>
              <ComboMulti label="Seasons" group={seasons} />
              <ComboMulti label="Season type" group={types} />
            </div>
          </AccordionPanel>
        </AccordionItem>

        <AccordionItem value="scope">
          <AccordionHeader
            expandIconPosition="end"
            icon={<Home20Regular />}
            className={s.accordionHeader}
            size="small"
          >
            Scope
          </AccordionHeader>
          <AccordionPanel className={s.panel}>
            <div className={s.group}>
              <ScopeSection
                ages={ages}
                tiers={tiers}
                division={division}
                communities={communities}
              />
            </div>
          </AccordionPanel>
        </AccordionItem>

        {refine && (
          <AccordionItem value="refine">
            <AccordionHeader
              expandIconPosition="end"
              icon={<Search20Regular />}
              className={s.accordionHeader}
              size="small"
            >
              Refine
            </AccordionHeader>
            <AccordionPanel className={s.panel}>
              <div className={s.group}>
                <ComboMulti label="Leagues" group={refine.leagues} />
                <ComboMulti label="Teams" group={refine.teams} />
              </div>
            </AccordionPanel>
          </AccordionItem>
        )}
      </Accordion>
    </aside>
  );
}

