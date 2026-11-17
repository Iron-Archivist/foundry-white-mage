import {ClassicLevel} from '/var/lib/foundry/app/node_modules/classic-level/index.js';
import fs from 'fs';
const [,,src,out]=process.argv; const {docs}=JSON.parse(fs.readFileSync(src));
const now=Date.now();
const stats={coreVersion:"13.350",systemId:"dnd5e",systemVersion:"5.3.3",createdTime:now,modifiedTime:now,lastModifiedBy:null,compendiumSource:null,duplicateSource:null,exportSource:null};
const dbs={};
const open=async n=>{if(!dbs[n]){fs.rmSync(`${out}/${n}`,{recursive:true,force:true});dbs[n]=new ClassicLevel(`${out}/${n}`,{valueEncoding:'json'});await dbs[n].open();}return dbs[n];};
for(const [coll,d] of docs){
  const pack = coll.startsWith('journal') ? 'white-mage-journal' : 'white-mage-items';
  const db=await open(pack); const p=d._parent; delete d._parent; d._stats=stats;
  if(coll==='items.effects') d.origin=null;
  await db.put(p?`!${coll}!${p}.${d._id}`:`!${coll}!${d._id}`, d);
}
for(const db of Object.values(dbs)) await db.close();
