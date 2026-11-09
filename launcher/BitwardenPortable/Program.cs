// Copyright 2026 Community Bitwarden PortableApps Builder contributors.
// MIT licensed launcher. Does not replace or modify Bitwarden itself.
// Security rule: never delete unverified host content, registry branches, or installed profiles.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Win32;
using System.Runtime.InteropServices;

namespace BitwardenPortableCommunity;

public sealed class Journal
{
    public string Root { get; set; } = "";
    public string CreatedUtc { get; set; } = "";
    public List<RegistrySnapshot> Entries { get; set; } = new();
}
public sealed class RegistrySnapshot
{
    public string Key { get; set; } = "";
    public string ValueName { get; set; } = "";
    public bool Existed { get; set; }
    public string? Value { get; set; }
    public string Kind { get; set; } = "";
}
[JsonSerializable(typeof(Journal))]
internal partial class JournalJsonContext : JsonSerializerContext { }

internal static class Program
{
    static readonly (string Key,string ValueName)[] OwnedCandidates =
    {
        (@"SOFTWARE\Mozilla\NativeMessagingHosts\com.8bit.bitwarden", ""),
        (@"SOFTWARE\Google\Chrome\NativeMessagingHosts\com.8bit.bitwarden", ""),
        (@"SOFTWARE\Chromium\NativeMessagingHosts\com.8bit.bitwarden", ""),
        (@"SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.8bit.bitwarden", ""),
        (@"SOFTWARE\Vivaldi\NativeMessagingHosts\com.8bit.bitwarden", ""),
        (@"SOFTWARE\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.8bit.bitwarden", ""),
        (@"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Bitwarden"),
    };

    [STAThread]
    private static int Main(string[] args)
    {
        var root = Path.GetFullPath(AppContext.BaseDirectory);
        var data = Path.Combine(root, "Data");
        var profile = Path.Combine(data, "Profile");
        var temp = Path.Combine(data, "Temp");
        var trace = Path.Combine(data, "TraceGuard");
        var appDir = Path.Combine(root, "App", "Bitwarden");
        var realExe = Path.Combine(appDir, "Bitwarden.exe");
        var pending = Path.Combine(trace, "shellguard-pending.json");
        var log = Path.Combine(trace, "launcher.log");
        try
        {
            if (args.Length == 1 && args[0] == "--self-test")
            {
                if (Path.GetFullPath(realExe) != Path.Combine(root, "App", "Bitwarden", "Bitwarden.exe")) return 12;
                if (!profile.StartsWith(root, StringComparison.OrdinalIgnoreCase)) return 13;
                Console.WriteLine("PORTABLE-LAUNCHER-SELFTEST-PASS");
                return 0;
            }
            // Prevent writes to host locations through swapped Data junction/symlink.
            foreach (string dir in new [] { data, profile, temp, trace })
            {
                if (Directory.Exists(dir) && (File.GetAttributes(dir) & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("Refusing to use a reparse-point Data folder: " + dir);
            }
            Directory.CreateDirectory(profile);
            Directory.CreateDirectory(temp);
            Directory.CreateDirectory(trace);
            if (!File.Exists(realExe)) throw new FileNotFoundException("Verified staged Bitwarden.exe missing", realExe);

            string key = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(root.ToUpperInvariant())))[..24];
            using var mutex = new Mutex(false, @"Local\BitwardenPortable_" + key);
            bool ownsLock;
            try { ownsLock = mutex.WaitOne(0); }
            catch (AbandonedMutexException) { ownsLock = true; }
            if (!ownsLock)
            {
                Message("Portable Bitwarden is already running from this folder. Close it from the tray before upgrading.");
                return 4;
            }
            try
            {
                // A killed launcher may leave the previous journal. Reconcile carefully first.
                if (File.Exists(pending))
                {
                    WriteLog(log, "Previous session journal exists; attempting conservative recovery");
                    CloseJournal(pending, root, trace, log);
                }
                var journal = Capture(root);
                SaveJournal(pending, journal);
                int result = 1;
                try
                {
                    var psi = new ProcessStartInfo(realExe) { UseShellExecute = false, WorkingDirectory = appDir };
                    foreach (var arg in args) psi.ArgumentList.Add(arg);
                    // Supported Bitwarden source-level preference overrides prior to Electron startup.
                    psi.Environment["BITWARDEN_APPDATA_DIR"] = profile;
                    psi.Environment["PORTABLE_EXECUTABLE_DIR"] = root;
                    psi.Environment["BITWARDEN_NO_UPDATER"] = "1";
                    psi.Environment["ELECTRON_NO_UPDATER"] = "1";
                    // Scoped to child process and descendants only; no global Windows TEMP changes.
                    psi.Environment["TEMP"] = temp;
                    psi.Environment["TMP"] = temp;
                    WriteLog(log, "Launching official unpacked Bitwarden desktop; launcher waiting for main process");
                    using var child = Process.Start(psi) ?? throw new IOException("Process.Start returned null");
                    child.WaitForExit(); // Standard Electron main process stays alive while its tray operates.
                    result = child.ExitCode;
                    WriteLog(log, "Main application returned exit code " + result);
                }
                finally { CloseJournal(pending, root, trace, log); }
                return result;
            }
            finally { mutex.ReleaseMutex(); }
        }
        catch (Exception ex)
        {
            try
            {
                // Never write into a suspicious redirected Data tree while reporting an error.
                if ((!Directory.Exists(data) || (File.GetAttributes(data) & FileAttributes.ReparsePoint)==0) &&
                    (!Directory.Exists(trace) || (File.GetAttributes(trace) & FileAttributes.ReparsePoint)==0))
                { Directory.CreateDirectory(trace); WriteLog(log, "ERROR: " + ex.Message); }
            } catch { }
            Message("Bitwarden Portable launcher error:\n" + ex.Message + "\n\nSee Data\\TraceGuard\\launcher.log");
            return 2;
        }
    }

    [DllImport("user32.dll", EntryPoint="MessageBoxW", CharSet=CharSet.Unicode)]
    private static extern int MessageBox(IntPtr hWnd,string text,string caption,uint type);
    static void Message(string txt)
    {
        MessageBox(IntPtr.Zero,txt,"Bitwarden Portable (Community)",0x10);
    }

    static void WriteLog(string file, string s)
    {
        File.AppendAllText(file, $"{DateTime.UtcNow:O} {s}{Environment.NewLine}", Encoding.UTF8);
    }

    static RegistrySnapshot Read(string key,string name)
    {
        using var k = Registry.CurrentUser.OpenSubKey(key, writable:false);
        var value = k?.GetValue(name, null, RegistryValueOptions.DoNotExpandEnvironmentNames);
        if (value is null) return new() { Key=key, ValueName=name, Existed=false };
        RegistryValueKind kind=k!.GetValueKind(name);
        // Don't read binary or arbitrary registry data; this code only manages string locations.
        if (kind != RegistryValueKind.String && kind != RegistryValueKind.ExpandString)
            return new() { Key=key, ValueName=name, Existed=true, Value=null, Kind="unsupported" };
        return new() { Key=key, ValueName=name, Existed=true, Value=(string)value, Kind=kind.ToString() };
    }
    static Journal Capture(string root)
    {
        var j=new Journal { Root=root, CreatedUtc=DateTime.UtcNow.ToString("O") };
        foreach (var entry in OwnedCandidates) j.Entries.Add(Read(entry.Key, entry.ValueName));
        return j;
    }
    static void SaveJournal(string file, Journal j)
    {
        string temp=file+".new";
        File.WriteAllText(temp,JsonSerializer.Serialize(j,JournalJsonContext.Default.Journal),Encoding.UTF8);
        File.Move(temp,file,true);
    }
    static bool Owned(string value, string root)
    {
        // Values can be quoted commands or absolute manifest paths. Check only package-owned roots.
        string canonical=root.TrimEnd(Path.DirectorySeparatorChar);
        return value.Contains(canonical+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) ||
               value.Contains('"'+canonical+'"',StringComparison.OrdinalIgnoreCase);
    }
    static void CloseJournal(string file,string root,string trace,string log)
    {
        if (!File.Exists(file)) return;
        Journal? j;
        try { j=JsonSerializer.Deserialize(File.ReadAllText(file,Encoding.UTF8),JournalJsonContext.Default.Journal); }
        catch (Exception e) { WriteLog(log,"Unparseable recovery journal retained: "+e.Message); return; }
        if (j is null || !Path.GetFullPath(j.Root).Equals(root,StringComparison.OrdinalIgnoreCase))
        { WriteLog(log,"Recovery journal belongs to another root; retained for manual review"); return; }
        foreach (var before in j.Entries)
        {
            try
            {
                var now=Read(before.Key,before.ValueName);
                if (before.Kind=="unsupported" || now.Kind=="unsupported")
                { WriteLog(log,"Non-string registry value preserved: "+before.Key); continue; }
                if (before.Existed==now.Existed && before.Value==now.Value) continue;
                if (before.Existed && !now.Existed)
                {
                    // Upstream setLoginItemSettings(false) can erase installed app's existing entry.
                    using var restore=Registry.CurrentUser.CreateSubKey(before.Key);
                    restore?.SetValue(before.ValueName,before.Value!,before.Kind=="ExpandString" ? RegistryValueKind.ExpandString : RegistryValueKind.String);
                    WriteLog(log,"Restored pre-existing missing registry value: "+before.Key);
                }
                else if (before.Existed && now.Existed && now.Value is not null && Owned(now.Value,root))
                {
                    using var restore=Registry.CurrentUser.CreateSubKey(before.Key);
                    restore?.SetValue(before.ValueName,before.Value!,before.Kind=="ExpandString" ? RegistryValueKind.ExpandString : RegistryValueKind.String);
                    WriteLog(log,"Restored pre-existing value after portable override: "+before.Key);
                }
                else if (!before.Existed && now.Existed && now.Value is not null && Owned(now.Value,root))
                {
                    // Save a recoverable text receipt BEFORE removing only proven package-owned values.
                    string rec=Path.Combine(trace,"Recovered","Registry");
                    Directory.CreateDirectory(rec);
                    var fileName=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(before.Key+"/"+before.ValueName)))[..16]+".txt";
                    File.WriteAllText(Path.Combine(rec,fileName),before.Key+"\n"+before.ValueName+"\n"+now.Value+"\n",Encoding.UTF8);
                    using (var ownedKey=Registry.CurrentUser.OpenSubKey(before.Key,writable:true))
                    { ownedKey?.DeleteValue(before.ValueName,throwOnMissingValue:false); }
                    if (before.ValueName=="")
                    {
                        // Leaf removal only if it is now absolutely empty, never parent trees.
                        using var check=Registry.CurrentUser.OpenSubKey(before.Key);
                        bool empty=check is not null && check.ValueCount==0 && check.SubKeyCount==0;
                        if (empty) Registry.CurrentUser.DeleteSubKey(before.Key,throwOnMissingSubKey:false);
                    }
                    WriteLog(log,"Recovered and removed newly created owned registry value: "+before.Key);
                }
                else
                {
                    WriteLog(log,"AMBIGUOUS external registry change preserved: "+before.Key);
                }
            }
            catch (Exception e) { WriteLog(log,"Registry item NOT modified after failure: "+before.Key+": "+e.Message); }
        }
        // Do not destroy source evidence if failures/uncertainty exist; archive the journal.
        string history=Path.Combine(trace,"History"); Directory.CreateDirectory(history);
        string archive=Path.Combine(history,"shellguard-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff")+".json");
        File.Move(file,archive);
    }
}
