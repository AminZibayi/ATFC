import { Graph } from '@antv/g6';
import { Renderer as WebGLRenderer } from '@antv/g-webgl';
import type { NetworkData, GraphConfig } from './types';

export function createGraph(containerId: string, data: NetworkData, config: GraphConfig) {
  const container = document.getElementById(containerId);
  if (!container) throw new Error(`Container ${containerId} not found`);

  // Map backend JSON to G6 v5 specification
  const graphData = {
    nodes: data.nodes.map(n => ({
      id: String(n.id),
      data: {
        ...n.metrics,
        group_label: n.group_label
      },
      style: {
        x: n.x,
        y: n.y,
        size: n.size,
        fill: n.color,
        labelText: String(n.id),
        labelFill: '#333',
        labelPlacement: 'bottom' as const,
        labelOffsetY: 4,
        labelMaxWidth: 120,               // truncate long names
        labelWordWrap: false,
        labelVisibility: 'visible' as any,
        labelFontSize: 10,
        lineWidth: 1,
        stroke: '#fff'
      }
    })),
    edges: data.edges.map((e, idx) => ({
      id: `edge-${idx}`,
      source: String(e.source),
      target: String(e.target),
      data: { weight: e.weight },
      style: {
        lineWidth: Math.max(e.width * 2, 0.5),
        stroke: e.color,
        strokeOpacity: 0.4
      }
    }))
  };

  const communityCount = new Set(data.nodes.map(n => n.group_label)).size;
  const USE_HULL = config.hullEnabled && communityCount <= 30;
  const USE_LEGEND = communityCount <= 30;

  const plugins: any[] = [
    {
      type: 'tooltip',
      trigger: 'hover',
      getContent: (_e: any, items: any) => {
        let html = `<div style="padding: 4px; background: white; border: 1px solid #ccc; border-radius: 4px;">`;
        if (items && items.length > 0) {
          const model = items[0];
          const metrics = model.data || {};
          html += `<strong style="display:block; margin-bottom:4px; color: #333;">${model.id}</strong>`;
          for (const [k, v] of Object.entries(metrics)) {
            if (k === 'group_label') continue;
            html += `<div style="font-size:12px; color: #555;"><b>${k}:</b> ${v}</div>`;
          }
        }
        html += `</div>`;
        return html;
      }
    }
  ];

  if (USE_LEGEND) {
    plugins.push({
      type: 'legend',
      key: 'legend',
      nodeField: 'group_label',
      position: 'bottom-right',
      layout: 'flex-wrap',
      itemSpacing: 8,
      titleText: 'Communities',
    });
  }

  if (USE_HULL) {
    plugins.push({
      type: 'hull',
      key: 'community-hull',
      members: (d: any) => d.data?.group_label,
      style: {
        fillOpacity: 0.08,
        strokeOpacity: 0.3,
        lineWidth: 1.5,
      }
    });
  }

  if (config.minimapEnabled) {
    plugins.push({
      type: 'minimap',
      key: 'minimap',
      size: [180, 120],
      position: 'bottom-left',
      containerStyle: {
        background: '#f8f8f8',
        border: '1px solid #ddd',
      }
    });
  }

  const graph = new Graph({
    container: containerId,
    renderer: () => new WebGLRenderer(),
    autoFit: 'view',
    data: graphData,
    node: {
      state: {
        active: {
          stroke: '#000',
          lineWidth: 2,
          zIndex: 10
        },
        inactive: {
          opacity: 0.15,
          labelOpacity: 0
        }
      },
      lodLevels: [
        { zoomRange: [0, 0.6], primary: true }, // zoom out: dots only
        { zoomRange: [0.6, Infinity], primary: false } // zoom in: dots + labels
      ]
    } as any,
    edge: {
      type: 'line',
      style: {
        strokeOpacity: 0.4
      },
      state: {
        active: {
          strokeOpacity: 1,
          lineWidth: (d: any) => (d.style?.lineWidth || 1) * 2
        },
        inactive: {
          strokeOpacity: 0.05
        }
      }
    },
    behaviors: [
      'drag-canvas',
      {
        type: 'zoom-canvas',
        sensitivity: 0.5,
      },
      'drag-element',
      {
        type: 'click-select',
        multiple: true,
      }
    ],
    plugins: plugins
  });

  graph.render();

  // Click-based highlight logic instead of hover-activate
  graph.on('node:click', (evt: any) => {
    const nodeId = evt.itemId;
    if (!nodeId) return;
    
    const neighbors = new Set(
      graph.getNeighborNodesData(nodeId).map((n: any) => n.id)
    );
    
    graph.getNodeData().forEach((n: any) => {
      const state = (neighbors.has(n.id) || n.id === nodeId) ? 'active' : 'inactive';
      graph.setElementState(n.id, state);
    });

    // Also highlight edges
    graph.getEdgeData().forEach((e: any) => {
        const isActive = (e.source === nodeId || e.target === nodeId);
        graph.setElementState(e.id, isActive ? 'active' : 'inactive');
    });
  });

  graph.on('canvas:click', () => {
    graph.getNodeData().forEach((n: any) => graph.setElementState(n.id, []));
    graph.getEdgeData().forEach((e: any) => graph.setElementState(e.id, []));
  });
  
  // Set the title
  const titleEl = document.getElementById('network-title');
  if (titleEl) {
    titleEl.textContent = config.title;
  }
  
  (window as any).__graph = graph;
  return graph;
}

export function setupSearch(graph: Graph, inputId: string, btnId: string) {
  const input = document.getElementById(inputId) as HTMLInputElement;
  const btn = document.getElementById(btnId);
  if (!input || !btn) return;

  btn.addEventListener('click', () => {
    const val = input.value.toLowerCase().trim();
    if (!val) return;
    
    const nodeData = graph.getNodeData();
    const target = nodeData.find(n => String(n.id).toLowerCase().includes(val));
    if (target) {
      graph.focusElement(target.id, true);
    } else {
      alert('Node not found');
    }
  });
}

export function setupExport(graph: Graph, btnId: string, filename: string) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (typeof (graph as any).downloadFullImage === 'function') {
      (graph as any).downloadFullImage(filename, 'image/png', {
        backgroundColor: '#ffffff',
        padding: 30,
      });
    } else if (typeof (graph as any).toDataURL === 'function') {
        (graph as any).toDataURL().then((url: string) => {
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
        });
    }
  });
}
