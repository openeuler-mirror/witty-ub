#include "urma_0965_read_eid_sysfs_with_index_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0965ReadEidSysfsWithIndexPathFailure> g_urma("urma_0965");

bool Urma0965ReadEidSysfsWithIndexPathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"snprintf failed, eid idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0965ReadEidSysfsWithIndexPathFailure::GetName() const
{
    return "read_eid_sysfs_with_index 格式化路径失败";
}

std::string Urma0965ReadEidSysfsWithIndexPathFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误；该路径返回 -1";
}

RootCause Urma0965ReadEidSysfsWithIndexPathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0965ReadEidSysfsWithIndexPathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0965ReadEidSysfsWithIndexPathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：snprintf failed, eid idx: %.";
}

std::string Urma0965ReadEidSysfsWithIndexPathFailure::GetId() const
{
    return "urma_0965";
}
} // namespace diag
