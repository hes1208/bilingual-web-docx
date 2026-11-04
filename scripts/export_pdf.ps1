# Word COM：更新域与目录、重排、统计、导出 PDF
# 用法: pwsh scripts/export_pdf.ps1 -Src out.docx -Pdf preview.pdf
param(
    [Parameter(Mandatory = $true)][string]$Src,
    [Parameter(Mandatory = $true)][string]$Pdf
)

$ErrorActionPreference = 'Stop'
$Src = (Resolve-Path $Src).Path
if (Test-Path $Pdf) { Remove-Item $Pdf -Force }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $doc = $word.Documents.Open($Src, $false, $false)

    # 目录样式压紧：默认 TOC 1/2 行距过大，会把目录撑成多页
    foreach ($name in @('TOC 1', 'TOC 2', 'TOC 3')) {
        try {
            $s = $doc.Styles.Item($name)
            if ($name -eq 'TOC 1') {
                $s.ParagraphFormat.SpaceBefore = 5
                $s.ParagraphFormat.SpaceAfter = 2
                $s.Font.Size = 10.5
            }
            else {
                $s.ParagraphFormat.SpaceBefore = 0
                $s.ParagraphFormat.SpaceAfter = 0
                $s.Font.Size = 10
            }
            $s.ParagraphFormat.LineSpacingRule = 0      # 单倍行距
            $s.ParagraphFormat.RightIndent = 16         # 给页码留位置
            $s.Font.Name = '微软雅黑'
        }
        catch { "WARN 样式不存在: $name" }
    }

    "TOC_COUNT=" + $doc.TablesOfContents.Count
    for ($i = 1; $i -le $doc.TablesOfContents.Count; $i++) {
        $doc.TablesOfContents.Item($i).Update()
    }
    $doc.Fields.Update() | Out-Null
    foreach ($sec in $doc.Sections) {
        foreach ($h in $sec.Headers) { $h.Range.Fields.Update() | Out-Null }
        foreach ($f in $sec.Footers) { $f.Range.Fields.Update() | Out-Null }
    }
    $doc.Repaginate()

    "PAGES=" + $doc.ComputeStatistics(2)
    "WORDS=" + $doc.ComputeStatistics(0)
    "TABLES=" + $doc.Tables.Count
    if ($doc.TablesOfContents.Count -gt 0) {
        "TOC_PARAS=" + $doc.TablesOfContents.Item(1).Range.Paragraphs.Count
    }

    $doc.ExportAsFixedFormat($Pdf, 17) | Out-Null   # 17 = wdExportFormatPDF
    $doc.Save()
    $doc.Close(0)
    "PDF=" + (Get-Item $Pdf).Length
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
