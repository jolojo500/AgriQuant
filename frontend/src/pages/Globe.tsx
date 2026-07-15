import { useEffect, useState, useCallback, useMemo } from 'react'
import DeckGL from '@deck.gl/react'
import { _GlobeView as GlobeView } from '@deck.gl/core'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer, ScatterplotLayer, LineLayer } from '@deck.gl/layers'
import { api } from '../api/client'
import type { WeatherRegion } from '../types'

const INITIAL_VIEW_STATE = {
  longitude: -75,   // open on the Americas — 6 of 10 regions face-on
  latitude: 15,
  zoom: 0.8,
}


// Footprint tint: cold = cyan token (#00CFFF), hot = amber token (#FFAA33).
// 12°C..38°C covers Saskatchewan-to-Punjab in the live data.
function tempColor(tempC: number, alpha = 60): [number, number, number, number] {
  const x = Math.min(1, Math.max(0, (tempC - 12) / 26))
  return [
    Math.round(x * 255),        // 0   → 255
    Math.round(207 - x * 37),   // 207 → 170
    Math.round(255 - x * 204),  // 255 → 51
    alpha,
  ]
}

// One falling raindrop. phase de-syncs drops, slant carries the wind.
type Drop = {
  lon: number
  lat: number
  phase: number   // 0-1 head start so drops don't fall in lockstep
  speed: number   // fall cycles per second
  slant: number   // degrees of horizontal drift over one full fall (∝ wind_speed)
}

const RAIN_TOP = 450_000 // spawn altitude in meters — tall enough to read at zoom 0.8


export default function Globe() {
  const [regions, setRegions] = useState<WeatherRegion[]>([])
  const [hovered, setHovered] = useState<WeatherRegion | null>(null)
  const [cursor, setCursor] = useState({ x: 0, y: 0 })

  // Animation clock, one rAF loop driving every weather effect
  const [time, setTime] = useState(0)
  useEffect(() => {
    let raf: number
    const t0 = performance.now()
    const tick = (now: number) => {
      setTime((now - t0) / 1000)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  // Drop field, regenerated only when region data changes, NOT per frame.
  // Density and fall speed scale with real rainfall; slant with real wind.
  const drops = useMemo(() => {
    const all: Drop[] = []
    for (const r of regions) {
      const n = Math.min(60, Math.round(r.rainfall_mm / 6)) // 60mm → 10 drops, 400mm → 60
      for (let i = 0; i < n; i++) {
        all.push({
          lon: r.lon + (Math.random() - 0.5) * 4.5,
          lat: r.lat + (Math.random() - 0.5) * 3.5,
          phase: Math.random(),
          speed: 0.25 + Math.random() * 0.2 + r.rainfall_mm / 2000, // heavier rain falls faster
          slant: (r.wind_speed ?? 0) * 0.35,
        })
      }
    }
    return all
  }, [regions])

  // Regions under real heat stres, same >35°C feature the model trains on
  const hotRegions = useMemo(
    () => regions.filter(r => (r.heat_stress_days ?? 0) > 30),
    [regions]
  )

    // Humidity range across the current data — haze contrast stays relative in any season
  const [hMin, hMax] = useMemo(() => {
    if (!regions.length) return [0, 100]
    const hs = regions.map(r => r.humidity ?? 0)
    return [Math.min(...hs), Math.max(...hs)]
  }, [regions])





 useEffect(() => {
    api.getWeather()
        .then(data => setRegions(data.regions))
        .catch(() => setRegions([
        { region: 'iowa',            lat: 42.0,  lon: -93.6,  rainfall_mm: 180, temp_max: 28, humidity: 72, solar_radiation: 18, wind_speed: 4.2, drought_days: 41, heat_stress_days: 2  },
        { region: 'kansas',          lat: 38.7,  lon: -98.4,  rainfall_mm: 95,  temp_max: 34, humidity: 45, solar_radiation: 22, wind_speed: 5.8, drought_days: 63, heat_stress_days: 21 },
        { region: 'mato_grosso',     lat: -12.6, lon: -55.9,  rainfall_mm: 310, temp_max: 31, humidity: 80, solar_radiation: 20, wind_speed: 2.1, drought_days: 22, heat_stress_days: 8  },
        { region: 'parana',          lat: -23.4, lon: -51.9,  rainfall_mm: 240, temp_max: 27, humidity: 75, solar_radiation: 17, wind_speed: 2.8, drought_days: 30, heat_stress_days: 1  },
        { region: 'buenos_aires_ag', lat: -36.6, lon: -63.8,  rainfall_mm: 120, temp_max: 22, humidity: 60, solar_radiation: 14, wind_speed: 4.9, drought_days: 55, heat_stress_days: 0  },
        { region: 'saskatchewan',    lat: 52.1,  lon: -106.7, rainfall_mm: 60,  temp_max: 18, humidity: 50, solar_radiation: 12, wind_speed: 4.5, drought_days: 70, heat_stress_days: 0  },
        { region: 'heilongjiang',    lat: 47.0,  lon: 128.9,  rainfall_mm: 145, temp_max: 24, humidity: 65, solar_radiation: 15, wind_speed: 3.4, drought_days: 48, heat_stress_days: 0  },
        { region: 'henan',           lat: 34.0,  lon: 113.7,  rainfall_mm: 200, temp_max: 30, humidity: 70, solar_radiation: 16, wind_speed: 2.6, drought_days: 38, heat_stress_days: 6  },
        { region: 'punjab_india',    lat: 30.9,  lon: 75.9,   rainfall_mm: 85,  temp_max: 38, humidity: 40, solar_radiation: 24, wind_speed: 3.1, drought_days: 68, heat_stress_days: 35 },
        { region: 'maharashtra',     lat: 19.7,  lon: 75.7,   rainfall_mm: 270, temp_max: 33, humidity: 78, solar_radiation: 19, wind_speed: 3.7, drought_days: 26, heat_stress_days: 12 },
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
    // Humidity haze — big, faint dome; denser air = more visible
    new ScatterplotLayer({
      id: 'humidity-haze',
      data: regions,
      getPosition: (d: WeatherRegion) => [d.lon, d.lat],
      getRadius: 430000,
      getFillColor: (d: WeatherRegion) => {
        const h = hMax > hMin ? ((d.humidity ?? 0) - hMin) / (hMax - hMin) : 0.5
        return [120, 190, 255, Math.round(12 + h * 48)]   // driest region alpha 12, wettest 60
      },
      stroked: false,
      pickable: false,
      updateTriggers: { getFillColor: [regions, hMin, hMax] },
    }),

    // Solar halo — ring brightness ∝ solar radiation (5..17 MJ/m²/day live range)
    new ScatterplotLayer({
      id: 'solar-halo',
      data: regions,
      getPosition: (d: WeatherRegion) => [d.lon, d.lat],
      getRadius: 330000,
      filled: false,
      stroked: true,
      getLineColor: (d: WeatherRegion) => {
        const s = Math.min(1, Math.max(0, ((d.solar_radiation ?? 0) - 5) / 12))
        return [255, 214, 120, Math.round(30 + s * 110)]
      },
      getLineWidth: 9000,
      pickable: false,
      updateTriggers: { getLineColor: [regions] },
    }),

       // Ground footprint — weather over an *area*, tinted by real temperature
    new ScatterplotLayer({
      id: 'region-footprint',
      data: regions,
      getPosition: (d: WeatherRegion) => [d.lon, d.lat],
      getRadius: 260000,
      getFillColor: (d: WeatherRegion) => tempColor(d.temp_max),
      stroked: true,
      getLineColor: (d: WeatherRegion) => tempColor(d.temp_max, 140),
      getLineWidth: 12000,
      pickable: true,
      onHover: handleHover,
      updateTriggers: { getFillColor: [regions], getLineColor: [regions] },
    }),
    // Heat shimmer — expanding radar pulse on heat-stressed regions, in --color-danger
    new ScatterplotLayer({
      id: 'heat-shimmer',
      data: hotRegions,
      getPosition: (d: WeatherRegion) => [d.lon, d.lat],
      getRadius: (_d: WeatherRegion, { index }: { index: number }) => {
        const p = (time * 0.45 + index * 0.37) % 1     // 0→1 expansion, de-synced per region
        return 260000 * (1 + p * 0.9)
      },
      filled: false,
      stroked: true,
      getLineColor: (_d: WeatherRegion, { index }: { index: number }) => {
        const p = (time * 0.45 + index * 0.37) % 1
        return [255, 61, 90, Math.round((1 - p) * 110)] // fades as it expands
      },
      getLineWidth: 7000,
      pickable: false,
      updateTriggers: { getRadius: [time], getLineColor: [time] },
    }),

    // Rain — LineLayer streaks falling from RAIN_TOP, drifting with the wind
    new LineLayer({
      id: 'rain',
      data: drops,
      getSourcePosition: (d: Drop) => {
        const p = (time * d.speed + d.phase) % 1            // 0→1 fall progress
        return [d.lon + p * d.slant, d.lat, RAIN_TOP * (1 - p)]
      },
      getTargetPosition: (d: Drop) => {
        const p = (time * d.speed + d.phase) % 1
        return [d.lon + p * d.slant, d.lat, Math.max(0, RAIN_TOP * (1 - p) - 55_000)]
      },
      getColor: [0, 207, 255, 160], // --color-cyan
      getWidth: 2,
      widthUnits: 'pixels',
      updateTriggers: { getSourcePosition: [time], getTargetPosition: [time] },
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
                    <p className="font-mono text-[0.8rem] text-ink mt-0 mb-1">
            Solar  <span className="text-warn">{hovered.solar_radiation} MJ/m²</span> · Wind <span className="text-cyan">{hovered.wind_speed} m/s</span>
          </p>
          <p className="font-mono text-[0.8rem] text-ink m-0">
            Drought <span className="text-danger">{hovered.drought_days}d</span> · Heat stress <span className="text-danger">{hovered.heat_stress_days}d</span>
          </p>
        </div>
      )}
    </div>
  )
}
