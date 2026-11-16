import {build} from "esbuild";
const common={bundle:true,minify:true,format:"iife",define:{"process.env.NODE_ENV":'"production"'},loader:{".jsx":"jsx"},jsx:"automatic",logLevel:"info"};
await build({...common,entryPoints:["src/apt.jsx"],outfile:"../static/apt.js"});
await build({...common,entryPoints:["src/street.jsx"],outfile:"../static/street-scene.js"});
