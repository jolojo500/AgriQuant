import DeckGL from '@deck.gl/react'
import { _GlobeView } from '@deck.gl/core'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 20,
  zoom: 0.8,
}

export default function Globe() {
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      position: 'relative',
      background: 'var(--bg-primary)',
    }}>
      <DeckGL
        views={new _GlobeView({ resolution: 5 })}
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={[
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
                bounds: [
                  boundingBox[0][0],
                  boundingBox[0][1],
                  boundingBox[1][0],
                  boundingBox[1][1],
                ],
              })
            },
          }),
        ]}
      />
    </div>
  )
}