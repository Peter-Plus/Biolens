export type ModelOption={id:string;label:string;description:string};
export default function ModelPicker({value,models,disabled,onChange}:{value:string;models:ModelOption[];disabled:boolean;onChange:(value:string)=>void}){
 return <select className="model-picker" aria-label="选择模型" title={models.find(m=>m.id===value)?.description||'选择本轮模型'} value={value} disabled={disabled||!models.length} onChange={e=>onChange(e.target.value)}>
  {!value&&<option value="">正在加载模型…</option>}{models.map(model=><option key={model.id} value={model.id}>{model.label}</option>)}
 </select>;
}
