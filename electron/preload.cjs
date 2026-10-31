const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('biolens',{
  connection:()=>ipcRenderer.invoke('connection'),
  chooseDirectory:()=>ipcRenderer.invoke('choose-directory'),
  openExternal:url=>ipcRenderer.invoke('external',url),
  saveArtifact:(id,name)=>ipcRenderer.invoke('save-artifact',id,name)
});
