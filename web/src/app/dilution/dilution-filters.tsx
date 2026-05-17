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
} from '@fluentui/react-icons';
import {
  filterByDivision,
  type Division,
} from '@/lib/analytics/communities';
import {
  DILUTION_METRIC_LABELS,
  type DilutionFilterState,
  type DilutionMetricLabel,
} from '@/lib/analytics/dilution';
import { type TierLabel } from '@/lib/analytics/tiering';

type Props = {
  state: DilutionFilterState;
  setState: (next: DilutionFilterState) => void;
  defaultState: DilutionFilterState;
  stickyTop?: number;
  allSeasons: string[];
  allTypes: string[];
  allAges: string[];
  allTiers: TierLabel[];
  allCommunities: string[];
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
    position: 'sticky',
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

function ComboMulti({
  label,
  values,
  options,
  onChange,
  placeholder,
}: {
  label: string;
  values: string[];
  options: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}) {
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
        onOptionSelect={(_, data) => onChange(data.selectedOptions)}
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

function countActiveFilters(
  state: DilutionFilterState,
  defaults: DilutionFilterState,
): number {
  let c = 0;
  const same = (a: unknown[], b: unknown[]) =>
    a.length === b.length && a.every((x, i) => x === b[i]);
  if (state.metric !== defaults.metric) c += 1;
  if (!same(state.seasons, defaults.seasons)) c += 1;
  if (!same(state.types, defaults.types)) c += 1;
  if (!same(state.ages, defaults.ages)) c += 1;
  if (!same(state.tiers, defaults.tiers)) c += 1;
  if (state.division !== defaults.division) c += 1;
  if (!same(state.communities, defaults.communities)) c += 1;
  return c;
}

export function DilutionFilters({
  state,
  setState,
  defaultState,
  stickyTop = 0,
  allSeasons,
  allTypes,
  allAges,
  allTiers,
  allCommunities,
}: Props) {
  const s = useStyles();
  const asideStyle = {
    top: stickyTop,
    height: `calc(100vh - ${stickyTop}px)`,
  };
  const update = <K extends keyof DilutionFilterState>(
    key: K,
    value: DilutionFilterState[K],
  ) => setState({ ...state, [key]: value });

  const communityOptions = filterByDivision(allCommunities, state.division);
  const activeCount = countActiveFilters(state, defaultState);

  return (
    <aside className={s.aside} style={asideStyle}>
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
            onClick={() => setState(defaultState)}
            title="Reset all filters to defaults"
          >
            Reset
          </Button>
        )}
      </div>

      <div className={s.metricRow}>
        <Field label="Performance metric">
          <Dropdown
            size="small"
            value={state.metric}
            selectedOptions={[state.metric]}
            onOptionSelect={(_, data) => {
              if (data.optionValue)
                update('metric', data.optionValue as DilutionMetricLabel);
            }}
          >
            {DILUTION_METRIC_LABELS.map((m) => (
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
              <ComboMulti
                label="Seasons"
                values={state.seasons}
                options={allSeasons}
                onChange={(v) => update('seasons', v)}
              />
              <ComboMulti
                label="Season type"
                values={state.types}
                options={allTypes}
                onChange={(v) => update('types', v)}
              />
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
              <ComboMulti
                label="Age category"
                values={state.ages}
                options={allAges}
                onChange={(v) => update('ages', v)}
              />
              <ComboMulti
                label="Tier"
                values={state.tiers}
                options={allTiers}
                onChange={(v) => update('tiers', v as TierLabel[])}
              />
              <Field label="Hockey Calgary division">
                <RadioGroup
                  layout="horizontal"
                  value={state.division}
                  onChange={(_, data) => {
                    const div = data.value as Division;
                    const nextCommunities = filterByDivision(allCommunities, div).filter((c) =>
                      state.communities.includes(c),
                    );
                    setState({
                      ...state,
                      division: div,
                      communities:
                        state.communities.length === allCommunities.length ||
                        nextCommunities.length === 0
                          ? filterByDivision(allCommunities, div)
                          : nextCommunities,
                    });
                  }}
                >
                  <Radio value="All" label="All" />
                  <Radio value="North" label="North" />
                  <Radio value="South" label="South" />
                </RadioGroup>
              </Field>
              <ComboMulti
                label="Communities"
                values={state.communities}
                options={communityOptions}
                onChange={(v) => update('communities', v)}
              />
            </div>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>
    </aside>
  );
}
