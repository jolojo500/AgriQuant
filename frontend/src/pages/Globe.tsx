import { useEffect, useState, useCallback } from 'react'
import DeckGL from '@deck.gl/react'
import { _GlobeView as GlobeView } from '@deck.gl/core'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer, ScatterplotLayer } from '@deck.gl/layers'
import { api } from '../api/client'
import type { WeatherRegion } from '../types'

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 20,
  zoom: 0.8,
}

export default function Globe() {
  const [regions, setRegions] = useState<WeatherRegion[]>([])
  const [hovered, setHovered] = useState<WeatherRegion | null>(null)
  const [cursor, setCursor] = useState({ x: 0, y: 0 })

 useEffect(() => {
    api.getWeather()
        .then(data => setRegions(data.regions))
        .catch(() => setRegions([
        { region: 'iowa',            lat: 42.0,  lon: -93.6, rainfall_mm: 180, temp_max: 28, humidity: 72 },
        { region: 'kansas',          lat: 38.7,  lon: -98.4, rainfall_mm: 95,  temp_max: 34, humidity: 45 },
        { region: 'mato_grosso',     lat: -12.6, lon: -55.9, rainfall_mm: 310, temp_max: 31, humidity: 80 },
        { region: 'parana',          lat: -23.4, lon: -51.9, rainfall_mm: 240, temp_max: 27, humidity: 75 },
        { region: 'buenos_aires_ag', lat: -36.6, lon: -63.8, rainfall_mm: 120, temp_max: 22, humidity: 60 },
        { region: 'saskatchewan',    lat: 52.1,  lon: -106.7, rainfall_mm: 60, temp_max: 18, humidity: 50 },
        { region: 'heilongjiang',    lat: 47.0,  lon: 128.9, rainfall_mm: 145, temp_max: 24, humidity: 65 },
        { region: 'henan',           lat: 34.0,  lon: 113.7, rainfall_mm: 200, temp_max: 30, humidity: 70 },
        { region: 'punjab_india',    lat: 30.9,  lon: 75.9,  rainfall_mm: 85,  temp_max: 38, humidity: 40 },
        { region: 'maharashtra',     lat: 19.7,  lon: 75.7,  rainfall_mm: 270, temp_max: 33, humidity: 78 },
        ]))

    }, [])

  const handleHover = useCallback((info: any) => {
    if (info.object) {
      setHovered(info.object)
      setCursor({ x: info.x, y: info.y })
    } else {
      setHovered(null)
    }
  }, [])

  const layers = [
    // Base map
    new TileLayer({
      data: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      minZoom: 0,
      maxZoom: 19,
      tileSize: 256,
      renderSubLayers: (props: any) => {
        const { boundingBox } = props.tile
        return new BitmapLayer(props, {
          data: undefined,
          image: props.data,
          bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
        })
      },
    }),

    // Glow outer ring
    new ScatterplotLayer({
      id: 'regions-glow',
      data: regions,
      getPosition: (d: WeatherRegion) => [d.lon, d.lat],
      getRadius: 300000,
      getFillColor: [0, 255, 136, 40],  // green, very transparent
      stroked: false,
      pickable: false,
    }),

    // Inner dot
    new ScatterplotLayer({
      id: 'regions-dot',
      data: regions,
      getPosition: (d: WeatherRegion) => [d.lon, d.lat],
      getRadius: 80000,
      getFillColor: (d: WeatherRegion) => {
        // Color by rainfall — more rain = brighter green
        const intensity = Math.min(d.rainfall_mm / 300, 1)
        return [0, Math.floor(180 + intensity * 75), Math.floor(100 + intensity * 36), 255]
      },
      stroked: true,
      getLineColor: [0, 255, 136, 120],
      getLineWidth: 15000,
      pickable: true,
      onHover: handleHover,
      updateTriggers: { getFillColor: [regions] },
    }),
  ]

  return (
    <div className="w-screen h-screen relative bg-canvas">
      <DeckGL
        views={new GlobeView({ resolution: 5 })}
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
      />

      {/* Hover tooltip */}
      {hovered && (
        <div
          className="fixed bg-surface border border-line-strong rounded-md px-4 py-3 pointer-events-none z-10"
          style={{ left: cursor.x + 16, top: cursor.y + 16 }}
        >
          <p className="font-mono text-[0.65rem] text-accent mt-0 mb-2 tracking-[0.1em]">
            {hovered.region.replace(/_/g, ' ').toUpperCase()} LAST 90 DAYS
          </p>
          <p className="font-mono text-[0.8rem] text-ink mt-0 mb-1">
            Rain   <span className="text-cyan">{hovered.rainfall_mm} mm</span>
          </p>
          <p className="font-mono text-[0.8rem] text-ink mt-0 mb-1">
            Temp   <span className="text-warn">{hovered.temp_max}°C</span>
          </p>
          <p className="font-mono text-[0.8rem] text-ink m-0">
            Humidity  <span className="text-ink-muted">{hovered.humidity}%</span>
          </p>
        </div>
      )}
    </div>
  )
}
