#include "urma_0865_urma_parse_rsvd_jetty_range_failure_urma_read_sysfs_file.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile> g_urma("urma_0865");

bool Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"parse sysfs:% failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::GetName() const
{
    return "urma_parse_rsvd_jetty_range 解析失败（urma_read_sysfs_file(sysfs_path, file, tmp_value, "
           "URMA_MAX_VALUE_LEN) <= 0）";
}

std::string Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常";
}

RootCause Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：parse sysfs:% failed";
}

std::string Urma0865UrmaParseRsvdJettyRangeFailureUrmaReadSysfsFile::GetId() const
{
    return "urma_0865";
}
} // namespace diag
