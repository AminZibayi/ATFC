export interface NodeData {
  id: string;
  x: number;
  y: number;
  size: number;
  color: string;
  group_label: string;
  metrics: Record<string, string | number>;
}

export interface EdgeData {
  source: string;
  target: string;
  width: number;
  color: string;
  weight: number;
}

export interface NetworkData {
  nodes: NodeData[];
  edges: EdgeData[];
}
