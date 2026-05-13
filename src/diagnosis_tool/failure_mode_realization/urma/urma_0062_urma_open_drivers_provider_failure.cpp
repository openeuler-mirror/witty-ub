#include "urma_0062_urma_open_drivers_provider_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0062UrmaOpenDriversProviderFailure> g_urma("urma_0062");

bool Urma0062UrmaOpenDriversProviderFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to open provider %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0062UrmaOpenDriversProviderFailure::GetName() const
{
    return "urma_open_drivers 打开provider失败";
}

std::string Urma0062UrmaOpenDriversProviderFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "n_loaded_drivers";
}

RootCause Urma0062UrmaOpenDriversProviderFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0062UrmaOpenDriversProviderFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0062UrmaOpenDriversProviderFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to open provider %";
}

std::string Urma0062UrmaOpenDriversProviderFailure::GetId() const
{
    return "urma_0062";
}
} // namespace diag
