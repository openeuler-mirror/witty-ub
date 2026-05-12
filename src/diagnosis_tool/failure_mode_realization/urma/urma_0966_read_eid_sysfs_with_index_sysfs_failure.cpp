#include "urma_0966_read_eid_sysfs_with_index_sysfs_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0966ReadEidSysfsWithIndexSysfsFailure> g_urma("urma_0966");

bool Urma0966ReadEidSysfsWithIndexSysfsFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to read sysfs file"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0966ReadEidSysfsWithIndexSysfsFailure::GetName() const
{
    return "read_eid_sysfs_with_index 读取sysfs失败";
}

std::string Urma0966ReadEidSysfsWithIndexSysfsFailure::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常；该路径返回 -1";
}

RootCause Urma0966ReadEidSysfsWithIndexSysfsFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0966ReadEidSysfsWithIndexSysfsFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0966ReadEidSysfsWithIndexSysfsFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to read sysfs file";
}

std::string Urma0966ReadEidSysfsWithIndexSysfsFailure::GetId() const
{
    return "urma_0966";
}
} // namespace diag
