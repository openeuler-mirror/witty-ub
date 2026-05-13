#include "urma_0967_read_eid_sysfs_with_index_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0967ReadEidSysfsWithIndexFailure> g_urma("urma_0967");

bool Urma0967ReadEidSysfsWithIndexFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to parse eid value, dev name:%, eid idx:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0967ReadEidSysfsWithIndexFailure::GetName() const
{
    return "read_eid_sysfs_with_index 解析失败";
}

std::string Urma0967ReadEidSysfsWithIndexFailure::GetRootCauseDesc() const
{
    return "解析设备属性、EID、sysfs 字段或输入格式失败，通常表示输入/设备上报内容不符合预期；该路径返回 -1";
}

RootCause Urma0967ReadEidSysfsWithIndexFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0967ReadEidSysfsWithIndexFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0967ReadEidSysfsWithIndexFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to parse eid value, dev name:%, eid idx:%";
}

std::string Urma0967ReadEidSysfsWithIndexFailure::GetId() const
{
    return "urma_0967";
}
} // namespace diag
