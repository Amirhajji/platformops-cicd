import { useCallback, useEffect, useState } from 'react'

export interface Load<T> {
  data?: T
  error?: string
  loading: boolean
  reload: () => void
}

/** Loads data when `deps` change. While it reloads, the previous data stays visible. */
export function useLoad<T>(
  load: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): Load<T> {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({
    loading: true,
  })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setState((previous) => ({ data: previous.data, loading: true }))
    load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ data, loading: false })
      },
      (error: unknown) => {
        if (controller.signal.aborted) return
        setState({
          error: error instanceof Error ? error.message : 'Unexpected error',
          loading: false,
        })
      },
    )
    return () => controller.abort()
    // `load` is a new function on every render: `deps` says when it really changes.
  }, [...deps, version])

  const reload = useCallback(() => setVersion((value) => value + 1), [])
  return { ...state, reload }
}
