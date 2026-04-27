import { Graph } from '@antv/g6';
import type { NetworkData } from './types';

export function createGraph(containerId: string, data: NetworkData, title: string) {
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
        labelBackgroundFill: 'rgba(255, 255, 255, 0.8)',
        labelBackgroundPadding: [2, 4],
        labelPlacement: 'center',
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
        lineWidth: Math.max(e.width * 2, 1),
        stroke: e.color,
        strokeOpacity: 0.6
      }
    }))
  };

  const graph = new Graph({
    container: containerId,
    autoFit: 'view',
    data: graphData,
    node: {
      state: {
        active: {
          stroke: '#000',
          lineWidth: 2
        },
        inactive: {
          opacity: 0.2,
          labelOpacity: 0.2
        }
      }
    },
    edge: {
      type: 'line',
      style: {
        strokeOpacity: 0.6
      },
      state: {
        active: {
          strokeOpacity: 1,
          lineWidth: (d: any) => (d.style?.lineWidth || 1) * 1.5
        },
        inactive: {
          strokeOpacity: 0.1
        }
      }
    },
    // No layout needed since nodes have x and y in style
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      'drag-element',
      {
        type: 'hover-activate',
        enable: true,
        degree: 1
      }
    ],
    plugins: [
      {
        type: 'tooltip',
        trigger: 'hover',
        getContent: (e: any, items: any) => {
          let html = `<div style="padding: 4px; background: white; border: 1px solid #ccc; border-radius: 4px;">`;
          if (items && items.length > 0) {
            const model = items[0];
            const metrics = model.data || {};
            html += `<strong style="display:block; margin-bottom:4px; color: #333;">${model.id}</strong>`;
            for (const [k, v] of Object.entries(metrics)) {
              html += `<div style="font-size:12px; color: #555;"><b>${k}:</b> ${v}</div>`;
            }
          }
          html += `</div>`;
          return html;
        }
      }
    ]
  });

  graph.render();
  (window as any).__graph = graph;
  return graph;
}

export function setupSearch(graph: Graph, inputId: string, btnId: string) {
  const input = document.getElementById(inputId) as HTMLInputElement;
  const btn = document.getElementById(btnId);
  if (!input || !btn) return;

  btn.addEventListener('click', () => {
    const val = input.value.toLowerCase().trim();
    if (!val) {
        return;
    }
    
    const nodeData = graph.getNodeData();
    const target = nodeData.find(n => String(n.id).toLowerCase().includes(val));
    if (target) {
      graph.focusElement(target.id, true);
    } else {
      alert('Node not found');
    }
  });
}
