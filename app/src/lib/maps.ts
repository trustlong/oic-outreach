let loader: Promise<typeof google.maps> | null = null

export function loadGoogleMaps(): Promise<typeof google.maps> {
  if (loader) return loader
  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  if (!key) return Promise.reject(new Error('VITE_GOOGLE_MAPS_API_KEY not set'))

  loader = new Promise((resolve, reject) => {
    const cbName = '__gmapsReady' + Math.random().toString(36).slice(2)
    ;(window as any)[cbName] = () => {
      delete (window as any)[cbName]
      resolve(google.maps)
    }
    const s = document.createElement('script')
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&libraries=marker&callback=${cbName}`
    s.async = true
    s.defer = true
    s.onerror = () => reject(new Error('Failed to load Google Maps'))
    document.head.appendChild(s)
  })
  return loader
}
