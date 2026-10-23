const path = require('path');
const sharp = require('C:/Users/20973/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
async function main(){
  const folder=path.join(__dirname,'charts');
  for(let m=6;m<=10;m++){
    await sharp(path.join(folder,`ratio-m${m}.svg`),{density:144}).png().toFile(path.join(folder,`ratio-m${m}.png`));
  }
  console.log('Rendered five high-resolution PNG charts.');
}
main().catch(e=>{console.error(e);process.exit(1);});
