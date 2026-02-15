import sharp from 'sharp';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const inputSvg = resolve(__dirname, '../public/icon.svg');
const outputDir = resolve(__dirname, '../public/icons');

const sizes = [192, 512];

for (const size of sizes) {
  await sharp(inputSvg)
    .resize(size, size)
    .png()
    .toFile(resolve(outputDir, `icon-${size}.png`));
  console.log(`Generated icon-${size}.png`);
}

console.log('Done!');
