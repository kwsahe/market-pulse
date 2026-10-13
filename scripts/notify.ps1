# scripts/notify.ps1
# 배치 결과를 Windows 알림으로 띄운다.
#
# 왜 필요한가: 스케줄러가 무인으로 돌면 콘솔을 보는 사람이 없다. 종료코드는 만들었지만
# 그걸 읽는 주체가 없으면 실패가 그대로 묻힌다. 외부 서비스(healthchecks.io)는
# "PC가 꺼져 있던 날"까지 잡아주지만 계정이 필요하고, 이 알림은 계정 없이 즉시 동작한다.
# 둘은 서로 다른 실패를 담당하므로 같이 쓰는 게 맞다.
#
# 사용법:
#   powershell -ExecutionPolicy Bypass -File scripts/notify.ps1 -Title "..." -Message "..." -Level error

param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$Message,
    [ValidateSet('info', 'error')][string]$Level = 'info'
)

# Windows 10/11의 토스트 알림. COM/WinRT 경로가 막힌 환경(정책·세션 종류)에서는
# 예외가 나므로, 알림 실패가 배치 실패로 번지지 않도록 통째로 감싼다.
try {
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime]

    # 알림 센터에 남기려면 등록된 AppUserModelID가 필요하다. PowerShell 것을 빌려 쓴다.
    $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'

    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
        [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $texts = $template.GetElementsByTagName('text')
    $texts.Item(0).AppendChild($template.CreateTextNode($Title)) | Out-Null
    $texts.Item(1).AppendChild($template.CreateTextNode($Message)) | Out-Null

    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
    exit 0
} catch {
    # 토스트가 안 되면 최소한 이벤트 로그에는 남긴다 — 나중에 이벤트 뷰어로 확인할 수 있다.
    try {
        $src = 'MarketPulse'
        if (-not [System.Diagnostics.EventLog]::SourceExists($src)) {
            New-EventLog -LogName Application -Source $src -ErrorAction Stop
        }
        $type = if ($Level -eq 'error') { 'Error' } else { 'Information' }
        Write-EventLog -LogName Application -Source $src -EventId 1000 -EntryType $type -Message "$Title`n$Message"
    } catch {
        # 이벤트 로그 소스 생성은 관리자 권한이 필요할 수 있다. 여기까지 실패하면 조용히 포기한다 —
        # 알림을 못 띄운 것 때문에 수집 배치가 실패로 끝나면 본말이 전도된다.
    }
    exit 0
}
