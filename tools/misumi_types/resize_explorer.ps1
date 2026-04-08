Add-Type @"
using System;
using System.Runtime.InteropServices;

public class WinAPI {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    public static void ResizeExplorer() {
        IntPtr hWnd = FindWindow("CabinetWClass", null);
        if (hWnd != IntPtr.Zero) {
            MoveWindow(hWnd, 100, 100, 800, 600, true);
        } else {
            Console.WriteLine("Explorer window not found.");
        }
    }
}
"@

[WinAPI]::ResizeExplorer()
