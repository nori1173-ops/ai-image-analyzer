export function parseRecipientList(value: string): string[] {
  return value.split(',').map((address) => address.trim()).filter(Boolean)
}
