using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

namespace LocalizationInstaller {
 public sealed class Settings {
  public string title,subtitle,archive_file,executable_file,backup_folder,notice,footer,build_label,supported_builds,version;
 }
 public sealed class PayloadFile {
  public string name,source_sha256,target_sha256,resource;
  public long source_size,target_size;
 }
 public sealed class Payload {
  public int schema; public string format; public Settings settings; public PayloadFile[] files;
  [System.Text.Json.Serialization.JsonIgnore] public Settings Settings {get=>settings;set=>settings=value;}
  [System.Text.Json.Serialization.JsonIgnore] public Func<string,Stream> OpenResource;
  public static Payload Load() {
   var assembly=Assembly.GetExecutingAssembly();
   using var stream=assembly.GetManifestResourceStream("payload.manifest.json") ?? throw new InvalidDataException("Missing payload manifest");
   if(stream.Length>1024*1024) throw new InvalidDataException("Manifest too large");
   var p=JsonSerializer.Deserialize<Payload>(stream,new JsonSerializerOptions {IncludeFields=true}) ?? throw new InvalidDataException("Invalid manifest");
   p.OpenResource=name=>assembly.GetManifestResourceStream(name) ?? throw new InvalidDataException("Missing payload: "+name);
   return p;
  }
 }
 public sealed class Component {
  public string Path,Backup,Current; public PayloadFile File;
  public bool IsInstalled=>Current==File.target_sha256;
 }
 public sealed class Inspection {
  public readonly List<Component> Components=new List<Component>();
  public bool CanInstall=>Components.Any(c=>!c.IsInstalled);
  public bool CanRestore=>Components.Any(c=>c.IsInstalled);
  public string Summary=>CanRestore?"已安装本版汉化，原版备份已验证":"原版文件验证通过，可以安装";
 }
 public sealed class Engine {
  readonly Payload payload; readonly Action<string,int> progress;
  internal Action<int> BeforeReplace=null;
  public Engine(Payload data,Action<string,int> report=null) {
   payload=data;progress=report ?? ((s,n)=>{});
   if(data==null || data.schema!=1 || data.format!="source-copy-add-v1" || data.Settings==null || data.files==null || data.files.Length!=2 || data.OpenResource==null) throw new InvalidDataException("Invalid payload metadata");
   var s=data.Settings;
   foreach(var name in new[]{s.archive_file,s.executable_file,s.backup_folder}) ValidName(name);
   if(new[]{s.archive_file,s.executable_file,s.backup_folder}.Distinct(StringComparer.OrdinalIgnoreCase).Count()!=3) throw new InvalidDataException("Duplicate payload paths");
   if(!data.files.Select(f=>f.name).OrderBy(x=>x).SequenceEqual(new[]{s.archive_file,s.executable_file}.OrderBy(x=>x))) throw new InvalidDataException("Unexpected payload files");
   foreach(var f in data.files) {
    ValidName(f.name);ValidName(f.resource);
    if(f.source_size<=0 || f.target_size<=0 || f.source_sha256==f.target_sha256) throw new InvalidDataException("Invalid payload sizes");
    foreach(var hash in new[]{f.source_sha256,f.target_sha256}) if(hash==null || hash.Length!=64 || hash.Any(c=>!"0123456789abcdef".Contains(c))) throw new InvalidDataException("Invalid payload hash");
   }
  }
  static void ValidName(string name) {
   if(String.IsNullOrWhiteSpace(name) || name=="." || name==".." || name.EndsWith(".") || name.EndsWith(" ") || name.IndexOfAny(new[]{'/','\\',':','\0','*','?','"','<','>','|'})>=0 || Path.GetFileName(name)!=name) throw new InvalidDataException("Invalid payload path");
  }
  [StructLayout(LayoutKind.Sequential)] struct FileInformation {
   public uint Attributes;public System.Runtime.InteropServices.ComTypes.FILETIME Creation,Access,Write;
   public uint Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;
  }
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle handle,out FileInformation info);
  static void CheckPath(string path) {
   string full=Path.GetFullPath(path);
   for(string p=full;!String.IsNullOrEmpty(p);p=Path.GetDirectoryName(p)) {
    try { if((File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0) throw new IOException("拒绝链接路径："+p); }
    catch(FileNotFoundException) {} catch(DirectoryNotFoundException) {}
    if(p==Path.GetPathRoot(p))break;
   }
   if(File.Exists(full)) {
    using var f=new FileStream(full,FileMode.Open,FileAccess.Read,FileShare.Read);
    if(OperatingSystem.IsWindows()) {
     if(!GetFileInformationByHandle(f.SafeFileHandle,out var info)) throw new IOException("读取文件身份失败");
     if(info.Links!=1) throw new IOException("拒绝硬链接文件："+full);
    }
   }
  }
  public static string Hash(string path) {
   using var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read,1024*1024,FileOptions.SequentialScan);
   return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();
  }
  static bool Matches(string path,long size,string sha) {
   CheckPath(path);return File.Exists(path)&&new FileInfo(path).Length==size&&Hash(path)==sha;
  }
  string Selected(string selected) {
   string path=Path.GetFullPath(selected);
   if(!String.Equals(Path.GetFileName(path),payload.Settings.archive_file,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("请选择 "+payload.Settings.archive_file);
   CheckPath(path);return path;
  }
  public Inspection Inspect(string selected,bool includeExe=true) {
   string path=Selected(selected),dir=Path.GetDirectoryName(path),cache=Path.Combine(dir,payload.Settings.backup_folder);
   if(!includeExe)throw new InvalidDataException("本版安装器要求同时处理资源及运行程序");
   CheckPath(cache);var result=new Inspection();
   foreach(var f in payload.files) {
    // Verify both components even in archive-only mode: unknown executables must never be silently accepted.
    string current=Path.Combine(dir,f.name),backup=Path.Combine(cache,f.name);
    progress("正在校验 "+f.name,10);
    CheckPath(current);CheckPath(backup);
    if(!File.Exists(current)) throw new FileNotFoundException("未找到 "+f.name);
    string hash=Hash(current);long size=new FileInfo(current).Length;
    bool original=size==f.source_size&&hash==f.source_sha256,installed=size==f.target_size&&hash==f.target_sha256;
    if(!original&&!installed) throw new InvalidDataException("文件版本不匹配，未作修改："+f.name+"；仅支持 "+payload.Settings.build_label);
    if(File.Exists(backup)&&!Matches(backup,f.source_size,f.source_sha256)) throw new InvalidDataException("原版备份校验失败："+f.name);
    if(installed&&!File.Exists(backup)) throw new InvalidDataException("汉化文件缺少有效原版备份："+f.name);
    if(f.name==payload.Settings.archive_file||includeExe) result.Components.Add(new Component {Path=current,Backup=backup,Current=hash,File=f});
   }
   if(result.Components.Any(c=>c.IsInstalled)&&result.Components.Any(c=>!c.IsInstalled)) throw new InvalidDataException("检测到混合文件状态，请先恢复与文件匹配的完整版本");
   return result;
  }
  public string Operate(string selected,bool includeExe,bool restore) {
   var inspection=Inspect(selected,includeExe);
   if(restore?!inspection.CanRestore:!inspection.CanInstall) return restore?"ALREADY_RESTORED":"ALREADY_INSTALLED";
   string dir=Path.GetDirectoryName(Selected(selected)),cache=Path.Combine(dir,payload.Settings.backup_folder);
   long required=64L*1024*1024+inspection.Components.Sum(c=>restore?c.File.source_size:c.File.source_size+c.File.target_size);
   if(new DriveInfo(Path.GetPathRoot(dir)).AvailableFreeSpace<required)throw new IOException("可用空间不足");
   Directory.CreateDirectory(cache);CheckPath(cache);
   string lockPath=Path.Combine(cache,"operation.lock");CheckPath(lockPath);
   if(File.Exists(lockPath)) throw new IOException("存在未清理的事务锁，请检查后重试");
   var staged=new Dictionary<Component,string>();var prior=new Dictionary<Component,string>();var committed=new List<Component>();
   bool success=false,rollbackFailed=false;
   using(var gate=new FileStream(lockPath,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None,1,FileOptions.DeleteOnClose)) {
    inspection=Inspect(selected,includeExe);string token=Guid.NewGuid().ToString("N");
    try {
     foreach(var c in inspection.Components) {
      if(!restore&&!File.Exists(c.Backup)) {
       string temp=Path.Combine(cache,"backup-"+token+"-"+c.File.name);staged[c]=temp;
       File.Copy(c.Path,temp,false);
       if(!Matches(temp,c.File.source_size,c.File.source_sha256))throw new IOException("备份校验失败");
       File.Move(temp,c.Backup);staged.Remove(c);
      }
      if(!Matches(c.Backup,c.File.source_size,c.File.source_sha256))throw new IOException("原版备份发生变化");
      string stage=Path.Combine(cache,"stage-"+token+"-"+c.File.name);staged[c]=stage;
      if(restore)File.Copy(c.Backup,stage,false);else Apply(c.Backup,stage,c.File,payload.OpenResource);
      if(!Matches(stage,restore?c.File.source_size:c.File.target_size,restore?c.File.source_sha256:c.File.target_sha256))throw new IOException("临时输出校验失败");
     }
     if(inspection.Components.Any(c=>!Matches(c.Path,c.IsInstalled?c.File.target_size:c.File.source_size,c.Current)))throw new IOException("操作过程中源文件发生变化");
     int index=0;
     foreach(var c in inspection.Components) {
      BeforeReplace?.Invoke(index++);CheckPath(cache);
      if(!Matches(c.Path,c.IsInstalled?c.File.target_size:c.File.source_size,c.Current))throw new IOException("提交前文件发生变化");
      if(!Matches(c.Backup,c.File.source_size,c.File.source_sha256))throw new IOException("提交前备份发生变化");
      string rollback=Path.Combine(cache,"transaction-"+token+"-"+c.File.name);prior[c]=rollback;
      File.Replace(staged[c],c.Path,rollback,true);committed.Add(c);
      if(!Matches(rollback,c.IsInstalled?c.File.target_size:c.File.source_size,c.Current))throw new IOException("替换时源文件发生变化");
      if(!Matches(c.Path,restore?c.File.source_size:c.File.target_size,restore?c.File.source_sha256:c.File.target_sha256))throw new IOException("写入后校验失败");
     }
     success=true;
    } catch(Exception original) {
     var errors=new List<Exception>();
     foreach(var c in committed.AsEnumerable().Reverse())try {
      CheckPath(c.Path);CheckPath(prior[c]);File.Replace(prior[c],c.Path,null,true);
      if(!Matches(c.Path,c.IsInstalled?c.File.target_size:c.File.source_size,c.Current))throw new IOException("事务恢复哈希不符");
     }catch(Exception ex){rollbackFailed=true;errors.Add(ex);}
     if(errors.Count>0)throw new AggregateException("事务恢复失败，保留原版备份及事务文件",new[]{original}.Concat(errors));
     throw;
    } finally {
     foreach(string temp in staged.Values.Concat(rollbackFailed?Array.Empty<string>():prior.Values))if(File.Exists(temp)) {CheckPath(temp);File.Delete(temp);}
    }
   }
   if(success&&restore) {
    // Delete only validated, known backup files; retain unknown files and directories.
    foreach(var c in inspection.Components)if(Matches(c.Path,c.File.source_size,c.File.source_sha256)&&Matches(c.Backup,c.File.source_size,c.File.source_sha256))File.Delete(c.Backup);
    if(!Directory.EnumerateFileSystemEntries(cache).Any())Directory.Delete(cache,false);
   }
   progress(restore?"原版恢复完成":"汉化安装完成",100);return restore?"RESTORED":"INSTALLED";
  }
  public static void Apply(string source,string target,PayloadFile file,Func<string,Stream> openResource) {
   if(!Matches(source,file.source_size,file.source_sha256))throw new InvalidDataException("差分源身份不符");
   using var input=new FileStream(source,FileMode.Open,FileAccess.Read,FileShare.Read);
   using var raw=openResource(file.resource);
   using var gz=new GZipStream(raw,CompressionMode.Decompress);
   using var reader=new BinaryReader(gz,Encoding.ASCII,true);
   if(!reader.ReadBytes(8).SequenceEqual(Encoding.ASCII.GetBytes("LOCDLT1\0")))throw new InvalidDataException("差分头错误");
   using(var output=new FileStream(target,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
    var buffer=new byte[1024*1024];long written=0;long commands=0;
    while(true) {
     if(++commands>10000000)throw new InvalidDataException("差分命令过多");
     int op=reader.ReadByte();if(op==0)break;
     long count;
     if(op==1) {
      ulong offset=reader.ReadUInt64(),length=reader.ReadUInt64();
      if(offset>(ulong)file.source_size||length>(ulong)file.source_size-offset)throw new InvalidDataException("差分复制越界");
      input.Position=(long)offset;count=(long)length;
     }else if(op==2)count=reader.ReadUInt32();else throw new InvalidDataException("未知差分命令");
     if(count<=0||count>file.target_size-written)throw new InvalidDataException("差分输出越界");
     long remain=count;Stream src=op==1?input:gz;
     while(remain>0) {int n=src.Read(buffer,0,(int)Math.Min(buffer.Length,remain));if(n==0)throw new EndOfStreamException("差分数据被截断");output.Write(buffer,0,n);remain-=n;}
     written+=count;
    }
    if(written!=file.target_size||gz.ReadByte()!=-1)throw new InvalidDataException("差分长度或结束标记错误");
    output.Flush(true);
   }
   if(!Matches(target,file.target_size,file.target_sha256))throw new InvalidDataException("差分输出 SHA-256 不符");
  }
 }
}
