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

export interface GraphConfig {
  title: string;
  nodeField: 'paper_count' | 'weighted_degree' | 'betweenness';
  lodThreshold: number;        // zoom level where labels appear
  maxDisplayNodes?: number;    // optional cap for WebGL memory
  hullEnabled: boolean;
  minimapEnabled: boolean;
}

