export interface MenuProps<K extends string> {
  labels: Record<K, string>;
  onSelect?: (key: K) => void;
  labelTitle?: string;
  disabled?: boolean;

}
