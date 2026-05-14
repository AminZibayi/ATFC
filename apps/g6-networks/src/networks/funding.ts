import { createGraph, setupSearch, setupExport } from '../lib/renderer';
import data from '@data/co_funding.json';

const graph = createGraph('container', data as any, {
  title: 'Funding Network',
  nodeField: 'paper_count',
  lodThreshold: 1.2,
  hullEnabled: true,
  minimapEnabled: true,
});
setupSearch(graph, 'searchInput', 'searchBtn');
setupExport(graph, 'exportBtn', 'funding_network');

