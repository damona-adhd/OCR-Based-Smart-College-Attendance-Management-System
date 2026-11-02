import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { reportsApi } from '../../api/reports'

export default function SettingsPage() {
  const qc = useQueryClient()
  const { data: settings = [], isLoading } = useQuery({ queryKey: ['settings'], queryFn: reportsApi.getSettings })
  const [values, setValues] = useState<Record<string, string>>({})

  const updateMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => reportsApi.updateSetting(key, value),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['settings'] }); toast.success('Setting updated') },
    onError: () => toast.error('Failed to update'),
  })

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>

  return (
    <div>
      <PageHeader title="Application Settings" subtitle="Configure system-wide defaults" />

      <div className="card max-w-2xl space-y-6">
        {settings.map((s: any) => {
          const val = values[s.key] ?? s.value
          return (
            <div key={s.key}>
              <label className="label">{s.key.replace(/_/g, ' ')}</label>
              {s.description && <p className="text-xs text-gray-400 mb-1">{s.description}</p>}
              <div className="flex gap-3">
                <input
                  className="input flex-1"
                  value={val}
                  onChange={e => setValues(v => ({ ...v, [s.key]: e.target.value }))}
                />
                <button
                  className="btn-primary shrink-0"
                  onClick={() => updateMut.mutate({ key: s.key, value: val })}
                >Save</button>
              </div>
            </div>
          )
        })}

        {settings.length === 0 && (
          <p className="text-sm text-gray-500">No settings configured. Default values are in use.</p>
        )}
      </div>
    </div>
  )
}
