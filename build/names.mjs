import {ClassicLevel} from '/var/lib/foundry/app/node_modules/classic-level/index.js';
const out={};
for (const p of ['spells','items']){const db=new ClassicLevel(process.argv[2]+'/'+p,{valueEncoding:'json'});
for await (const [k,v] of db.iterator()) if(k.startsWith('!items!')) out[p+'|'+v.name]={id:v._id,level:v.system.level,school:v.system.school};
await db.close();}
console.log(JSON.stringify(out));
