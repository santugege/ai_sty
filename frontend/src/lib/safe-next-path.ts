export function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }

  try {
    if (decodeURIComponent(value).includes("\\")) {
      return "/";
    }
  } catch {
    return "/";
  }

  return value;
}
