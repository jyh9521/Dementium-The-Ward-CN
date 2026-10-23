using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using LocalizationInstaller;

static class InstallerTests {
 static int passed;
 static void Check(bool ok,string name) {if(!ok)throw new Exception("FAIL: "+name);passed++;Console.WriteLine("PASS: "+name);}
 static void Reject(Action action,string name) {try{action();}catch(Exception ex) when(ex is InvalidDataException||ex is IOException||ex is InvalidOperationException||ex is ArgumentException){Check(true,name);return;}throw new Exception("FAIL no rejection: "+name);}
 static string Sha(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static byte[] Delta(byte[] source,byte[] target,int variant=0) {
  using var data=new MemoryStream();
  using(var gz=new GZipStream(data,CompressionLevel.Optimal,true))using(var w=new BinaryWriter(gz,Encoding.ASCII,true)) {
   w.Write(Encoding.ASCII.GetBytes("LOCDLT1\0"));
   if(variant==1){w.Write((byte)1);w.Write((ulong)source.Length);w.Write((ulong)1);}
   else if(variant==2){w.Write((byte)9);}
   else if(variant==3){w.Write((byte)2);w.Write((uint)target.Length+1);w.Write(target);}
   else if(variant==4){w.Write((byte)2);w.Write((uint)target.Length);w.Write(target.Take(target.Length-1).ToArray());return data.ToArray();}
   else {
    int same=0;while(same<Math.Min(source.Length,target.Length)&&source[same]==target[same])same++;
    if(same>0){w.Write((byte)1);w.Write((ulong)0);w.Write((ulong)same);}
    if(same<target.Length){w.Write((byte)2);w.Write((uint)(target.Length-same));w.Write(target,same,target.Length-same);}
   }
   w.Write((byte)0);if(variant==5)w.Write((byte)42);
  }
  return data.ToArray();
 }
 sealed class Fixture:IDisposable {
  public string Dir=Path.Combine(Path.GetTempPath(),"localization-installer-tests-"+Guid.NewGuid().ToString("N"));
  public byte[] A=Encoding.UTF8.GetBytes("ARCHIVE original abcdefghijklmnopqrstuvwxyz"),B=Encoding.UTF8.GetBytes("EXECUTABLE original abcdefghijklmnopqrstuvwxyz");
  public byte[] At=Encoding.UTF8.GetBytes("ARCHIVE 中文资源 modified extra bytes"),Bt=Encoding.UTF8.GetBytes("EXECUTABLE 中文运行时 modified");
  public Payload Payload;public Dictionary<string,byte[]> Resources=new();public Engine Engine; public string Rom=>Path.Combine(Dir,"rom.zar");public string Exe=>Path.Combine(Dir,"Dementium.exe");public string Cache=>Path.Combine(Dir,".localization-backup");
  public Fixture() {
   Directory.CreateDirectory(Dir);File.WriteAllBytes(Rom,A);File.WriteAllBytes(Exe,B);
   Resources["rom.delta.gz"]=Delta(A,At);Resources["exe.delta.gz"]=Delta(B,Bt);
   Payload=new Payload {schema=1,format="source-copy-add-v1",Settings=new Settings {archive_file="rom.zar",executable_file="Dementium.exe",backup_folder=".localization-backup",build_label="fixture"},files=new[]{
    new PayloadFile {name="rom.zar",source_size=A.Length,source_sha256=Sha(A),target_size=At.Length,target_sha256=Sha(At),resource="rom.delta.gz"},
    new PayloadFile {name="Dementium.exe",source_size=B.Length,source_sha256=Sha(B),target_size=Bt.Length,target_sha256=Sha(Bt),resource="exe.delta.gz"}},OpenResource=n=>new MemoryStream(Resources[n],false)};
   Engine=new Engine(Payload);
  }
  public bool Original=>File.ReadAllBytes(Rom).SequenceEqual(A)&&File.ReadAllBytes(Exe).SequenceEqual(B);
  public bool Installed=>File.ReadAllBytes(Rom).SequenceEqual(At)&&File.ReadAllBytes(Exe).SequenceEqual(Bt);
  public void Dispose(){
   string full=Path.GetFullPath(Dir),root=Path.GetFullPath(Path.GetTempPath());
   if(Path.GetDirectoryName(full).TrimEnd(Path.DirectorySeparatorChar)!=root.TrimEnd(Path.DirectorySeparatorChar) ||
      !Path.GetFileName(full).StartsWith("localization-installer-tests-",StringComparison.Ordinal) ||
      (Directory.Exists(full)&&(File.GetAttributes(full)&FileAttributes.ReparsePoint)!=0))
    throw new IOException("Fixture cleanup target failed canonical-path validation");
   if(Directory.Exists(full))Directory.Delete(full,true);
  }
 }
 static void Main(string[] args) {
  using(var f=new Fixture()) {
   var i=f.Engine.Inspect(f.Rom);Check(i.CanInstall&&!i.CanRestore,"BASELINE original identity");
   File.WriteAllText(Path.Combine(f.Dir,"savegame.sav"),"PLAYER SAVE");File.WriteAllText(Path.Combine(f.Dir,"config.ini"),"PLAYER CONFIG");
   Check(f.Engine.Operate(f.Rom,true,false)=="INSTALLED"&&f.Installed,"MODIFIED two components installed");
   Check(f.Engine.Operate(f.Rom,true,false)=="ALREADY_INSTALLED","install idempotent");
   Check(f.Engine.Inspect(f.Rom).CanRestore,"installed backup validated");
   File.WriteAllText(Path.Combine(f.Cache,"user-note.txt"),"KEEP");Directory.CreateDirectory(Path.Combine(f.Cache,"user-folder"));
   Check(f.Engine.Operate(f.Rom,true,true)=="RESTORED"&&f.Original,"ROLLBACK original two hashes restored");
   Check(File.ReadAllText(Path.Combine(f.Cache,"user-note.txt"))=="KEEP"&&Directory.Exists(Path.Combine(f.Cache,"user-folder")),"restore preserves unknown backup content");
   Check(!File.Exists(Path.Combine(f.Cache,"rom.zar"))&&!File.Exists(Path.Combine(f.Cache,"Dementium.exe")),"restore removes only verified known backups");
   Check(File.ReadAllText(Path.Combine(f.Dir,"savegame.sav"))=="PLAYER SAVE"&&File.ReadAllText(Path.Combine(f.Dir,"config.ini"))=="PLAYER CONFIG","save/config unchanged");
   Check(f.Engine.Operate(f.Rom,true,true)=="ALREADY_RESTORED","restore idempotent");
  }
  using(var f=new Fixture()){f.Engine.Operate(f.Rom,true,false);f.Engine.Operate(f.Rom,true,true);Check(!Directory.Exists(f.Cache),"empty backup tree cleaned");}
  foreach(bool restoring in new[]{false,true})using(var f=new Fixture()) {
   if(restoring)f.Engine.Operate(f.Rom,true,false);
   f.Engine.BeforeReplace=n=>{if(n==1)throw new IOException("INJECTED transaction failure");};
   Reject(()=>f.Engine.Operate(f.Rom,true,restoring),restoring?"restore interruption rejected":"install interruption rejected");
   Check(restoring?f.Installed:f.Original,restoring?"failed restore rolls back both installed files":"failed install rolls back both originals");
   Check(f.Engine.Inspect(f.Rom).CanInstall==!restoring,"transaction rollback inspection consistent");
   Check(!Directory.EnumerateFiles(f.Cache).Any(p=>Path.GetFileName(p).StartsWith("transaction-")||Path.GetFileName(p).StartsWith("stage-")),"transaction temporary files cleaned");
  }
  using(var f=new Fixture()){File.AppendAllText(f.Exe,"drift");Reject(()=>f.Engine.Operate(f.Rom,true,false),"unknown executable version rejected");Check(File.ReadAllBytes(f.Rom).SequenceEqual(f.A),"unknown version leaves archive unchanged");}
  using(var f=new Fixture()){File.AppendAllText(f.Rom,"drift");Reject(()=>f.Engine.Inspect(f.Rom),"unknown archive version rejected");}
  using(var f=new Fixture()){f.Engine.Operate(f.Rom,true,false);File.WriteAllBytes(f.Exe,f.B);Reject(()=>f.Engine.Inspect(f.Rom),"mixed state rejected");}
  using(var f=new Fixture()){f.Engine.Operate(f.Rom,true,false);File.Delete(Path.Combine(f.Cache,"rom.zar"));Reject(()=>f.Engine.Inspect(f.Rom),"missing backup rejected");}
  using(var f=new Fixture()){Directory.CreateDirectory(f.Cache);File.WriteAllText(Path.Combine(f.Cache,"rom.zar"),"corrupt");Reject(()=>f.Engine.Operate(f.Rom,true,false),"corrupt backup rejected");Check(f.Original,"corrupt backup preserves originals");}
  using(var f=new Fixture()){Directory.CreateDirectory(f.Cache);File.WriteAllText(Path.Combine(f.Cache,"operation.lock"),"stale");Reject(()=>f.Engine.Operate(f.Rom,true,false),"stale operation lock rejected");Check(f.Original,"lock rejection preserves originals");}
  for(int variant=1;variant<=5;variant++)using(var f=new Fixture()) {
   f.Resources["rom.delta.gz"]=Delta(f.A,f.At,variant);
   Reject(()=>f.Engine.Operate(f.Rom,true,false),"malformed delta variant "+variant);Check(f.Original,"malformed delta preserves originals "+variant);
  }
  using(var f=new Fixture()){f.Resources["exe.delta.gz"]=Delta(f.B,Encoding.ASCII.GetBytes("WRONG HASH"));Reject(()=>f.Engine.Operate(f.Rom,true,false),"wrong output hash/size rejected");Check(f.Original,"all staging occurs before any replacement");}
  foreach(var name in new[]{"../escape","..\\escape","rom.zar:stream","ending.","ending ","C:\\escape"})using(var f=new Fixture()){f.Payload.Settings.backup_folder=name;Reject(()=>new Engine(f.Payload),"payload path attack rejected "+name);}
  using(var f=new Fixture()){f.Payload.files[0].target_sha256="bad";Reject(()=>new Engine(f.Payload),"invalid hash metadata rejected");}
  using(var f=new Fixture()){Reject(()=>f.Engine.Inspect(Path.Combine(f.Dir,"other.zar")),"wrong selected filename rejected");}
  if(OperatingSystem.IsWindows()) {
   using(var f=new Fixture()) {
    string linked=Path.Combine(f.Dir,"linked-original");File.Copy(f.Rom,linked);File.Delete(f.Rom);
    if(!CreateHardLink(f.Rom,linked,IntPtr.Zero))throw new IOException("Could not create fixture hardlink");
    Reject(()=>f.Engine.Inspect(f.Rom),"hardlinked archive rejected");
   }
   using(var f=new Fixture()) {
    string target=Path.Combine(f.Dir,"actual-backup");Directory.CreateDirectory(target);
    var process=System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("cmd.exe","/c mklink /J \""+f.Cache+"\" \""+target+"\"") {UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true});process.WaitForExit();
    if(process.ExitCode!=0)throw new IOException("Could not create fixture junction");
    Reject(()=>f.Engine.Operate(f.Rom,true,false),"junction backup path rejected");Directory.Delete(f.Cache);
   }
  }
  var tree=SteamLocator.Parse("\"libraryfolders\" { \"0\" { \"path\" \"C:\\\\Steam\" } }");Check(tree.Children[0].Children[0].Get("path")=="C:\\Steam","Steam VDF parser escapes");
  Reject(()=>SteamLocator.Parse("\"libraryfolders\" {"),"malformed Steam VDF rejected");Check(SteamLocator.AppId=="3909960","Steam game AppID identity");
  using(var f=new Fixture()) {
   string library=Path.Combine(f.Dir,"steam");string game=Path.Combine(library,"steamapps","common","Dementium");Directory.CreateDirectory(game);
   File.WriteAllText(Path.Combine(library,"steamapps","appmanifest_3909960.acf"),"\"AppState\" { \"appid\" \"3909960\" \"installdir\" \"Dementium\" }");File.WriteAllText(Path.Combine(game,"rom.zar"),"fixture");File.WriteAllText(Path.Combine(game,"Dementium.exe"),"fixture");
   Check(SteamLocator.Discover(new[]{library}).Single()==Path.Combine(game,"rom.zar"),"read-only Steam fixture detection");
   File.WriteAllText(Path.Combine(library,"steamapps","appmanifest_3909960.acf"),"\"AppState\" { \"appid\" \"3909960\" \"installdir\" \"../escape\" }");Check(SteamLocator.Discover(new[]{library}).Count==0,"Steam manifest traversal rejected");
  }
  if(args.Length==2&&args[0]=="--real") {
   var p=Payload.Load();var e=new Engine(p);string rom=Path.Combine(Path.GetFullPath(args[1]),p.Settings.archive_file);
   Check(e.Inspect(rom).CanInstall,"REAL BASELINE identities");Check(e.Operate(rom,true,false)=="INSTALLED","REAL MODIFIED install");Check(e.Operate(rom,true,false)=="ALREADY_INSTALLED","REAL idempotent install");Check(e.Operate(rom,true,true)=="RESTORED","REAL ROLLBACK restore");Check(e.Inspect(rom).CanInstall,"REAL restored original identities");
  }
  Console.WriteLine("INSTALLER_TESTS_PASSED="+passed);
 }
 [System.Runtime.InteropServices.DllImport("kernel32.dll",CharSet=System.Runtime.InteropServices.CharSet.Unicode,SetLastError=true)] static extern bool CreateHardLink(string path,string target,IntPtr unused);
}
