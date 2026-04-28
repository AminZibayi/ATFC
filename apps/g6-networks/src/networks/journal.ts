import { createGraph, setupSearch } from '../lib/renderer';
import data from '@data/journal.json';

const graph = createGraph('container', data, 'Journal Network');
setupSearch(graph, 'searchInput', 'searchBtn');
