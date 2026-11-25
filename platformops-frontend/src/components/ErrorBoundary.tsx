import { Component } from 'react'
import type { ReactNode } from 'react'
import { ErrorBox } from './States'

/** A rendering error shows a message instead of a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <ErrorBox
        message="This page could not be displayed."
        onRetry={() => this.setState({ failed: false })}
      />
    )
  }
}
