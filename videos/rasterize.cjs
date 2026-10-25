const fs=require('node:fs');
const path=require('node:path');
const {Resvg}=require('../.build-check/node_modules/@resvg/resvg-js');
const dir=path.join(__dirname,'recording');
for(const name of fs.readdirSync(dir).filter(n=>n.endsWith('.svg'))){
 const target=path.join(dir,name.replace('.svg','.png'));
 const result=new Resvg(fs.readFileSync(path.join(dir,name)),{font:{loadSystemFonts:false,fontFiles:['C:/Windows/Fonts/consola.ttf','C:/Windows/Fonts/consolab.ttf','C:/Windows/Fonts/seguisym.ttf','C:/Windows/Fonts/seguiemj.ttf'],defaultFontFamily:'Consolas',monospaceFamily:'Consolas'}}).render();
 fs.writeFileSync(path.join(dir,name.replace('.svg','.png')),result.asPng());
}
console.log('Rasterized real app recording frames');
