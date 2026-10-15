using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal static class Program
{
    internal const int Port = 18766;
    internal const string Home = "http://127.0.0.1:18766/";
    internal const string Marker = "stray-diary-local-v1";

    [STAThread]
    private static void Main(string[] args)
    {
        bool openBrowser = Array.IndexOf(args, "--no-browser") < 0;
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        try
        {
            using (var client = new WebClient())
            {
                client.Proxy = null;
                if (client.DownloadString(Home + "health") == Marker)
                {
                    if (openBrowser) OpenGame();
                    return;
                }
            }
        }
        catch (WebException) { }
        try { Application.Run(new PortContext(openBrowser)); }
        catch (Exception error)
        {
            MessageBox.Show("无法启动流浪日记电脑版：\n" + error.Message,
                            "流浪日记", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    internal static void OpenGame()
    {
        Process.Start(new ProcessStartInfo(Home) { UseShellExecute = true });
    }
}

internal sealed class PortContext : ApplicationContext
{
    private readonly TcpListener listener;
    private readonly NotifyIcon tray;
    private readonly string root;
    private volatile bool stopping;

    internal PortContext(bool openBrowser)
    {
        root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "web")) + Path.DirectorySeparatorChar;
        if (!File.Exists(Path.Combine(root, "index.html"))) throw new FileNotFoundException("缺少 web 游戏文件夹，请先完整解压电脑版。");
        listener = new TcpListener(IPAddress.Loopback, Program.Port);
        listener.Start();
        var menu = new ContextMenuStrip();
        menu.Items.Add("打开游戏", null, delegate { Program.OpenGame(); });
        menu.Items.Add("退出电脑版", null, delegate { ExitThread(); });
        tray = new NotifyIcon();
        tray.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        tray.Text = "流浪日记电脑版";
        tray.ContextMenuStrip = menu;
        tray.DoubleClick += delegate { Program.OpenGame(); };
        tray.Visible = true;
        Task.Run((Action)AcceptLoop);
        if (openBrowser) Program.OpenGame();
    }

    private void AcceptLoop()
    {
        while (!stopping)
        {
            try
            {
                TcpClient client = listener.AcceptTcpClient();
                ThreadPool.QueueUserWorkItem(delegate { Serve(client); });
            }
            catch (SocketException) { if (!stopping) Thread.Sleep(100); }
            catch (ObjectDisposedException) { break; }
        }
    }

    private void Serve(TcpClient client)
    {
        using (client)
        {
            try
            {
                client.ReceiveTimeout = 5000;
                client.SendTimeout = 10000;
                using (NetworkStream stream = client.GetStream())
                {
                    var header = new StringBuilder();
                    int value;
                    while (header.Length < 16384 && (value = stream.ReadByte()) != -1)
                    {
                        header.Append((char)value);
                        if (header.Length >= 4 && header.ToString(header.Length - 4, 4) == "\r\n\r\n") break;
                    }
                    string[] request = header.ToString().Split(new[] { "\r\n" }, StringSplitOptions.None)[0].Split(' ');
                    if (request.Length != 3 || (request[0] != "GET" && request[0] != "HEAD"))
                    {
                        Respond(stream, 400, "text/plain", Encoding.UTF8.GetBytes("Bad request"), false);
                        return;
                    }
                    string uri = Uri.UnescapeDataString(request[1].Split('?')[0]);
                    if (uri == "/health")
                    {
                        Respond(stream, 200, "text/plain", Encoding.UTF8.GetBytes(Program.Marker), request[0] == "HEAD");
                        return;
                    }
                    if (uri == "/") uri = "/index.html";
                    string file = Path.GetFullPath(Path.Combine(root, uri.TrimStart('/').Replace('/', Path.DirectorySeparatorChar)));
                    if (!file.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(file))
                    {
                        Respond(stream, 404, "text/plain", Encoding.UTF8.GetBytes("Not found"), false);
                        return;
                    }
                    Respond(stream, 200, Mime(file), File.ReadAllBytes(file), request[0] == "HEAD");
                }
            }
            catch (IOException) { }
            catch (ArgumentException) { }
            catch (UnauthorizedAccessException) { }
            catch (FormatException) { }
        }
    }

    private static string Mime(string file)
    {
        switch (Path.GetExtension(file).ToLowerInvariant())
        {
            case ".html": return "text/html; charset=utf-8";
            case ".js": return "application/javascript; charset=utf-8";
            case ".json": return "application/json; charset=utf-8";
            case ".css": return "text/css; charset=utf-8";
            case ".png": return "image/png";
            case ".jpg": case ".jpeg": return "image/jpeg";
            case ".mp3": return "audio/mpeg";
            case ".ogg": return "audio/ogg";
            default: return "application/octet-stream";
        }
    }

    private static void Respond(Stream stream, int status, string mime, byte[] data, bool head)
    {
        string reason = status == 200 ? "OK" : status == 404 ? "Not Found" : "Bad Request";
        byte[] headers = Encoding.ASCII.GetBytes("HTTP/1.1 " + status + " " + reason + "\r\nContent-Type: " + mime +
            "\r\nContent-Length: " + data.Length + "\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n");
        stream.Write(headers, 0, headers.Length);
        if (!head) stream.Write(data, 0, data.Length);
    }

    protected override void ExitThreadCore()
    {
        stopping = true;
        listener.Stop();
        tray.Visible = false;
        tray.Dispose();
        base.ExitThreadCore();
    }
}
