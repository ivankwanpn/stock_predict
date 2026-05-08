import { describe, expect, test } from 'vitest'
import React from 'react'

describe('vitest smoke test', () => {
  test('basic assertions work', () => {
    expect(1 + 1).toBe(2)
  })

  test('React is importable', () => {
    expect(React).toBeDefined()
    expect(React.createElement).toBeDefined()
  })

  test('DOM environment is available', () => {
    expect(document).toBeDefined()
    expect(window).toBeDefined()
  })
})
