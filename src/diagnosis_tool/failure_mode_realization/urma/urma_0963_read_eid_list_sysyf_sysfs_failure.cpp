#include "urma_0963_read_eid_list_sysyf_sysfs_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0963ReadEidListSysyfSysfsFailure> g_urma("urma_0963");

bool Urma0963ReadEidListSysyfSysfsFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to read sysfs file"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0963ReadEidListSysyfSysfsFailure::GetName() const
{
    return "read_eid_list_sysyf 读取sysfs失败";
}

std::string Urma0963ReadEidListSysyfSysfsFailure::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常";
}

RootCause Urma0963ReadEidListSysyfSysfsFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0963ReadEidListSysyfSysfsFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0963ReadEidListSysyfSysfsFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to read sysfs file";
}

std::string Urma0963ReadEidListSysyfSysfsFailure::GetId() const
{
    return "urma_0963";
}
} // namespace diag
