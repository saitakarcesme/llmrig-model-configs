import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
export default function(pi: ExtensionAPI) {
 pi.registerTool(defineTool({
  name: "clef_decide", label: "Clef decision",
  description: "Use Cloudflare Clef to make typed decisions: return option probabilities for choice, boolean (noul), and ordered score questions. This is a decision model, not a chat model.",
  parameters: Type.Object({state: Type.String(), questions: Type.Record(Type.String(), Type.Object({type: Type.Union([Type.Literal('choice'),Type.Literal('noul'),Type.Literal('score')]),instructions: Type.Optional(Type.String()),criteria: Type.Optional(Type.Union([Type.Record(Type.String(),Type.String()),Type.Array(Type.String())]))}))}),
  async execute(_id, params, signal) {
   const t=performance.now();
   const response=await fetch((process.env.CLEF_URL || 'http://127.0.0.1:18031')+'/v1/systemone',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:process.env.CLEF_MODEL || 'clef-flash',...params}),signal});
   if(!response.ok) throw new Error(`Clef HTTP ${response.status}: ${await response.text()}`);
   const result=await response.json();
   return {content:[{type:'text',text:JSON.stringify(result)}],details:{wall_ms:performance.now()-t,result}};
  }
 }));
}
