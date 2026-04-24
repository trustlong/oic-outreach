import { useEffect, useRef, useState } from 'react'
import type { ScoredRecord } from '../lib/types'
import { loadGoogleMaps } from '../lib/maps'
import { OIC_LAT, OIC_LON } from '../lib/scoring'
import { fmtName, fmtAddr, ETH_COLOR } from '../lib/format'

interface Props {
  items: ScoredRecord[]
  center?: { lat: number; lon: number }
  centerLabel?: string
}

export default function MapView({ items, center, centerLabel }: Props) {
  const divRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const markersRef = useRef<google.maps.Marker[]>([])
  const infoRef = useRef<google.maps.InfoWindow | null>(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    loadGoogleMaps()
      .then(maps => {
        if (cancelled || !divRef.current) return
        const c = center ?? { lat: OIC_LAT, lon: OIC_LON }
        mapRef.current = new maps.Map(divRef.current, {
          center: { lat: c.lat, lng: c.lon },
          zoom: 11,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        })
        infoRef.current = new maps.InfoWindow()
        setReady(true)
      })
      .catch(e => setError(e.message))
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const maps = google.maps

    markersRef.current.forEach(m => m.setMap(null))
    markersRef.current = []

    const bounds = new maps.LatLngBounds()

    // Center pin (OIC church, or user location on Near Me)
    const c = center ?? { lat: OIC_LAT, lon: OIC_LON }
    const centerPos = { lat: c.lat, lng: c.lon }
    const centerMarker = new maps.Marker({
      map,
      position: centerPos,
      title: centerLabel ?? 'One In Christ Church',
      icon: {
        path: 'M 0,-10 L 2.5,-3 10,-2 4,2.5 6,10 0,6 -6,10 -4,2.5 -10,-2 -2.5,-3 Z',
        fillColor: '#e91e63',
        fillOpacity: 1,
        strokeColor: '#fff',
        strokeWeight: 1.5,
        scale: 1.2,
      },
      zIndex: 1000,
    })
    centerMarker.addListener('click', () => {
      infoRef.current?.setContent(`<div style="font-size:13px;font-weight:600">${centerLabel ?? 'One In Christ Church'}</div>`)
      infoRef.current?.open(map, centerMarker)
    })
    markersRef.current.push(centerMarker)
    bounds.extend(centerPos)

    items.forEach((item, i) => {
      const lat = parseFloat(item.r.LAT)
      const lon = parseFloat(item.r.LON)
      if (!isFinite(lat) || !isFinite(lon)) return
      const pos = { lat, lng: lon }
      const color = ETH_COLOR[item.r.ESTIMATED_ETHNICITY || 'Unknown'] ?? '#95a5a6'
      const marker = new maps.Marker({
        map,
        position: pos,
        label: { text: String(i + 1), color: '#fff', fontSize: '12px', fontWeight: '700' },
        icon: {
          path: maps.SymbolPath.CIRCLE,
          fillColor: color,
          fillOpacity: 1,
          strokeColor: '#fff',
          strokeWeight: 2,
          scale: 13,
        },
        title: `${i + 1}. ${fmtName(item.r.Owner1)}`,
      })
      marker.addListener('click', () => {
        const name = fmtName(item.r.Owner1)
        const addr = fmtAddr(item.r.LocAddr)
        const nav = `https://maps.google.com/?q=${lat},${lon}`
        infoRef.current?.setContent(
          `<div style="font-size:13px;line-height:1.5;max-width:220px">
            <div style="font-weight:600;margin-bottom:2px">${i + 1}. ${name}</div>
            <div style="color:#555">${addr}</div>
            <div style="color:#888;font-size:12px;margin-top:2px">Score ${item.score} · ${item.dist.toFixed(1)} mi</div>
            <a href="${nav}" target="_blank" rel="noopener" style="display:inline-block;margin-top:6px;color:#1a73e8;font-size:12px">Open in Google Maps ↗</a>
          </div>`
        )
        infoRef.current?.open(map, marker)
      })
      markersRef.current.push(marker)
      bounds.extend(pos)
    })

    if (items.length) {
      map.fitBounds(bounds, 48)
    }
  }, [items, center, centerLabel, ready])

  if (error) {
    return <div style={{ margin: '0 12px 16px', padding: 12, fontSize: '.8em', color: '#c00', background: '#fff3f3', borderRadius: 8 }}>Map unavailable: {error}</div>
  }

  return (
    <div
      ref={divRef}
      style={{ height: 280, margin: '0 12px 16px', borderRadius: 12, overflow: 'hidden', background: '#eee' }}
    />
  )
}
