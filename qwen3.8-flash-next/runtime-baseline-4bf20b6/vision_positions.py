"""Wire image MRoPE into Flash-Next generation and QSA indexer planes.

The pinned native QSA kernels use one-dimensional cache positions. Image
queries and pooled block keys must instead use the same three-axis frequencies
as the main attention, as specified by the official Transformers QSA indexer.
"""
import torch
from exllamav3.modules.attn import Attention
from exllamav3.modules.qsa_indexer import QSAIndexer
from exllamav3.util.rope import RoPE
from exllamav3.util.tensor import get_for_device


class AngleTable:
    def __init__(self,frequencies,rope,offset,sine):
        self.frequencies=frequencies[0]
        self.rope=rope
        self.offset=offset
        self.sine=sine

    def __getitem__(self,positions):
        frequencies=self.frequencies
        angles=(positions.unsqueeze(-1).float()+self.offset)*self.rope.inv_freq
        bounded=positions.clamp(0,frequencies.shape[0]-1)
        angles=torch.where((positions<frequencies.shape[0]).unsqueeze(-1),frequencies[bounded],angles)
        values=angles.sin() if self.sine else angles.cos()
        return torch.cat((values,values),dim=-1)*self.rope.attn_factor


class PositionTables:
    def __init__(self,frequencies,rope,offset):
        self.cached_cos=AngleTable(frequencies,rope,offset,False)
        self.cached_sin=AngleTable(frequencies,rope,offset,True)

    def expand_cache(self,_):
        pass


def install(model,config):
    if not config.vision:
        return
    model.caps['mrope']=True
    model.g_rope=RoPE('cpu',config.rope_settings)
    original_update=QSAIndexer.update_planes
    original_bc=Attention.bc_attn_step

    def update(self,layer,x,rope,block_table,lengths,params):
        if not params.get('indexed_embeddings'):
            return original_update(self,layer,x,rope,block_table,lengths,params)
        if x.shape[0]!=1:
            raise RuntimeError('Vision QSA adapter supports one sequence at a time')
        frequencies=get_for_device(params,'inv_freq',x.device,None)
        if frequencies is not None:
            layer.flashnext_image_frequencies=frequencies
        else:
            frequencies=getattr(layer,'flashnext_image_frequencies',None)
        if frequencies is None:
            raise RuntimeError('Image QSA frequencies were not prepared')
        positions=params.get('positions')
        offset=int(positions[0])-int(lengths[0]) if positions is not None else 0
        tables=PositionTables(frequencies,rope,offset)
        return self.update_planes_ref(layer,x,tables,block_table,lengths,params)

    def bc(self,x,cache,params,*args,**kwargs):
        if params.get('indexed_embeddings'):
            return None
        return original_bc(self,x,cache,params,*args,**kwargs)

    QSAIndexer.update_planes=update
    Attention.bc_attn_step=bc
