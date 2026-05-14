import { createGraph, setupSearch, setupExport } from '../lib/renderer';
import data from '@data/co_affiliation.json';

const graph = createGraph('container', data as any, {
  title: 'Institutional Network',
  nodeField: 'paper_count',
  lodThreshold: 1.2,
  hullEnabled: true,
  minimapEnabled: true,
});
setupSearch(graph, 'searchInput', 'searchBtn');
setupExport(graph, 'exportBtn', 'institutional_network');

