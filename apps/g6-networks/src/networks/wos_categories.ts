import { createGraph, setupSearch, setupExport } from '../lib/renderer';
import data from '@data/wos_categories.json';

const graph = createGraph('container', data as any, {
  title: 'WoS Categories Network',
  nodeField: 'paper_count',
  lodThreshold: 1.2,
  hullEnabled: true,
  minimapEnabled: true,
});
setupSearch(graph, 'searchInput', 'searchBtn');
setupExport(graph, 'exportBtn', 'wos_categories_network');