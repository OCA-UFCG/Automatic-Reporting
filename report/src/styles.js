import variables from './styles/variables.css?raw';
import cover from './styles/cover.css?raw';
import content from './styles/content.css?raw';
import print from './styles/print.css?raw';

export const pdfStyles = [variables, cover, content, print].join('\n');
