import {build} from "esbuild";
await build({entryPoints:["src/street.jsx"],outfile:"../static/street-scene.js",bundle:true,minify:true,format:"iife",
  define:{"process.env.NODE_ENV":'"production"'},loader:{".jsx":"jsx"},jsx:"automatic",logLevel:"info"});
