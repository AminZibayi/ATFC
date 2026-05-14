import { createGraph, setupSearch, setupExport } from '../lib/renderer';
import data from '@data/author_keywords.json';

const graph = createGraph('container', data as any, {
  title: 'Author Keywords Network',
  nodeField: 'paper_count',
  lodThreshold: 1.2,
  hullEnabled: true,
  minimapEnabled: true,
});
setupSearch(graph, 'searchInput', 'searchBtn');
setupExport(graph, 'exportBtn', 'author_keywords_network');