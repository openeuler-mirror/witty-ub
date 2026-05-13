#include "urma_0065_urma_open_provider_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0065UrmaOpenProviderPathFailure> g_urma("urma_0065");

bool Urma0065UrmaOpenProviderPathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"realpath failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0065UrmaOpenProviderPathFailure::GetName() const
{
    return "urma_open_provider 路径规范化失败";
}

std::string Urma0065UrmaOpenProviderPathFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0065UrmaOpenProviderPathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0065UrmaOpenProviderPathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0065UrmaOpenProviderPathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：realpath failed.";
}

std::string Urma0065UrmaOpenProviderPathFailure::GetId() const
{
    return "urma_0065";
}
} // namespace diag
