export type MapClickHandlerProps = {
  onLocationSelect: (
    formattedCoords: string,
    rawCoords: [number, number],
  ) => void;
};
