const {chromium}=require('../.build-check/node_modules/playwright');
const path=require('node:path');
(async()=>{
const browser=await chromium.launch({headless:true});
for(const [name,port]of[['launch',3002],['setup-guide',3003]]){
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const response=await page.goto(`http://localhost:${port}/#project/${name}`,{waitUntil:'networkidle',timeout:60000});
 await page.screenshot({path:path.join(__dirname,name,'preview.png')});
 console.log(JSON.stringify({name,status:response.status(),title:await page.title(),body:(await page.locator('body').innerText()).slice(0,500)}));
 await page.close();
}
await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
