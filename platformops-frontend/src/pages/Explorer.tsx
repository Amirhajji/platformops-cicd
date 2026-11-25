import { MetricChart, MetricPicker, useSelectedMetrics } from '../components/Metrics'
import { Card, PageTitle } from '../components/States'

const NONE: number[] = []

export function Explorer() {
  const { ids, toggle, clear } = useSelectedMetrics(NONE)
  return (
    <>
      <PageTitle title="Metric explorer" />
      <MetricChart ids={ids} onRemove={toggle} onClear={clear} />
      <Card title="Catalog">
        <MetricPicker ids={ids} onToggle={toggle} />
      </Card>
    </>
  )
}
