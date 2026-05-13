#include "urma_0066_urma_open_provider_file_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0066UrmaOpenProviderFileFailure> g_urma("urma_0066");

bool Urma0066UrmaOpenProviderFileFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"% open failed, err: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0066UrmaOpenProviderFileFailure::GetName() const
{
    return "urma_open_provider 打开文件或库失败";
}

std::string Urma0066UrmaOpenProviderFileFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0066UrmaOpenProviderFileFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0066UrmaOpenProviderFileFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0066UrmaOpenProviderFileFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：% open failed, err: %.";
}

std::string Urma0066UrmaOpenProviderFileFailure::GetId() const
{
    return "urma_0066";
}
} // namespace diag
