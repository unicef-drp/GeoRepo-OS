

export const getUrl = (viewName: string) => {
  // Returns an absolute path reference (a URL without the domain name) matching
  // a given view name
  return (window as any)[viewName];
}

