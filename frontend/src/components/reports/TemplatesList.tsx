import { TemplateCard } from './TemplateCard'
import type { TemplateItem } from '@/mocks/reportsData'

interface TemplatesListProps {
  templates: TemplateItem[]
  onGenerate: (type: 'flash' | 'period' | 'board') => void
}

export function TemplatesList({ templates, onGenerate }: TemplatesListProps) {
  return (
    <div className="space-y-2.5">
      {templates.map((t) => (
        <TemplateCard key={t.id} template={t} onGenerate={() => onGenerate(t.previewType)} />
      ))}
    </div>
  )
}
