export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }

  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return value;
  }
}

export function titleCase(value: string) {
  return value
    .toLowerCase()
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
