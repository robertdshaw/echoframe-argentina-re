import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

/**
 * Calls invalidateSize() shortly after the map mounts. Fixes the common
 * react-leaflet failure mode where a map initialised with a hidden or
 * 0px-tall container renders tiles at the wrong scale and never recovers.
 *
 * Drop this as a child of any MapContainer that lives below the fold or
 * inside a flex/grid container that resolves its height asynchronously.
 */
const MapSizingFix = () => {
  const map = useMap();
  useEffect(() => {
    const t = window.setTimeout(() => {
      try {
        map.invalidateSize();
      } catch {
        // Map may have been unmounted before the timer fired — ignore.
      }
    }, 80);
    return () => window.clearTimeout(t);
  }, [map]);
  return null;
};

export default MapSizingFix;
