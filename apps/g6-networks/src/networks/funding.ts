import { createGraph, setupSearch } from '../lib/renderer';
import data from '../data/funding.json';

const graph = createGraph('container', data, 'Funding Network');
setupSearch(graph, 'searchInput', 'searchBtn');
