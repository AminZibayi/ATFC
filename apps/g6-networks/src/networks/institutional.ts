import { createGraph, setupSearch } from '../lib/renderer';
import data from '@data/institutional.json';

const graph = createGraph('container', data, 'Institutional Network');
setupSearch(graph, 'searchInput', 'searchBtn');
