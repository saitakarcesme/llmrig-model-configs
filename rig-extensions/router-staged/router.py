"""Loopback Elpis router: one in-flight request per engine, bounded affinity, no POST replay."""
from __future__ import annotations
import collections
import csv
import io
import fcntl
import http.client
import json
import logging
import os
import signal
import subprocess
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG=logging.getLogger("elpis-router")
LIMIT=32*1024*1024
HOP={"connection","transfer-encoding","keep-alive","proxy-authenticate","proxy-authorization","te","trailers","upgrade","content-length"}

SAMPLED_MODEL="qwen3.8-27b-sampled"
TEXT_MODELS={"qwen3.8:27b","qwen3.8-27b"}

def has_images(payload):
    if payload.get("images"):return True
    for message in payload.get("messages",[]):
        if message.get("images"):return True
        content=message.get("content")
        if isinstance(content,list) and any(isinstance(part,dict) and part.get("type") in {"image_url","input_image","image"} for part in content):return True
    return False

def gpu_memory():
    result=subprocess.run(["nvidia-smi","--query-gpu=index,name,memory.total,memory.used,memory.free","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=3,check=True)
    return [{"index":int(row[0]),"name":row[1].strip(),"total_mib":int(row[2]),"used_mib":int(row[3]),"free_mib":int(row[4])} for row in csv.reader(io.StringIO(result.stdout))]

def props(server):
    pool=server.pool
    with pool.telemetry_lock:
        now=time.monotonic()
        if now-pool.telemetry_at>=5:
            try:pool.telemetry={"gpus":gpu_memory(),"gpu_memory_error":None}
            except (OSError,ValueError,subprocess.SubprocessError) as error:
                pool.telemetry={"gpus":None,"gpu_memory_error":type(error).__name__}
            pool.telemetry_at=now;pool.telemetry_unix=time.time()
        memory=dict(pool.telemetry);memory["gpu_memory_sampled_at"]=pool.telemetry_unix
    media_locked=False
    if pool.media_lock:
        with open(pool.media_lock,"a") as lease:
            try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:media_locked=True
    host_memory=None
    try:
        mem={line.split(":")[0]:int(line.split()[1])/1024 for line in Path("/proc/meminfo").read_text().splitlines()}
        host_memory={"total_mib":mem["MemTotal"],"available_mib":mem["MemAvailable"],"swap_used_mib":mem["SwapTotal"]-mem["SwapFree"]}
    except (OSError,ValueError,KeyError):pass
    slots=[]
    for i,lane in enumerate(pool.snapshot()):
        reserved=media_locked and i==pool.media_lane
        slots.append({"id":i,"gpu_index":i,"model":"qwen3.8-27b","context_limit":262144,
                      "healthy":lane["healthy"],"busy":lane["busy"],"gpu_lease_held":reserved,
                      "available":lane["healthy"] and not lane["busy"] and not reserved,
                      "context_tokens_in_use":None})
    return {"backend":"elpis","schema_version":1,"sampled_at":time.time(),**memory,"host_memory":host_memory,"slots":slots,
            "extensions":{"health_path":"/extensions/health","embedding_device":"cpu","embedding_memory_limit_mib":2048,"media_worker_memory_limit_mib":6144,"media_gpu_index":1},
            "text_sampling":{"temperature":0,"top_p":1,"presence_penalty":0,"stochastic_sampling":False},
            "vision":{"model":"qwen3.8-27b","context_limit":65536,"gpu_index":pool.media_lane,"shares_secondary_text_slot":True},
            "limits":{"chat_body_bytes":LIMIT,"pdf_file_bytes":100*1024*1024},
            "notes":["Free GPU memory is a snapshot, not an allocation guarantee.","Each text slot has its own context limit; limits are not additive for one request.","Live context occupancy is not exposed by this backend (null).","PDF and vision temporarily reserve the secondary GPU."]}

class Pool:
    def __init__(self, ports, media_lock=None, media_lane=1):
        self.telemetry_lock=threading.Lock();self.telemetry_at=float("-inf");self.telemetry={};self.telemetry_unix=None
        self.media_lock=media_lock;self.media_lane=media_lane;self.leases={}
        self.ports=ports;self.busy=[False]*len(ports);self.healthy=[False]*len(ports)
        self.cv=threading.Condition();self.affinity=collections.OrderedDict();self.completed=[0]*len(ports)
    def lock_lane(self,i):
        if i!=self.media_lane or not self.media_lock:return True
        lease=open(self.media_lock,"a")
        try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:lease.close();return False
        self.leases[i]=lease
        return True
    def acquire(self,key,timeout=7200):
        end=time.monotonic()+timeout
        with self.cv:
            while True:
                available=[i for i in range(len(self.ports)) if self.healthy[i] and not self.busy[i]]
                preferred=self.affinity.get(key)
                available.sort(key=lambda i:(i!=preferred,self.completed[i]))
                i=next((i for i in available if self.lock_lane(i)),None)
                if i is not None:
                    self.busy[i]=True
                    if key:
                        self.affinity[key]=i;self.affinity.move_to_end(key)
                        while len(self.affinity)>256:self.affinity.popitem(last=False)
                    return i
                if not any(self.healthy):raise ConnectionError("No healthy local Elpis engine")
                left=end-time.monotonic()
                if left<=0:raise TimeoutError("Local engine queue timeout")
                self.cv.wait(min(left,1))
    def reserve(self,i,timeout=7200):
        end=time.monotonic()+timeout
        with self.cv:
            while self.busy[i] or not self.lock_lane(i):
                left=end-time.monotonic()
                if left<=0:raise TimeoutError("GPU reservation timeout")
                self.cv.wait(min(left,1))
            self.busy[i]=True
        return i
    def release(self,i):
        with self.cv:
            lease=self.leases.pop(i,None)
            if lease:lease.close()
            self.busy[i]=False;self.completed[i]+=1;self.cv.notify_all()
    def set_health(self,i,healthy):
        with self.cv:self.healthy[i]=healthy;self.cv.notify_all()
    def snapshot(self):
        with self.cv:return [{"port":p,"healthy":self.healthy[i],"busy":self.busy[i],"completed":self.completed[i]} for i,p in enumerate(self.ports)]

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,config):
        self.config=config;self.pool=Pool(config["ports"],config.get("media_lock"),config.get("vision_lane",1))
        self.auth="Bearer "+Path(config["api_key_file"]).read_text().strip()
        self.stop=threading.Event();self.inflight=threading.BoundedSemaphore(4);self.notified=False
        super().__init__(("127.0.0.1",config.get("port",11446)),Handler)
    def probe(self):
        while not self.stop.is_set():
            for i,p in enumerate(self.pool.ports):
                c=http.client.HTTPConnection("127.0.0.1",p,timeout=3)
                try:
                    c.request("GET","/health",headers={"Authorization":self.auth});r=c.getresponse();r.read();ok=r.status==200
                except OSError:ok=False
                finally:c.close()
                self.pool.set_health(i,ok)
            if not self.notified and all(self.pool.healthy):
                address=os.environ.get("NOTIFY_SOCKET")
                if address:
                    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as notify:
                        notify.sendto(b"READY=1",("\0"+address[1:]) if address.startswith("@") else address)
                self.notified=True
            self.stop.wait(5)

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def setup(self):
        super().setup();self.connection.settimeout(60)
    def log_message(self,*args):pass
    def reply(self,status,data):
        raw=json.dumps(data).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def proxy(self,port,path,body=None):
        c=http.client.HTTPConnection("127.0.0.1",port,timeout=7200)
        started=False
        try:
            headers={}
            if body is not None:headers["Content-Type"]="application/json"
            c.request(self.command,path,body,headers)
            r=c.getresponse()
            self.send_response(r.status)
            for k,v in r.getheaders():
                if k.lower() not in HOP:self.send_header(k,v)
            self.send_header("Connection","close");self.end_headers()
            self.close_connection=True;started=True
            while chunk:=r.read1(65536):self.wfile.write(chunk);self.wfile.flush()
        except (OSError,http.client.HTTPException):
            if not started:self.reply(503,{"error":"Local upstream unavailable; request not replayed"})
        finally:c.close()
    def documents(self,port=None):
        self.close_connection=True
        c=http.client.HTTPConnection("127.0.0.1",port or self.server.config.get("pdf_port",11447),timeout=8500)
        started=False
        try:
            if self.headers.get("Transfer-Encoding"):raise ValueError("Content-Length required")
            if len(self.headers.get_all("Content-Length",[]))>1:raise ValueError("Duplicate Content-Length")
            size=int(self.headers.get("Content-Length","0"))
            if size<0:raise ValueError("Invalid Content-Length")
            limit=256*1024 if self.path=="/v1/embeddings" else 101*1024*1024
            if size>limit:return self.reply(413,{"error":"Upload exceeds endpoint size limit"})
            c.putrequest(self.command,self.path)
            c.putheader("Content-Type",self.headers.get("Content-Type","application/octet-stream"))
            c.putheader("Content-Length",str(size));c.endheaders()
            while size:
                chunk=self.rfile.read(min(65536,size))
                if not chunk:raise ValueError("Incomplete request body")
                c.send(chunk);size-=len(chunk)
            r=c.getresponse();self.send_response(r.status)
            for k,v in r.getheaders():
                if k.lower() not in HOP:self.send_header(k,v)
            self.send_header("Connection","close");self.end_headers();started=True
            while chunk:=r.read1(65536):self.wfile.write(chunk);self.wfile.flush()
        except ValueError as e:
            if not started:self.reply(400,{"error":str(e)})
        except (OSError,http.client.HTTPException):
            if not started:self.reply(503,{"error":"Local auxiliary service unavailable; request not replayed"})
        finally:c.close()
    def do_GET(self):
        if self.path=="/extensions/health":return self.proxy(self.server.config.get("extension_port",11450),"/health")
        if self.path=="/props":return self.reply(200,props(self.server))
        if self.path=="/v1/documents" or self.path.startswith("/v1/documents/"):return self.documents()
        if self.path=="/api/tags":
            c=http.client.HTTPConnection("127.0.0.1",self.server.config.get("vision_port",11436),timeout=10)
            try:
                c.request("GET",self.path);r=c.getresponse();data=json.load(r)
                data["models"]=[v for v in data.get("models",[]) if v.get("name") in {self.server.config.get("vision_model"),self.server.config.get("multimodal_model")}]
                return self.reply(r.status,data)
            except (OSError,ValueError):return self.reply(503,{"error":"Local vision metadata unavailable"})
            finally:c.close()
        if self.path in {"/api/ps","/api/version"}:
            return self.proxy(self.server.config.get("vision_port",11436),self.path)
        lanes=self.server.pool.snapshot();ready=any(l["healthy"] for l in lanes)
        if self.path=="/health":return self.reply(200 if ready else 503,{"state":"ready" if ready else "unavailable","backend":"elpis","context":262144,"lanes":lanes})
        if self.path=="/v1/models":return self.reply(200 if ready else 503,{"object":"list","data":[{"id":"qwen3.8-27b","object":"model","owned_by":"local","max_model_len":262144,"sampling":"greedy","input_modalities":["text","image"],"architecture":{"input_modalities":["text","image"],"output_modalities":["text"]},"vision_backend":"local-ollama-qwen27b","vision_max_model_len":65536}, {"id":self.server.config.get("vision_model","qwen2.5vl:3b"),"object":"model","owned_by":"local-ollama","input_modalities":["text","image"]}, {'id': 'qwen3.8-27b-sampled', 'object': 'model', 'owned_by': 'local-ollama', 'max_model_len': 65536, 'input_modalities': ['text', 'image'], 'sampling_defaults': {'temperature': 1.0, 'top_p': 0.95, 'top_k': 20, 'presence_penalty': 0}}, {'id': 'qwen3-embedding:0.6b', 'object': 'model', 'owned_by': 'local-ollama-cpu', 'capabilities': ['embeddings'], 'max_model_len': 2048}]})
        self.reply(404,{"error":"Unknown local endpoint"})
    def vision(self,payload):
        cfg=self.server.config
        if payload.get("model")==SAMPLED_MODEL:
            if self.path!="/v1/chat/completions":raise ValueError("Use /v1/chat/completions for the sampled profile")
            top_k=payload.pop("top_k",20)
            if type(top_k) not in (int,float) or top_k!=20:raise ValueError("The sampled profile has fixed top_k=20")
            payload.setdefault("temperature",1.0);payload.setdefault("top_p",0.95)
            payload.setdefault("presence_penalty",0);payload.setdefault("max_tokens",4096)
            payload["model"]=cfg.get("multimodal_model")
        if payload.get("model") in TEXT_MODELS:
            payload["model"]=cfg.get("multimodal_model")
        selected_model=payload.get("model")
        if not cfg.get("vision_container") or selected_model not in {cfg.get("vision_model"),cfg.get("multimodal_model")}:
            raise ValueError("Only the configured local vision model is accepted here")

        index=self.server.pool.reserve(cfg.get("vision_lane",1));stopped=False
        name=cfg["vision_container"]
        def ollama(path,body):
            c=http.client.HTTPConnection("127.0.0.1",cfg.get("vision_port",11436),timeout=7200)
            try:
                c.request("POST",path,json.dumps(body),{"Content-Type":"application/json"})
                response=c.getresponse();raw=response.read(LIMIT+1)
                if len(raw)>LIMIT:raise ValueError("Vision response exceeds limit")
                if response.status!=200:raise ConnectionError("Local vision service failed")
                return json.loads(raw)
            finally:c.close()
        try:
            self.server.pool.set_health(index,False)
            subprocess.run(["docker","stop","--time","45",name],check=True,timeout=55,capture_output=True)
            stopped=True
            payload["keep_alive"]=0
            # Ollama supports native NDJSON and OpenAI SSE; forward incrementally.
            self.proxy(cfg.get("vision_port",11436),self.path,json.dumps(payload).encode())
        finally:
            if stopped:
                try:
                    ollama("/api/generate",{"model":selected_model,"keep_alive":0})
                    end=time.monotonic()+60
                    while time.monotonic()<end:
                        c=http.client.HTTPConnection("127.0.0.1",cfg.get("vision_port",11436),timeout=5)
                        try:
                            c.request("GET","/api/ps");r=c.getresponse();models=json.load(r).get("models",[])
                        finally:c.close()
                        if not models:break
                        time.sleep(1)
                    else:raise TimeoutError("Vision model did not unload")
                    subprocess.run(["docker","start",name],check=True,timeout=30,capture_output=True)
                except Exception:
                    LOG.exception("Failed to restore secondary engine after vision")
            self.server.pool.release(index)

    def do_POST(self):
        if self.path in {"/v1/embeddings","/v1/audio/transcriptions","/v1/ocr","/v1/pdf/objects"}:return self.documents(self.server.config.get("extension_port",11450))
        if self.path=="/v1/documents" or self.path.startswith("/v1/documents/"):return self.documents()
        if self.path not in {"/v1/chat/completions","/v1/completions","/v1/chat/completions/render","/api/chat","/api/generate","/api/show"}:
            self.close_connection=True;return self.reply(404,{"error":"Unknown local endpoint"})
        if not self.server.inflight.acquire(blocking=False):
            self.close_connection=True
            return self.reply(429,{"error":"Local inference queue is full; retry later"})
        index=None;conn=None;started=False;t0=time.monotonic()
        try:
            if self.headers.get("Transfer-Encoding"):raise ValueError("Content-Length required")
            if len(self.headers.get_all("Content-Length",[]))!=1:raise ValueError("Exactly one Content-Length required")
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=LIMIT:raise ValueError("Request body must be between 1 byte and 32 MiB")
            body=self.rfile.read(n)
            if len(body)!=n:raise ValueError("Incomplete request body")
            payload=json.loads(body)
            if not isinstance(payload,dict):raise ValueError("JSON object required")
            if self.path=="/api/show":
                if payload.get("model",payload.get("name"))!=self.server.config.get("vision_model"):
                    raise ValueError("Use /v1/models for Elpis text models")
                return self.proxy(self.server.config.get("vision_port",11436),self.path,body)
            if self.path in {"/api/chat","/api/generate"} or payload.get("model") in {self.server.config.get("vision_model"),self.server.config.get("multimodal_model")} or payload.get("model")==SAMPLED_MODEL or has_images(payload):
                return self.vision(payload)
            if payload.get("model")=="qwen3.8:27b":payload["model"]="qwen3.8-27b"
            body=json.dumps(payload).encode()
            key=self.headers.get("X-LLMRig-Affinity","")[:256]
            index=self.server.pool.acquire(key)
            conn=http.client.HTTPConnection("127.0.0.1",self.server.pool.ports[index],timeout=10)
            conn.connect();conn.sock.settimeout(7200)
            conn.request("POST",self.path,body,headers={"Authorization":self.server.auth,"Content-Type":"application/json"})
            response=conn.getresponse();self.send_response(response.status)
            for k,v in response.getheaders():
                if k.lower() not in HOP:self.send_header(k,v)
            self.send_header("Connection","close");self.send_header("X-LLMRig-Lane",str(index));self.end_headers();started=True;self.close_connection=True
            while chunk:=response.read1(65536):self.wfile.write(chunk);self.wfile.flush()
            LOG.info("lane=%s status=%s elapsed=%.3f",index,response.status,time.monotonic()-t0)
        except (ValueError,TypeError) as e:
            self.close_connection=True
            if not started:self.reply(400,{"error":str(e)})
        except (OSError,http.client.HTTPException,TimeoutError,subprocess.SubprocessError) as e:
            self.close_connection=True
            if index is not None:self.server.pool.set_health(index,False)
            if not started:
                try:self.reply(503,{"error":"Local Elpis request failed; not replayed","type":type(e).__name__})
                except OSError:pass
            LOG.warning("lane=%s transport=%s",index,type(e).__name__)
        finally:
            if conn:conn.close()
            if index is not None:self.server.pool.release(index)
            self.server.inflight.release()

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
    server=Server(json.loads(Path(os.environ.get("ELPIS_ROUTER_CONFIG",str(Path(__file__).with_name("router.json")))).read_text()))
    aliases=[]
    for port in server.config.get("alias_ports",[]):
        alias=ThreadingHTTPServer(("127.0.0.1",port),Handler)
        alias.daemon_threads=True
        alias.pool=server.pool;alias.config=server.config;alias.auth=server.auth;alias.inflight=server.inflight
        aliases.append(alias)
        threading.Thread(target=alias.serve_forever,daemon=True).start()
    threading.Thread(target=server.probe,daemon=True).start()
    def stop(*_):
        server.stop.set();threading.Thread(target=server.shutdown,daemon=True).start()
        for alias in aliases:threading.Thread(target=alias.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    server.serve_forever()
