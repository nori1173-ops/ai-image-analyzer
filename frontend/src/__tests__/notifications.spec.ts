import { describe, expect, it } from 'vitest'
import { parseRecipientList } from '../notifications'

describe('parseRecipientList', () => {
  it('trims comma-separated addresses and removes empty values', () => {
    expect(parseRecipientList(' to@example.com, , cc@example.com ,, bcc@example.com ')).toEqual([
      'to@example.com',
      'cc@example.com',
      'bcc@example.com',
    ])
  })

  it('returns an empty array for an empty value', () => {
    expect(parseRecipientList('')).toEqual([])
  })
})
